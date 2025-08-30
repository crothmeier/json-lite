#!/bin/bash
#
# Database Restore Script for Unified Conversations Database
#
# DESCRIPTION:
#   Simplified restoration script for the SQLite database backups
#   created by backup_db.sh
#
# USAGE:
#   ./restore_db.sh                    # Interactive mode - select from available backups
#   ./restore_db.sh backup.db.gz       # Restore specific backup file
#   ./restore_db.sh --latest           # Restore the most recent backup
#   ./restore_db.sh --list             # List available backups
#   ./restore_db.sh --verify FILE      # Verify backup integrity without restoring
#

set -euo pipefail

# Configuration
TARGET_DB="/home/crathmene/data/unified_conversations.db"
BACKUP_DIR="/home/crathmene/backups/conversations"
SAFETY_BACKUP_DIR="/home/crathmene/data/safety_backups"

# Commands with full paths for reliability
SQLITE3="/usr/bin/sqlite3"
GUNZIP="/bin/gunzip"
FIND="/usr/bin/find"
MKDIR="/bin/mkdir"
CP="/bin/cp"
MV="/bin/mv"
DATE="/bin/date"

# Colors
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

list_backups() {
    echo "Available backups in $BACKUP_DIR:"
    echo "----------------------------------------"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "Backup directory not found: $BACKUP_DIR"
        return 1
    fi
    
    local backups=$("$FIND" "$BACKUP_DIR" -name "unified_conversations_*.db.gz" -type f 2>/dev/null | sort -r)
    
    if [ -z "$backups" ]; then
        log_warning "No backups found"
        return 1
    fi
    
    local count=0
    while IFS= read -r backup; do
        count=$((count + 1))
        local size=$(du -h "$backup" | cut -f1)
        local date=$(stat -c %y "$backup" | cut -d' ' -f1,2 | cut -d'.' -f1)
        local name=$(basename "$backup")
        
        printf "%2d. %s (%s) - %s\n" "$count" "$name" "$size" "$date"
    done <<< "$backups"
    
    echo ""
    echo "Total backups: $count"
}

select_backup_interactive() {
    echo "Select a backup to restore:"
    echo ""
    
    local backups=$("$FIND" "$BACKUP_DIR" -name "unified_conversations_*.db.gz" -type f 2>/dev/null | sort -r)
    
    if [ -z "$backups" ]; then
        log_error "No backups found in $BACKUP_DIR"
        exit 1
    fi
    
    # Create array of backups
    local backup_array=()
    while IFS= read -r backup; do
        backup_array+=("$backup")
    done <<< "$backups"
    
    # Display menu
    local count=0
    for backup in "${backup_array[@]}"; do
        count=$((count + 1))
        local size=$(du -h "$backup" | cut -f1)
        local name=$(basename "$backup")
        printf "%2d. %s (%s)\n" "$count" "$name" "$size"
    done
    
    echo ""
    read -p "Enter number (1-$count) or 'q' to quit: " selection
    
    if [ "$selection" = "q" ] || [ "$selection" = "Q" ]; then
        log_info "Restore cancelled"
        exit 0
    fi
    
    if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt "$count" ]; then
        log_error "Invalid selection"
        exit 1
    fi
    
    local selected_backup="${backup_array[$((selection - 1))]}"
    echo "$selected_backup"
}

get_latest_backup() {
    local latest=$("$FIND" "$BACKUP_DIR" -name "unified_conversations_*.db.gz" -type f 2>/dev/null | sort -r | head -1)
    
    if [ -z "$latest" ]; then
        log_error "No backups found in $BACKUP_DIR"
        exit 1
    fi
    
    echo "$latest"
}

verify_backup() {
    local backup_file="$1"
    
    log_step "Verifying backup file: $(basename "$backup_file")"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Create temp directory
    local temp_dir=$(mktemp -d)
    local temp_db="${temp_dir}/verify.db"
    
    # Decompress
    log_info "Decompressing backup for verification..."
    if ! "$GUNZIP" -c "$backup_file" > "$temp_db" 2>&1; then
        log_error "Failed to decompress backup"
        rm -rf "$temp_dir"
        return 1
    fi
    
    # Check integrity
    log_info "Running integrity check..."
    local integrity_result=$("$SQLITE3" "$temp_db" "PRAGMA integrity_check;" 2>&1 || echo "FAILED")
    
    if [ "$integrity_result" = "ok" ]; then
        log_info "✓ Integrity check passed"
    else
        log_warning "Integrity check result: $integrity_result"
    fi
    
    # Get statistics
    log_info "Backup statistics:"
    local conv_count=$("$SQLITE3" "$temp_db" "SELECT COUNT(*) FROM metadata;" 2>/dev/null || echo "unknown")
    local msg_count=$("$SQLITE3" "$temp_db" "SELECT COUNT(*) FROM conversations;" 2>/dev/null || echo "unknown")
    local sources=$("$SQLITE3" "$temp_db" "SELECT source, COUNT(*) FROM metadata GROUP BY source;" 2>/dev/null || echo "unknown")
    
    echo "  Conversations: $conv_count"
    echo "  Messages: $msg_count"
    echo "  Sources: $sources"
    
    # Clean up
    rm -rf "$temp_dir"
    
    if [ "$integrity_result" = "ok" ]; then
        return 0
    else
        return 1
    fi
}

