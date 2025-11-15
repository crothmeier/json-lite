#!/bin/bash
#
# Database Backup Script for Unified Conversations Database
# 
# DESCRIPTION:
#   Backs up the SQLite database using the .backup command for consistency,
#   compresses with gzip, and maintains a retention policy of 7 days.
#
# CRON SETUP:
#   Add to crontab for daily backups at 2 AM:
#   0 2 * * * /home/crathmene/git/json-lite/scripts/backup_db.sh > /dev/null 2>&1
#
#   Or with logging:
#   0 2 * * * /home/crathmene/git/json-lite/scripts/backup_db.sh >> /var/log/db_backup.log 2>&1
#
# RESTORE INSTRUCTIONS:
#   To restore from a backup:
#   1. Stop any services using the database
#   2. Decompress the backup:
#      gunzip -k /home/crathmene/backups/conversations/unified_conversations_YYYYMMDD_HHMMSS.db.gz
#   3. Verify the backup integrity:
#      sqlite3 /home/crathmene/backups/conversations/unified_conversations_YYYYMMDD_HHMMSS.db "PRAGMA integrity_check;"
#   4. Replace the current database:
#      mv /home/crathmene/data/unified_conversations.db /home/crathmene/data/unified_conversations.db.old
#      cp /home/crathmene/backups/conversations/unified_conversations_YYYYMMDD_HHMMSS.db /home/crathmene/data/unified_conversations.db
#   5. Verify the restored database:
#      sqlite3 /home/crathmene/data/unified_conversations.db "SELECT COUNT(*) FROM metadata;"
#   6. Restart services
#
# MANUAL RESTORE USING THIS SCRIPT:
#   ./backup_db.sh --restore /path/to/backup.db.gz
#

set -euo pipefail

# Configuration
# These can be overridden via environment variables
# Set DATABASE_PATH and DATA_DIR in your .env file or environment
SOURCE_DB="${DATABASE_PATH:-${DATA_DIR:-$HOME/data}/unified_conversations.db}"
BACKUP_DIR="${BACKUP_DIR:-${DATA_DIR:-$HOME/data}/../backups/conversations}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

# For cron compatibility - use full paths
SQLITE3="/usr/bin/sqlite3"
GZIP="/bin/gzip"
FIND="/usr/bin/find"
RM="/bin/rm"
MV="/bin/mv"
CP="/bin/cp"
MKDIR="/bin/mkdir"
BASENAME="/usr/bin/basename"
DIRNAME="/usr/bin/dirname"
DATE="/bin/date"

# Colors (disabled when not in terminal, e.g., in cron)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# Functions
log_info() {
    echo -e "${GREEN}${LOG_PREFIX} [INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}${LOG_PREFIX} [ERROR]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}${LOG_PREFIX} [WARNING]${NC} $1"
}

check_dependencies() {
    local missing_deps=0
    
    for cmd in "$SQLITE3" "$GZIP" "$FIND"; do
        if [ ! -x "$cmd" ]; then
            log_error "Required command not found or not executable: $cmd"
            missing_deps=1
        fi
    done
    
    if [ $missing_deps -eq 1 ]; then
        log_error "Missing dependencies. Please install required packages."
        exit 1
    fi
}

create_backup_directory() {
    if [ ! -d "$BACKUP_DIR" ]; then
        log_info "Creating backup directory: $BACKUP_DIR"
        "$MKDIR" -p "$BACKUP_DIR"
        
        if [ ! -d "$BACKUP_DIR" ]; then
            log_error "Failed to create backup directory"
            exit 1
        fi
    fi
}

check_source_database() {
    if [ ! -f "$SOURCE_DB" ]; then
        log_error "Source database not found: $SOURCE_DB"
        exit 1
    fi
    
    if [ ! -r "$SOURCE_DB" ]; then
        log_error "Cannot read source database: $SOURCE_DB"
        exit 1
    fi
    
    # Check database integrity
    log_info "Checking source database integrity..."
    if ! integrity_result=$("$SQLITE3" "$SOURCE_DB" "PRAGMA integrity_check;" 2>&1); then
        log_error "Database integrity check failed: $integrity_result"
        exit 1
    fi
    
    if [ "$integrity_result" != "ok" ]; then
        log_warning "Database integrity check returned: $integrity_result"
    else
        log_info "Database integrity check passed"
    fi
}

