#!/bin/bash
# Management script for Auto Import Watcher

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="auto-import.service"
LOG_FILE="$SCRIPT_DIR/auto_import.log"
STATE_FILE="$SCRIPT_DIR/.auto_import_state.json"
PYTHON_SCRIPT="$SCRIPT_DIR/auto_import.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

test_run() {
    print_info "Testing auto-import script (Ctrl+C to stop)..."
    
    # Check if virtual environment exists
    if [ ! -f "/home/crathmene/git/json-lite/venv/bin/python" ]; then
        print_error "Virtual environment not found. Please set up the venv first."
        exit 1
    fi
    
    # Run the script directly
    /home/crathmene/git/json-lite/venv/bin/python "$PYTHON_SCRIPT"
}

install_service() {
    print_info "Installing auto-import service..."
    
    if [[ $EUID -ne 0 ]]; then
        print_error "This operation requires root privileges. Please run with sudo."
        exit 1
    fi
    
    # Copy service file
    cp "$SCRIPT_DIR/$SERVICE_FILE" "/etc/systemd/system/"
    print_success "Service file copied"
    
    # Reload systemd
    systemctl daemon-reload
    print_success "Systemd daemon reloaded"
    
    # Enable service
    systemctl enable "$SERVICE_FILE"
    print_success "Service enabled"
    
    print_success "Installation complete!"
    print_info "To start: sudo systemctl start $SERVICE_FILE"
}

uninstall_service() {
    print_info "Uninstalling auto-import service..."
    
    if [[ $EUID -ne 0 ]]; then
        print_error "This operation requires root privileges. Please run with sudo."
        exit 1
    fi
    
    # Stop service if running
    if systemctl is-active --quiet "$SERVICE_FILE"; then
        systemctl stop "$SERVICE_FILE"
        print_success "Service stopped"
    fi
    
    # Disable service
    if systemctl is-enabled --quiet "$SERVICE_FILE"; then
        systemctl disable "$SERVICE_FILE"
        print_success "Service disabled"
    fi
    
    # Remove service file
    if [ -f "/etc/systemd/system/$SERVICE_FILE" ]; then
        rm "/etc/systemd/system/$SERVICE_FILE"
        print_success "Service file removed"
    fi
    
    # Reload systemd
    systemctl daemon-reload
    print_success "Systemd daemon reloaded"
    
    print_success "Uninstallation complete!"
}

show_status() {
    print_info "Auto-Import Status:"
    echo ""
    
    # Show service status if installed
    if [ -f "/etc/systemd/system/$SERVICE_FILE" ]; then
        systemctl status "$SERVICE_FILE" --no-pager || true
        echo ""
    else
        print_info "Service not installed as systemd unit"
        echo ""
    fi
    
    # Show state file info
    if [ -f "$STATE_FILE" ]; then
        print_info "State file content:"
        python3 -m json.tool "$STATE_FILE" | head -20
        echo ""
    else
        print_info "No state file found (no files processed yet)"
        echo ""
    fi
    
    # Show recent log entries
    if [ -f "$LOG_FILE" ]; then
        print_info "Recent log entries:"
        tail -10 "$LOG_FILE"
    else
        print_info "No log file found"
    fi
}

view_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_info "Showing log file (press Ctrl+C to exit):"
        tail -f "$LOG_FILE"
    else
        print_error "Log file not found at $LOG_FILE"
    fi
}

reset_state() {
    print_info "Resetting processed files state..."
    
    if [ -f "$STATE_FILE" ]; then
        # Backup old state
        backup_file="${STATE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$STATE_FILE" "$backup_file"
        print_success "Backed up old state to: $backup_file"
        
        # Remove state file
        rm "$STATE_FILE"
        print_success "State file reset"
    else
        print_info "No state file to reset"
    fi
}

show_help() {
    echo "Auto Import Watcher Management Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  test       Run the script in foreground for testing"
    echo "  install    Install as systemd service (requires sudo)"
    echo "  uninstall  Remove systemd service (requires sudo)"
    echo "  status     Show current status and recent logs"
    echo "  logs       View log file (tail -f)"
    echo "  reset      Reset the processed files state"
    echo "  help       Show this help message"
    echo ""
    echo "Systemd commands (after installation):"
    echo "  sudo systemctl start auto-import.service    # Start service"
    echo "  sudo systemctl stop auto-import.service     # Stop service"
    echo "  sudo systemctl restart auto-import.service  # Restart service"
    echo "  journalctl -u auto-import.service -f        # View systemd logs"
    echo ""
    echo "Directories watched:"
    echo "  ChatGPT: /home/crathmene/data/chatgpt-exports/ (*.json)"
    echo "  Claude:  /home/crathmene/data/claude-exports/ (*.zip)"
    echo ""
    echo "Files:"
    echo "  Log:   $LOG_FILE"
    echo "  State: $STATE_FILE"
}

# Main script logic
case "${1:-}" in
    test)
        test_run
        ;;
    install)
        install_service
        ;;
    uninstall)
        uninstall_service
        ;;
    status)
        show_status
        ;;
    logs)
        view_logs
        ;;
    reset)
        reset_state
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        if [ -n "${1:-}" ]; then
            print_error "Unknown command: $1"
            echo ""
        fi
        show_help
        exit 1
        ;;
esac