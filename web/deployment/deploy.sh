#!/bin/bash
# Deployment script for Conversation Search Flask application
# This script helps install and manage the systemd service

set -e

SERVICE_NAME="conversation-search.service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"
LOG_FILE="/var/log/conversation-search.log"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if running as root (needed for systemd operations)
check_root() {
    if [[ $EUID -eq 0 ]]; then
        return 0
    else
        return 1
    fi
}

install_service() {
    print_info "Installing Conversation Search service..."
    
    # Check if running as root
    if ! check_root; then
        print_error "This operation requires root privileges. Please run with sudo."
        exit 1
    fi
    
    # Copy service file
    print_info "Copying service file to systemd directory..."
    cp "${CURRENT_DIR}/${SERVICE_NAME}" "$SERVICE_FILE"
    print_success "Service file copied"
    
    # Create log file with proper permissions
    print_info "Creating log file with proper permissions..."
    touch "$LOG_FILE"
    chown crathmene:crathmene "$LOG_FILE"
    print_success "Log file created"
    
    # Reload systemd
    print_info "Reloading systemd daemon..."
    systemctl daemon-reload
    print_success "Systemd daemon reloaded"
    
    # Enable service
    print_info "Enabling service to start on boot..."
    systemctl enable "$SERVICE_NAME"
    print_success "Service enabled"
    
    print_success "Installation complete!"
    print_info "To start the service, run: sudo systemctl start ${SERVICE_NAME}"
}

uninstall_service() {
    print_info "Uninstalling Conversation Search service..."
    
    if ! check_root; then
        print_error "This operation requires root privileges. Please run with sudo."
        exit 1
    fi
    
    # Stop service if running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_info "Stopping service..."
        systemctl stop "$SERVICE_NAME"
        print_success "Service stopped"
    fi
    
    # Disable service
    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        print_info "Disabling service..."
        systemctl disable "$SERVICE_NAME"
        print_success "Service disabled"
    fi
    
    # Remove service file
    if [[ -f "$SERVICE_FILE" ]]; then
        print_info "Removing service file..."
        rm "$SERVICE_FILE"
        print_success "Service file removed"
    fi
    
    # Reload systemd
    print_info "Reloading systemd daemon..."
    systemctl daemon-reload
    print_success "Systemd daemon reloaded"
    
    print_success "Uninstallation complete!"
    print_info "Log file preserved at: $LOG_FILE"
}

start_service() {
    if ! check_root; then
        print_error "This operation requires root privileges. Please run with sudo."
        exit 1
    fi
    
    print_info "Starting Conversation Search service..."
    systemctl start "$SERVICE_NAME"
    print_success "Service started"
    systemctl status "$SERVICE_NAME" --no-pager
}

stop_service() {
    if ! check_root; then
        print_error "This operation requires root privileges. Please run with sudo."
        exit 1
    fi
    
    print_info "Stopping Conversation Search service..."
    systemctl stop "$SERVICE_NAME"
    print_success "Service stopped"
}

restart_service() {
    if ! check_root; then
        print_error "This operation requires root privileges. Please run with sudo."
        exit 1
    fi
    
    print_info "Restarting Conversation Search service..."
    systemctl restart "$SERVICE_NAME"
    print_success "Service restarted"
    systemctl status "$SERVICE_NAME" --no-pager
}

status_service() {
    systemctl status "$SERVICE_NAME" --no-pager
}

view_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        print_info "Showing last 50 lines of log file (press Ctrl+C to exit):"
        tail -n 50 -f "$LOG_FILE"
    else
        print_error "Log file not found at $LOG_FILE"
    fi
}

show_help() {
    echo "Conversation Search Service Deployment Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install    Install and enable the systemd service (requires sudo)"
    echo "  uninstall  Stop and remove the systemd service (requires sudo)"
    echo "  start      Start the service (requires sudo)"
    echo "  stop       Stop the service (requires sudo)"
    echo "  restart    Restart the service (requires sudo)"
    echo "  status     Show service status"
    echo "  logs       View service logs (tail -f)"
    echo "  help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  sudo $0 install    # Install the service"
    echo "  sudo $0 start      # Start the service"
    echo "  $0 status          # Check service status"
    echo "  $0 logs            # View logs"
}

# Main script logic
case "${1:-}" in
    install)
        install_service
        ;;
    uninstall)
        uninstall_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    logs)
        view_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: ${1:-}"
        echo ""
        show_help
        exit 1
        ;;
esac