perform_backup() {
    local timestamp=$("$DATE" '+%Y%m%d_%H%M%S')
    local backup_name="unified_conversations_${timestamp}.db"
    local backup_path="${BACKUP_DIR}/${backup_name}"
    local backup_gz="${backup_path}.gz"
    
    log_info "Starting backup of $SOURCE_DB"
    
    # Use SQLite's .backup command for consistency
    log_info "Creating consistent backup using SQLite .backup command..."
    
    # Create the backup SQL command
    local backup_sql="
PRAGMA busy_timeout = 30000;
.backup '${backup_path}'
"
    
    # Execute the backup
    if ! backup_output=$(echo "$backup_sql" | "$SQLITE3" "$SOURCE_DB" 2>&1); then
        log_error "SQLite backup failed: $backup_output"
        # Clean up partial backup if it exists
        [ -f "$backup_path" ] && "$RM" -f "$backup_path"
        exit 1
    fi
    
    # Verify the backup was created
    if [ ! -f "$backup_path" ]; then
        log_error "Backup file was not created: $backup_path"
        exit 1
    fi
    
    # Get file sizes for logging
    local source_size=$("$BASENAME" "$SOURCE_DB" | xargs -I {} find "$("$DIRNAME" "$SOURCE_DB")" -name {} -printf "%s")
    local backup_size=$("$BASENAME" "$backup_path" | xargs -I {} find "$BACKUP_DIR" -name {} -printf "%s")
    
    log_info "Backup created successfully (size: $backup_size bytes)"
    
    # Verify backup integrity
    log_info "Verifying backup integrity..."
    if ! verify_result=$("$SQLITE3" "$backup_path" "PRAGMA integrity_check;" 2>&1); then
        log_error "Backup verification failed: $verify_result"
        "$RM" -f "$backup_path"
        exit 1
    fi
    
    if [ "$verify_result" != "ok" ]; then
        log_warning "Backup integrity check returned: $verify_result"
    else
        log_info "Backup integrity verified"
    fi
    
    # Compress the backup
    log_info "Compressing backup with gzip..."
    if ! "$GZIP" -9 "$backup_path" 2>&1; then
        log_error "Failed to compress backup"
        # Try to clean up
        [ -f "$backup_path" ] && "$RM" -f "$backup_path"
        exit 1
    fi
    
    # Verify compressed file exists
    if [ ! -f "$backup_gz" ]; then
        log_error "Compressed backup file not found: $backup_gz"
        exit 1
    fi
    
    local compressed_size=$(find "$BACKUP_DIR" -name "$($BASENAME "$backup_gz")" -printf "%s")
    local compression_ratio=$(echo "scale=2; (1 - $compressed_size / $backup_size) * 100" | bc 2>/dev/null || echo "unknown")
    
    log_info "Backup compressed successfully (size: $compressed_size bytes, compression: ${compression_ratio}%)"
    log_info "Backup completed: $backup_gz"
    
    return 0
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    # Find and count old backups
    local old_backups_count=$("$FIND" "$BACKUP_DIR" -name "unified_conversations_*.db.gz" -type f -mtime +$RETENTION_DAYS | wc -l)
    
    if [ "$old_backups_count" -gt 0 ]; then
        log_info "Found $old_backups_count old backup(s) to remove"
        
        # Remove old backups
        "$FIND" "$BACKUP_DIR" -name "unified_conversations_*.db.gz" -type f -mtime +$RETENTION_DAYS -exec "$RM" -f {} \; -exec echo "${LOG_PREFIX} [INFO] Removed old backup: {}" \;
    else
        log_info "No old backups to remove"
    fi
    
    # List current backups
    local current_backups=$("$FIND" "$BACKUP_DIR" -name "unified_conversations_*.db.gz" -type f | wc -l)
    log_info "Current number of backups: $current_backups"
}

