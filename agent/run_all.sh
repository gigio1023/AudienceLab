#!/bin/bash
# Total solution script for MCP-based agent simulation
# This script:
# 1. Installs dependencies if needed
# 2. Starts SNS-Vibe server
# 3. Runs the MCP agent simulation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SNS_VIBE_DIR="$PROJECT_ROOT/sns-vibe"
AGENT_DIR="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
CROWD_COUNT=9
MAX_CONCURRENCY=4
HEADED=""
DRY_RUN=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --crowd-count)
            CROWD_COUNT="$2"
            shift 2
            ;;
        --max-concurrency)
            MAX_CONCURRENCY="$2"
            shift 2
            ;;
        --headed)
            HEADED="--headed"
            shift
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --crowd-count N      Number of crowd agents (default: 9)"
            echo "  --max-concurrency N  Max concurrent agents (default: 4)"
            echo "  --headed             Show browser windows"
            echo "  --dry-run            Skip actual browser actions"
            echo "  --help               Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    if [[ -n "$SNS_PID" ]] && kill -0 "$SNS_PID" 2>/dev/null; then
        log_info "Stopping SNS-Vibe server (PID: $SNS_PID)..."
        kill "$SNS_PID" 2>/dev/null || true
    fi
    # Kill any orphaned processes
    pkill -f "vite.*sns-vibe" 2>/dev/null || true
}

trap cleanup EXIT

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js not found. Please install Node.js 18+."
        exit 1
    fi
    NODE_VERSION=$(node --version | cut -d. -f1 | sed 's/v//')
    if [[ "$NODE_VERSION" -lt 18 ]]; then
        log_error "Node.js 18+ required. Found: $(node --version)"
        exit 1
    fi
    log_success "Node.js $(node --version)"

    # Check npm
    if ! command -v npm &> /dev/null; then
        log_error "npm not found."
        exit 1
    fi
    log_success "npm $(npm --version)"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found."
        exit 1
    fi
    log_success "Python $(python3 --version)"

    # Check uv (optional but preferred)
    if command -v uv &> /dev/null; then
        log_success "uv $(uv --version)"
        USE_UV=1
    else
        log_warn "uv not found. Using pip instead."
        USE_UV=0
    fi
}

# Setup SNS-Vibe
setup_sns_vibe() {
    log_info "Setting up SNS-Vibe..."

    if [[ ! -d "$SNS_VIBE_DIR" ]]; then
        log_error "SNS-Vibe directory not found at: $SNS_VIBE_DIR"
        exit 1
    fi

    cd "$SNS_VIBE_DIR"

    # Install dependencies if needed
    if [[ ! -d "node_modules" ]]; then
        log_info "Installing SNS-Vibe dependencies..."
        npm install
    else
        log_success "SNS-Vibe dependencies already installed"
    fi
}

# Setup Agent Python environment
setup_agent() {
    log_info "Setting up Agent Python environment..."

    cd "$AGENT_DIR"

    if [[ ! -d ".venv" ]]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv .venv
    fi

    # Activate venv
    source .venv/bin/activate

    # Install/update dependencies
    if [[ -f "requirements.txt" ]]; then
        log_info "Installing Python dependencies..."
        if [[ "$USE_UV" -eq 1 ]]; then
            uv pip install -r requirements.txt
        else
            pip install -r requirements.txt
        fi
    fi

    # Install playwright browsers if needed
    if ! python3 -c "from playwright.sync_api import sync_playwright" 2>/dev/null; then
        log_info "Installing Playwright browsers..."
        playwright install chromium
    else
        log_success "Playwright already installed"
    fi
}

# Start SNS-Vibe server
start_sns_vibe() {
    log_info "Starting SNS-Vibe server..."

    cd "$SNS_VIBE_DIR"

    # Kill any existing SNS-Vibe process
    pkill -f "vite.*sns-vibe" 2>/dev/null || true
    sleep 1

    # Start server in background
    npm run dev -- --port 8383 > /tmp/sns-vibe.log 2>&1 &
    SNS_PID=$!

    log_info "SNS-Vibe starting (PID: $SNS_PID)..."

    # Wait for server to be ready
    MAX_WAIT=30
    WAITED=0
    while [[ $WAITED -lt $MAX_WAIT ]]; do
        if curl -s http://localhost:8383 > /dev/null 2>&1; then
            log_success "SNS-Vibe server running at http://localhost:8383"
            return 0
        fi
        sleep 1
        WAITED=$((WAITED + 1))
    done

    log_error "SNS-Vibe server failed to start. Check /tmp/sns-vibe.log"
    cat /tmp/sns-vibe.log
    exit 1
}

# Run agent simulation
run_simulation() {
    log_info "Running MCP agent simulation..."
    log_info "  Crowd count: $CROWD_COUNT"
    log_info "  Max concurrency: $MAX_CONCURRENCY"
    [[ -n "$HEADED" ]] && log_info "  Mode: headed (visible browser)"
    [[ -n "$DRY_RUN" ]] && log_info "  Mode: dry-run"

    cd "$AGENT_DIR"
    source .venv/bin/activate

    # Run the simulation with local Playwright (no MCP server needed)
    python3 cli.py run \
        --crowd-count "$CROWD_COUNT" \
        --max-concurrency "$MAX_CONCURRENCY" \
        $HEADED \
        $DRY_RUN

    log_success "Simulation complete!"
}

# Main
main() {
    echo ""
    echo "=========================================="
    echo " MCP Agent Simulation - Total Solution"
    echo "=========================================="
    echo ""

    check_prerequisites
    setup_sns_vibe
    setup_agent
    start_sns_vibe
    run_simulation
}

main
