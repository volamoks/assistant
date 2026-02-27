#!/bin/bash
# sudo_approve.sh — One-time sudo token manager for OpenClaw agents
#
# Usage:
#   sudo_approve.sh request "<command>"     — Request sudo for a command
#   sudo_approve.sh check [token]           — Check if token is valid (reads from file if not provided)
#   sudo_approve.sh approve [token]         — Approve a pending request
#   sudo_approve.sh deny [token]            — Deny a pending request
#   sudo_approve.sh status                  — Show current sudo status
#   sudo_approve.sh clear                   — Clear all tokens
#
# Token format: <timestamp>:<random>:<command_hash>
# Expiration: 5 minutes (300 seconds)
#

SUDO_DIR="${SUDO_DIR:-/tmp/sudo_approval}"
LOG_FILE="${SUDO_DIR}/audit.log"
TOKEN_TTL=300  # 5 minutes in seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

init_dirs() {
    mkdir -p "$SUDO_DIR"
    touch "$LOG_FILE"
}

log_event() {
    local event_type="$1"
    local token="$2"
    local command="$3"
    local status="$4"
    local timestamp
    timestamp=$(date -Iseconds)
    echo "$timestamp|$event_type|$token|$command|$status" >> "$LOG_FILE"
}

generate_token() {
    local cmd_hash
    cmd_hash=$(echo "$1" | sha256sum | cut -c1-16)
    local random
    random=$(openssl rand -hex 8 2>/dev/null || head -c 16 /dev/urandom | xxd -p)
    local timestamp
    timestamp=$(date +%s)
    echo "${timestamp}:${random}:${cmd_hash}"
}

is_token_valid() {
    local token="$1"
    local stored_token
    stored_token=$(cat "$SUDO_DIR/token" 2>/dev/null)
    
    if [ "$token" != "$stored_token" ]; then
        return 1
    fi
    
    # Check expiration
    local token_timestamp
    token_timestamp=$(echo "$token" | cut -d':' -f1)
    local current_timestamp
    current_timestamp=$(date +%s)
    local age=$((current_timestamp - token_timestamp))
    
    if [ "$age" -gt "$TOKEN_TTL" ]; then
        log_event "EXPIRED" "$token" "" "token expired after ${age}s"
        echo -e "${YELLOW}Token expired${NC}" >&2
        rm -f "$SUDO_DIR/token" "$SUDO_DIR/pending_command"
        return 1
    fi
    
    return 0
}

cmd_request() {
    local command="$1"
    if [ -z "$command" ]; then
        echo "Error: Command required" >&2
        echo "Usage: $0 request \"<command>\"" >&2
        exit 1
    fi
    
    # Check if there's already a pending request
    if [ -f "$SUDO_DIR/token" ]; then
        if is_token_valid "$(cat "$SUDO_DIR/token")"; then
            echo -e "${RED}Error: There's already a pending sudo request${NC}" >&2
            echo "Use 'sudo_approve.sh status' to check current status" >&2
            exit 1
        fi
    fi
    
    local token
    token=$(generate_token "$command")
    
    echo "$token" > "$SUDO_DIR/token"
    echo "$command" > "$SUDO_DIR/pending_command"
    echo "$command" > "$SUDO_DIR/pending_command_display"  # Sanitized for display
    
    log_event "REQUESTED" "$token" "$command" "pending"
    
    echo "Sudo request created:"
    echo "  Token: $token"
    echo "  Command: $command"
    echo "  Expires in: ${TOKEN_TTL}s"
    echo ""
    echo "Ask user to approve with:"
    echo "  /sudo approve $token"
    echo "or click Approve button in Telegram"
}

cmd_check() {
    local token="${1:-$(cat "$SUDO_DIR/token" 2>/dev/null)}"
    
    if [ -z "$token" ]; then
        echo "No sudo token found"
        exit 1
    fi
    
    if is_token_valid "$token"; then
        local command
        command=$(cat "$SUDO_DIR/pending_command" 2>/dev/null)
        echo -e "${GREEN}Sudo access GRANTED${NC}"
        echo "  Token: $token"
        echo "  Command: $command"
        
        # Consume the token (one-time use)
        rm -f "$SUDO_DIR/token" "$SUDO_DIR/pending_command" "$SUDO_DIR/pending_command_display"
        log_event "USED" "$token" "$command" "success"
        
        exit 0
    else
        echo -e "${RED}Sudo access DENIED or EXPIRED${NC}"
        exit 1
    fi
}