restore_database() {
    local backup_file="$1"
    
    log_step "Preparing to restore from: $(basename "$backup_file")"
    
    # Verify backup exists
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    # Show current database info
    if [ -f "$TARGET_DB" ]; then
        log_info "Current database information:"
        local current_size=$(du -h "$TARGET_DB" | cut -f1)
        local current_convs=$("$SQLITE3" "$TARGET_DB" "SELECT COUNT(*) FROM metadata;" 2>/dev/null || echo "unknown")
        echo "  Size: $current_size"
        echo "  Conversations: $current_convs"
    else
        log_warning "No existing database found at $TARGET_DB"
    fi
    
    # Verify backup first
    log_step "Verifying backup integrity..."
    if ! verify_backup "$backup_file"; then
        log_error "Backup verification failed"
        read -p "Continue anyway? (y/N): " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            log_info "Restore cancelled"
            exit 0
        fi
    fi
    
    # Final confirmation
    echo ""
    log_warning "This will replace the current database!"
    echo "Backup to restore: $(basename "$backup_file")"
    echo "Target location: $TARGET_DB"
    echo ""
    read -p "Type 'RESTORE' to confirm: " confirm
    
    if [ "$confirm" != "RESTORE" ]; then
        log_info "Restore cancelled"
        exit 0
    fi
    
    # Create safety backup directory
    "$MKDIR" -p "$SAFETY_BACKUP_DIR"
    
    # Create safety backup of current database
    if [ -f "$TARGET_DB" ]; then
        local safety_backup="${SAFETY_BACKUP_DIR}/pre_restore_$($DATE '+%Y%m%d_%H%M%S').db"
        log_step "Creating safety backup: $safety_backup"
        "$CP" "$TARGET_DB" "$safety_backup"
        
        # Compress safety backup
        "$GZIP" -9 "$safety_backup"
        log_info "Safety backup created: ${safety_backup}.gz"
    fi
    
    # Create temp directory for restoration
    local temp_dir=$(mktemp -d)
    local temp_db="${temp_dir}/restore.db"
    
    # Decompress backup
    log_step "Decompressing backup..."
    if ! "$GUNZIP" -c "$backup_file" > "$temp_db" 2>&1; then
        log_error "Failed to decompress backup"
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Stop any services using the database
    log_warning "Please ensure all services using the database are stopped"
    read -p "Press ENTER when ready to continue..."
    
    # Replace database
    log_step "Replacing database..."
    "$MV" "$temp_db" "$TARGET_DB"
    
    # Set proper permissions
    chmod 644 "$TARGET_DB"
    chown crathmene:crathmene "$TARGET_DB" 2>/dev/null || true
    
    # Verify restored database
    log_step "Verifying restored database..."
    if ! "$SQLITE3" "$TARGET_DB" "SELECT COUNT(*) FROM metadata;" >/dev/null 2>&1; then
        log_error "Restored database verification failed!"
        
        if [ -f "${safety_backup}.gz" ]; then
            log_warning "Attempting to restore safety backup..."
            "$GUNZIP" -c "${safety_backup}.gz" > "$TARGET_DB"
        fi
        
        rm -rf "$temp_dir"
        exit 1
    fi
    
    # Clean up
    rm -rf "$temp_dir"
    
    # Show restored database info
    log_info "Database restored successfully!"
    local restored_convs=$("$SQLITE3" "$TARGET_DB" "SELECT COUNT(*) FROM metadata;" 2>/dev/null)
    local restored_msgs=$("$SQLITE3" "$TARGET_DB" "SELECT COUNT(*) FROM conversations;" 2>/dev/null)
    echo ""
    echo "Restored database contains:"
    echo "  Conversations: $restored_convs"
    echo "  Messages: $restored_msgs"
    echo ""
    log_info "Safety backup kept at: ${safety_backup}.gz"
    log_info "You can now restart services using the database"
}

show_help() {
    echo "Database Restore Script"
    echo ""
    echo "Usage:"
    echo "  $0                     # Interactive mode - select from list"
    echo "  $0 <backup.db.gz>      # Restore specific backup file"
    echo "  $0 --latest            # Restore the most recent backup"
    echo "  $0 --list              # List available backups"
    echo "  $0 --verify <file>     # Verify backup integrity"
    echo "  $0 --help              # Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --list"
    echo "  $0 --verify $BACKUP_DIR/unified_conversations_20240101_020000.db.gz"
    echo "  $0 --latest"
    echo "  $0 /path/to/backup.db.gz"
    echo ""
    echo "Safety:"
    echo "  - Creates safety backup before restoration"
    echo "  - Verifies backup integrity before restoring"
    echo "  - Safety backups stored in: $SAFETY_BACKUP_DIR"
}

# Main execution
main() {
    case "${1:-}" in
        --list)
            list_backups
            ;;
        --latest)
            log_info "Selecting latest backup..."
            backup=$(get_latest_backup)
            log_info "Latest backup: $(basename "$backup")"
            restore_database "$backup"
            ;;
        --verify)
            if [ -z "${2:-}" ]; then
                log_error "Please specify a backup file to verify"
                exit 1
            fi
            verify_backup "$2"
            ;;
        --help|-h)
            show_help
            ;;
        "")
            # Interactive mode
            backup=$(select_backup_interactive)
            restore_database "$backup"
            ;;
        *)
            # Assume it's a backup file path
            if [[ "$1" == -* ]]; then
                log_error "Unknown option: $1"
                show_help
                exit 1
            fi
            restore_database "$1"
            ;;
    esac
}

# Handle errors
trap 'log_error "Restore script failed with error on line $LINENO"' ERR

# Run main function
main "$@"