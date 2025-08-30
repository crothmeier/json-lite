#!/bin/bash
#
# Cron Setup Script for Database Backups
# Sets up automated daily backups via crontab
#

set -euo pipefail

BACKUP_SCRIPT="/home/crathmene/git/json-lite/scripts/backup_db.sh"
LOG_FILE="/var/log/db_backup.log"

# Colors
if [ -t 1 ]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    NC='\033[0m'
else
    GREEN=''
    YELLOW=''
    RED=''
    NC=''
fi

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    if [ ! -f "$BACKUP_SCRIPT" ]; then
        log_error "Backup script not found: $BACKUP_SCRIPT"
        exit 1
    fi
    
    if [ ! -x "$BACKUP_SCRIPT" ]; then
        log_error "Backup script is not executable: $BACKUP_SCRIPT"
        echo "Run: chmod +x $BACKUP_SCRIPT"
        exit 1
    fi
}

setup_log_file() {
    if [ ! -f "$LOG_FILE" ]; then
        log_info "Creating log file: $LOG_FILE"
        sudo touch "$LOG_FILE"
        sudo chown crathmene:crathmene "$LOG_FILE"
    else
        log_info "Log file already exists: $LOG_FILE"
    fi
}

add_cron_job() {
    local schedule="$1"
    local description="$2"
    
    # Create the cron entry
    local cron_entry="$schedule $BACKUP_SCRIPT >> $LOG_FILE 2>&1"
    
    # Check if already exists
    if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
        log_warning "Backup cron job already exists:"
        crontab -l | grep "$BACKUP_SCRIPT"
        echo ""
        read -p "Replace existing cron job? (y/N): " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            log_info "Keeping existing cron job"
            return
        fi
        
        # Remove existing entry
        crontab -l | grep -v "$BACKUP_SCRIPT" | crontab -
    fi
    
    # Add new cron job
    log_info "Adding cron job: $description"
    log_info "Schedule: $schedule"
    
    # Add to crontab
    (crontab -l 2>/dev/null || true; echo "# Database backup - $description"; echo "$cron_entry") | crontab -
    
    log_info "Cron job added successfully"
}

remove_cron_job() {
    if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
        log_info "Removing existing backup cron job..."
        crontab -l | grep -v "$BACKUP_SCRIPT" | crontab -
        log_info "Cron job removed"
    else
        log_info "No backup cron job found"
    fi
}

show_status() {
    echo "Backup Cron Status"
    echo "=================="
    echo ""
    
    echo "Current cron jobs for user $(whoami):"
    if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
        crontab -l | grep -A1 -B1 "$BACKUP_SCRIPT" || crontab -l | grep "$BACKUP_SCRIPT"
    else
        echo "No backup cron job configured"
    fi
    
    echo ""
    echo "Log file: $LOG_FILE"
    if [ -f "$LOG_FILE" ]; then
        echo "Last 5 log entries:"
        tail -5 "$LOG_FILE" 2>/dev/null || echo "  (no entries yet)"
    else
        echo "  (log file does not exist)"
    fi
    
    echo ""
    echo "Backup script: $BACKUP_SCRIPT"
    if [ -x "$BACKUP_SCRIPT" ]; then
        echo "  Status: Executable ✓"
    else
        echo "  Status: Not executable ✗"
    fi
}

interactive_setup() {
    echo "Database Backup Cron Setup"
    echo "========================="
    echo ""
    echo "Select backup schedule:"
    echo "1. Daily at 2:00 AM (recommended)"
    echo "2. Daily at midnight"
    echo "3. Every 6 hours"
    echo "4. Every 12 hours"
    echo "5. Weekly on Sunday at 2:00 AM"
    echo "6. Custom schedule"
    echo "7. Remove cron job"
    echo "0. Cancel"
    echo ""
    read -p "Enter choice (0-7): " choice
    
    case "$choice" in
        1)
            add_cron_job "0 2 * * *" "Daily at 2:00 AM"
            ;;
        2)
            add_cron_job "0 0 * * *" "Daily at midnight"
            ;;
        3)
            add_cron_job "0 */6 * * *" "Every 6 hours"
            ;;
        4)
            add_cron_job "0 */12 * * *" "Every 12 hours"
            ;;
        5)
            add_cron_job "0 2 * * 0" "Weekly on Sunday at 2:00 AM"
            ;;
        6)
            echo ""
            echo "Enter custom cron schedule (e.g., '0 2 * * *' for daily at 2 AM)"
            echo "Format: minute hour day month weekday"
            echo "Use https://crontab.guru for help"
            read -p "Schedule: " custom_schedule
            if [ -n "$custom_schedule" ]; then
                add_cron_job "$custom_schedule" "Custom schedule"
            else
                log_error "No schedule provided"
                exit 1
            fi
            ;;
        7)
            remove_cron_job
            ;;
        0)
            log_info "Setup cancelled"
            exit 0
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
}

test_backup() {
    log_info "Running test backup..."
    
    if "$BACKUP_SCRIPT"; then
        log_info "Test backup completed successfully"
    else
        log_error "Test backup failed"
        exit 1
    fi
}

# Main
main() {
    case "${1:-}" in
        --add)
            check_prerequisites
            setup_log_file
            if [ -n "${2:-}" ]; then
                add_cron_job "$2" "Custom schedule"
            else
                add_cron_job "0 2 * * *" "Daily at 2:00 AM (default)"
            fi
            ;;
        --remove)
            remove_cron_job
            ;;
        --status)
            show_status
            ;;
        --test)
            check_prerequisites
            test_backup
            ;;
        --help|-h)
            echo "Database Backup Cron Setup"
            echo ""
            echo "Usage:"
            echo "  $0                     # Interactive setup"
            echo "  $0 --add [schedule]    # Add cron job (default: daily 2 AM)"
            echo "  $0 --remove            # Remove cron job"
            echo "  $0 --status            # Show current status"
            echo "  $0 --test              # Run test backup"
            echo "  $0 --help              # Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 --add '0 2 * * *'   # Daily at 2 AM"
            echo "  $0 --add '0 */6 * * *' # Every 6 hours"
            echo ""
            echo "Cron format: minute hour day month weekday"
            echo "Visit https://crontab.guru for schedule help"
            ;;
        "")
            check_prerequisites
            setup_log_file
            interactive_setup
            echo ""
            read -p "Run test backup now? (y/N): " test_confirm
            if [ "$test_confirm" = "y" ] || [ "$test_confirm" = "Y" ]; then
                test_backup
            fi
            echo ""
            show_status
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
}

main "$@"