cmd_approve() {
    local token="$1"
    
    if [ -z "$token" ]; then
        # If no token provided, approve the pending one
        if [ -f "$SUDO_DIR/token" ]; then
            token=$(cat "$SUDO_DIR/token")
        else
            echo "Error: No pending sudo request" >&2
            exit 1
        fi
    fi
    
    local stored_token
    stored_token=$(cat "$SUDO_DIR/token" 2>/dev/null)
    
    if [ "$token" != "$stored_token" ]; then
        echo -e "${RED}Error: Token mismatch${NC}" >&2
        echo "Provided: $token"
        echo "Expected: $stored_token"
        log_event "APPROVE_FAILED" "$token" "" "token mismatch"
        exit 1
    fi
    
    if ! is_token_valid "$token"; then
        echo -e "${YELLOW}Token expired or invalid${NC}" >&2
        exit 1
    fi
    
    local command
    command=$(cat "$SUDO_DIR/pending_command" 2>/dev/null)
    
    # Mark as approved (but don't consume yet - will be consumed on use)
    echo "approved" > "$SUDO_DIR/status"
    
    log_event "APPROVED" "$token" "$command" "user approved"
    
    echo -e "${GREEN}Sudo approved!${NC}"
    echo "  Token: $token"
    echo "  Command: $command"
    echo ""
    echo "The agent can now execute the command."
}

cmd_deny() {
    local token="$1"
    
    if [ -z "$token" ]; then
        if [ -f "$SUDO_DIR/token" ]; then
            token=$(cat "$SUDO_DIR/token")
        else
            echo "Error: No pending sudo request" >&2
            exit 1
        fi
    fi
    
    local stored_token
    stored_token=$(cat "$SUDO_DIR/token" 2>/dev/null)
    
    if [ "$token" != "$stored_token" ]; then
        echo -e "${RED}Error: Token mismatch${NC}" >&2
        log_event "DENY_FAILED" "$token" "" "token mismatch"
        exit 1
    fi
    
    local command
    command=$(cat "$SUDO_DIR/pending_command" 2>/dev/null)
    
    rm -f "$SUDO_DIR/token" "$SUDO_DIR/pending_command" "$SUDO_DIR/pending_command_display" "$SUDO_DIR/status"
    
    log_event "DENIED" "$token" "$command" "user denied"
    
    echo -e "${RED}Sudo denied${NC}"
    echo "  Token: $token"
    echo "  Command: $command"
}

cmd_status() {
    if [ -f "$SUDO_DIR/token" ]; then
        local token
        token=$(cat "$SUDO_DIR/token")
        
        if is_token_valid "$token"; then
            local command
            command=$(cat "$SUDO_DIR/pending_command" 2>/dev/null)
            local token_timestamp
            token_timestamp=$(echo "$token" | cut -d':' -f1)
            local current_timestamp
            current_timestamp=$(date +%s)
            local remaining=$((TOKEN_TTL - (current_timestamp - token_timestamp)))
            
            echo -e "${GREEN}Pending sudo request:${NC}"
            echo "  Token: $token"
            echo "  Command: $command"
            echo "  Expires in: ${remaining}s"
        else
            echo -e "${YELLOW}Expired sudo request${NC}"
            echo "  Token: $token"
            echo "  (run 'sudo_approve.sh clear' to clean up)"
        fi
    else
        echo "No pending sudo requests"
    fi
}

cmd_clear() {
    rm -f "$SUDO_DIR/token" "$SUDO_DIR/pending_command" "$SUDO_DIR/pending_command_display" "$SUDO_DIR/status"
    echo "Cleared all sudo tokens"
}

cmd_audit() {
    if [ -f "$LOG_FILE" ]; then
        echo "=== Sudo Audit Log ==="
        tail -20 "$LOG_FILE"
    else
        echo "No audit log found"
    fi
}

# Main
init_dirs

case "${1:-}" in
    request)
        cmd_request "$2"
        ;;
    check)
        cmd_check "$2"
        ;;
    approve)
        cmd_approve "$2"
        ;;
    deny)
        cmd_deny "$2"
        ;;
    status)
        cmd_status
        ;;
    clear)
        cmd_clear
        ;;
    audit)
        cmd_audit
        ;;
    *)
        echo "Sudo Approval Manager"
        echo "====================="
        echo ""
        echo "Usage: $0 <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  request \"<command>\"   — Create a new sudo request"
        echo "  check [token]         — Check if sudo is granted (one-time use)"
        echo "  approve [token]        — Approve a sudo request"
        echo "  deny [token]           — Deny a sudo request"
        echo "  status                 — Show current status"
        echo "  clear                  — Clear all tokens"
        echo "  audit                  — Show audit log"
        echo ""
        echo "Token TTL: ${TOKEN_TTL}s"
        exit 1
        ;;
esac
