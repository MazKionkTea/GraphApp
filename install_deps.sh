#!/usr/bin/env bash
# Graph App — install system-level build dependencies (Rust, etc.)
# Run this ONCE if pip install fails with "Failed to build pydantic-core"

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  Graph App — Installing system build dependencies"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Detect distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO="$ID"
else
    DISTRO="unknown"
fi

echo "Detected distro: $DISTRO"
echo ""

case "$DISTRO" in
    arch|manjaro|endeavouros|garuda)
        echo "→ Installing Rust toolchain + base-devel (Arch)…"
        echo "  (requires sudo)"
        sudo pacman -S --needed --noconfirm base-devel rust
        ;;
    debian|ubuntu|pop|mint|elementary)
        echo "→ Installing build-essential + rustc (Debian/Ubuntu)…"
        echo "  (requires sudo)"
        sudo apt update
        sudo apt install -y build-essential rustc cargo
        ;;
    fedora|rhel|centos|rocky|almalinux)
        echo "→ Installing gcc + rust (Fedora/RHEL)…"
        echo "  (requires sudo)"
        sudo dnf install -y gcc gcc-c++ rust cargo
        ;;
    opensuse*)
        echo "→ Installing gcc + rust (openSUSE)…"
        echo "  (requires sudo)"
        sudo zypper install -y gcc rust
        ;;
    *)
        echo "  Unknown distro. Please install manually:"
        echo "    - A C/C++ compiler (gcc/clang)"
        echo "    - The Rust toolchain (https://rustup.rs/)"
        echo ""
        echo "  Or alternatively, on most systems, you can avoid building"
        echo "  by ensuring pip uses pre-built wheels:"
        echo "    pip install --only-binary=:all: pydantic-core"
        echo ""
        exit 1
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✓ System dependencies installed."
echo ""
echo "  Now retry:"
echo "    ./start.sh"
echo "═══════════════════════════════════════════════════════════"