restore_backup() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_warning "RESTORE MODE - This will replace the current database!"
    echo "Current database: $SOURCE_DB"
    echo "Restore from: $backup_file"
    echo ""
    echo "Press ENTER to continue or Ctrl+C to cancel..."
    read -r
    
    # Create temp directory for restoration
    local temp_dir=$(mktemp -d)
    local temp_db="${temp_dir}/restore.db"
    
    # Decompress if needed
    if [[ "$backup_file" == *.gz ]]; then
        log_info "Decompressing backup..."
        if ! gunzip -c "$backup_file" > "$temp_db" 2>&1; then
            log_error "Failed to decompress backup"
            rm -rf "$temp_dir"
            exit 1
        fi
    else
        cp "$backup_file" "$temp_db"
    fi
    
    # Verify backup integrity
    log_info "Verifying backup integrity..."
    if ! verify_result=$("$SQLITE3" "$temp_db" "PRAGMA integrity_check;" 2>&1); then
        log_error "Backup verification failed: $verify_result"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    if [ "$verify_result" != "ok" ]; then
        log_warning "Backup integrity check returned: $verify_result"
        echo "Continue anyway? (y/N)"
        read -r confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            log_info "Restore cancelled"
            rm -rf "$temp_dir"
            exit 0
        fi
    fi
    
    # Backup current database before replacing
    local safety_backup="${SOURCE_DB}.before_restore.$(date '+%Y%m%d_%H%M%S')"
    log_info "Creating safety backup of current database: $safety_backup"
    "$CP" "$SOURCE_DB" "$safety_backup"
    
    # Replace database
    log_info "Replacing database..."
    "$MV" "$temp_db" "$SOURCE_DB"
    
    # Verify restored database
    log_info "Verifying restored database..."
    if ! "$SQLITE3" "$SOURCE_DB" "SELECT COUNT(*) FROM metadata;" >/dev/null 2>&1; then
        log_error "Restored database verification failed!"
        log_warning "Attempting to restore safety backup..."
        "$MV" "$safety_backup" "$SOURCE_DB"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Clean up
    rm -rf "$temp_dir"
    
    log_info "Database restored successfully!"
    log_info "Safety backup kept at: $safety_backup"
    
    # Show some statistics
    local conv_count=$("$SQLITE3" "$SOURCE_DB" "SELECT COUNT(*) FROM metadata;" 2>/dev/null || echo "unknown")
    local msg_count=$("$SQLITE3" "$SOURCE_DB" "SELECT COUNT(*) FROM conversations;" 2>/dev/null || echo "unknown")
    log_info "Restored database contains $conv_count conversations and $msg_count messages"
}

show_backup_status() {
    log_info "Backup Status Report"
    echo "----------------------------------------"
    echo "Source Database: $SOURCE_DB"
    echo "Backup Directory: $BACKUP_DIR"
    echo "Retention Policy: $RETENTION_DAYS days"
    echo ""
    
    if [ -f "$SOURCE_DB" ]; then
        local db_size=$(du -h "$SOURCE_DB" | cut -f1)
        echo "Database Size: $db_size"
        
        local conv_count=$("$SQLITE3" "$SOURCE_DB" "SELECT COUNT(*) FROM metadata;" 2>/dev/null || echo "unknown")
        local msg_count=$("$SQLITE3" "$SOURCE_DB" "SELECT COUNT(*) FROM conversations;" 2>/dev/null || echo "unknown")
        echo "Conversations: $conv_count"
        echo "Messages: $msg_count"
    else
        echo "Database: NOT FOUND"
    fi
    
    echo ""
    echo "Existing Backups:"
    if [ -d "$BACKUP_DIR" ]; then
        "$FIND" "$BACKUP_DIR" -name "unified_conversations_*.db.gz" -type f -printf "%TY-%Tm-%Td %TH:%TM  %s bytes  %f\n" | sort -r | head -10
        
        local total_backups=$("$FIND" "$BACKUP_DIR" -name "unified_conversations_*.db.gz" -type f | wc -l)
        local total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
        echo ""
        echo "Total Backups: $total_backups"
        echo "Total Size: $total_size"
    else
        echo "Backup directory does not exist"
    fi
}

# Main execution
main() {
    case "${1:-}" in
        --restore)
            if [ -z "${2:-}" ]; then
                log_error "Please specify a backup file to restore"
                echo "Usage: $0 --restore /path/to/backup.db.gz"
                exit 1
            fi
            check_dependencies
            restore_backup "$2"
            ;;
        --status)
            show_backup_status
            ;;
        --help|-h)
            echo "Database Backup Script"
            echo ""
            echo "Usage:"
            echo "  $0                    # Perform backup"
            echo "  $0 --restore FILE     # Restore from backup"
            echo "  $0 --status           # Show backup status"
            echo "  $0 --help             # Show this help"
            echo ""
            echo "Cron example (daily at 2 AM):"
            echo "  0 2 * * * $0"
            ;;
        "")
            # Normal backup operation
            log_info "Starting database backup process"
            check_dependencies
            check_source_database
            create_backup_directory
            perform_backup
            cleanup_old_backups
            log_info "Backup process completed successfully"
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
}

# Handle errors
trap 'log_error "Backup script failed with error on line $LINENO"' ERR

# Run main function
main "$@"