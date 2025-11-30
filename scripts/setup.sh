#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

info "Detected: $OS ($ARCH)"

# =============================================================================
# macOS Setup
# =============================================================================
setup_macos() {
    info "Setting up macOS dependencies..."

    # Check for Homebrew
    if ! command -v brew &>/dev/null; then
        warn "Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    success "Homebrew installed"

    # System dependencies
    BREW_DEPS=(
        portaudio      # Audio capture (gordonklaus/portaudio)
        protobuf       # Protobuf compiler
        ffmpeg         # Audio processing (faster-whisper)
        python@3.12    # Python runtime
        go             # Go runtime
        node           # Node.js for frontend
    )

    info "Installing Homebrew packages..."
    for dep in "${BREW_DEPS[@]}"; do
        if brew list "$dep" &>/dev/null; then
            success "$dep already installed"
        else
            info "Installing $dep..."
            brew install "$dep"
            success "$dep installed"
        fi
    done

    # Ensure Python 3.12 is linked
    if ! command -v python3.12 &>/dev/null; then
        brew link python@3.12
    fi
}

# =============================================================================
# Linux Setup (Debian/Ubuntu)
# =============================================================================
setup_linux_debian() {
    info "Setting up Debian/Ubuntu dependencies..."

    # Update package list
    sudo apt-get update

    # System dependencies
    APT_DEPS=(
        # Audio
        portaudio19-dev
        libportaudio2
        # Protobuf
        protobuf-compiler
        # FFmpeg for faster-whisper
        ffmpeg
        # Python
        python3.12
        python3.12-venv
        python3-pip
        # Build tools
        build-essential
        pkg-config
        # Screen capture (one of these)
        gnome-screenshot
        # SQLite for ChromaDB
        libsqlite3-dev
    )

    info "Installing apt packages..."
    sudo apt-get install -y "${APT_DEPS[@]}" || {
        # Fallback: try without python3.12 (use default python3)
        warn "python3.12 not available, trying default python3..."
        APT_DEPS=("${APT_DEPS[@]/python3.12/python3}")
        APT_DEPS=("${APT_DEPS[@]/python3.12-venv/python3-venv}")
        sudo apt-get install -y "${APT_DEPS[@]}"
    }

    # Install Go if not present
    if ! command -v go &>/dev/null; then
        info "Installing Go..."
        GO_VERSION="1.24.0"
        wget -q "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -O /tmp/go.tar.gz
        sudo rm -rf /usr/local/go
        sudo tar -C /usr/local -xzf /tmp/go.tar.gz
        echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
        export PATH=$PATH:/usr/local/go/bin
        rm /tmp/go.tar.gz
    fi
    success "Go installed"

    # Install Node.js if not present
    if ! command -v node &>/dev/null; then
        info "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    success "Node.js installed"
}

# =============================================================================
# Linux Setup (Fedora/RHEL)
# =============================================================================
setup_linux_fedora() {
    info "Setting up Fedora/RHEL dependencies..."

    DNF_DEPS=(
        portaudio-devel
        protobuf-compiler
        ffmpeg
        python3.12
        python3-pip
        gcc
        gcc-c++
        make
        pkg-config
        gnome-screenshot
        sqlite-devel
    )

    sudo dnf install -y "${DNF_DEPS[@]}"

    # Install Go
    if ! command -v go &>/dev/null; then
        sudo dnf install -y golang
    fi

    # Install Node.js
    if ! command -v node &>/dev/null; then
        sudo dnf install -y nodejs npm
    fi
}

# =============================================================================
# Linux Setup (Arch)
# =============================================================================
setup_linux_arch() {
    info "Setting up Arch Linux dependencies..."

    PACMAN_DEPS=(
        portaudio
        protobuf
        ffmpeg
        python
        python-pip
        base-devel
        pkg-config
        gnome-screenshot
        sqlite
        go
        nodejs
        npm
    )

    sudo pacman -Syu --noconfirm "${PACMAN_DEPS[@]}"
}

# =============================================================================
# Verify Installations
# =============================================================================
verify_deps() {
    info "Verifying installations..."
    local failed=0

    # Check each dependency
    check_cmd() {
        if command -v "$1" &>/dev/null; then
            success "$1: $(command -v "$1")"
        else
            error "$1 not found!"
            failed=1
        fi
    }

    check_pkg_config() {
        if pkg-config --exists "$1" 2>/dev/null; then
            success "pkg-config $1: found"
        else
            warn "pkg-config $1: not found (may still work)"
        fi
    }

    check_cmd go
    check_cmd python3
    check_cmd node
    check_cmd npm
    check_cmd protoc
    check_cmd ffmpeg
    check_pkg_config portaudio-2.0

    if [[ $failed -eq 1 ]]; then
        error "Some dependencies are missing!"
    fi

    success "All system dependencies verified!"
}

# =============================================================================
# Project Setup
# =============================================================================
setup_project() {
    info "Setting up project dependencies..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    cd "$PROJECT_ROOT"

    # Go tools
    info "Installing Go tools..."
    go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest
    go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest
    success "Go tools installed"

    # Python venv
    info "Setting up Python virtual environment..."
    cd backend/inference
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
    success "Python dependencies installed"
    cd "$PROJECT_ROOT"

    # Go modules
    info "Setting up Go modules..."
    cd backend/platform
    go mod tidy
    success "Go modules ready"
    cd "$PROJECT_ROOT"

    # Node modules
    info "Setting up Node.js dependencies..."
    cd frontend
    npm install
    success "Node.js dependencies installed"
    cd "$PROJECT_ROOT"

    # Generate protobufs
    info "Generating protobuf files..."
    make proto
    success "Protobuf files generated"
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo ""
    echo "======================================"
    echo "  Good Listener - Setup Script"
    echo "======================================"
    echo ""

    case "$OS" in
        Darwin)
            setup_macos
            ;;
        Linux)
            # Detect distro
            if [[ -f /etc/debian_version ]]; then
                setup_linux_debian
            elif [[ -f /etc/fedora-release ]] || [[ -f /etc/redhat-release ]]; then
                setup_linux_fedora
            elif [[ -f /etc/arch-release ]]; then
                setup_linux_arch
            else
                error "Unsupported Linux distribution. Please install dependencies manually."
            fi
            ;;
        *)
            error "Unsupported OS: $OS"
            ;;
    esac

    verify_deps
    setup_project

    echo ""
    success "=========================================="
    success "  Setup complete! Run 'make dev' to start"
    success "=========================================="
    echo ""
}

# Run with optional flags
case "${1:-}" in
    --deps-only)
        case "$OS" in
            Darwin) setup_macos ;;
            Linux)
                if [[ -f /etc/debian_version ]]; then setup_linux_debian
                elif [[ -f /etc/fedora-release ]]; then setup_linux_fedora
                elif [[ -f /etc/arch-release ]]; then setup_linux_arch
                fi
                ;;
        esac
        verify_deps
        ;;
    --project-only)
        setup_project
        ;;
    --verify)
        verify_deps
        ;;
    *)
        main
        ;;
esac

