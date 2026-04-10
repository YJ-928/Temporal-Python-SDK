#!/usr/bin/env bash

# Start Temporal development server (local mode)
# Automatically installs the Temporal CLI if not found.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TEMPORAL_INSTALL_DIR="$HOME/.temporalio/bin"

# ---------------------------------------------------------------------------
# Detect temporal: check PATH first, then the known install dir.
# If found in the install dir but not in PATH, add it silently.
# ---------------------------------------------------------------------------
detect_temporal() {
    if command -v temporal &>/dev/null; then
        return 0  # already in PATH
    fi
    if [[ -x "$TEMPORAL_INSTALL_DIR/temporal" ]]; then
        # Installed but not in PATH — add it for this session
        export PATH="$TEMPORAL_INSTALL_DIR:$PATH"
        echo -e "${YELLOW}Temporal found at $TEMPORAL_INSTALL_DIR but not in PATH.${NC}"
        echo -e "${YELLOW}Add the following to your shell profile to make it permanent:${NC}"
        echo ""
        echo "      export PATH=\"\$HOME/.temporalio/bin:\$PATH\""
        echo ""
        return 0
    fi
    return 1  # not found anywhere
}

# ---------------------------------------------------------------------------
# Install via the official Temporal install script (works on Linux & macOS)
# ---------------------------------------------------------------------------
install_via_script() {
    echo -e "${BLUE}Downloading and running the official Temporal CLI install script...${NC}"
    if command -v curl &>/dev/null; then
        curl -sSf https://temporal.download/cli.sh | sh
    elif command -v wget &>/dev/null; then
        wget -qO- https://temporal.download/cli.sh | sh
    else
        echo -e "${RED}Neither curl nor wget is available. Please install one and retry.${NC}"
        exit 1
    fi
    # Make the freshly installed binary available in this session
    export PATH="$TEMPORAL_INSTALL_DIR:$PATH"
}

# ---------------------------------------------------------------------------
# Check for Temporal CLI; install only if missing
# ---------------------------------------------------------------------------
if detect_temporal; then
    echo -e "${GREEN}Temporal CLI found: $(temporal --version)${NC}"
else
    echo -e "${YELLOW}Temporal CLI not found. Attempting installation...${NC}"

    OS="$(uname -s)"

    case "$OS" in
        Darwin)
            if command -v brew &>/dev/null; then
                echo -e "${BLUE}macOS detected — installing via Homebrew...${NC}"
                brew install temporal
            else
                echo -e "${YELLOW}Homebrew not found. Falling back to the install script...${NC}"
                install_via_script
            fi
            ;;
        Linux)
            echo -e "${BLUE}Linux detected — installing via the official install script...${NC}"
            install_via_script
            ;;
        *)
            echo -e "${RED}Unsupported operating system: $OS${NC}"
            echo "Please install the Temporal CLI manually:"
            echo "  https://docs.temporal.io/cli#install"
            exit 1
            ;;
    esac

    # Final verification
    if ! detect_temporal; then
        echo -e "${RED}Installation finished but 'temporal' could not be located.${NC}"
        echo "Try opening a new terminal or sourcing your shell profile, then re-run this script."
        exit 1
    fi

    echo -e "${GREEN}Temporal CLI installed successfully: $(temporal --version)${NC}"
fi

# ---------------------------------------------------------------------------
# Start the dev server
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}Starting Temporal development server...${NC}"
echo -e "  ${BLUE}gRPC endpoint :${NC} localhost:7233"
echo -e "  ${BLUE}Web UI        :${NC} http://localhost:8233"
echo ""
echo "Press Ctrl+C to stop."
echo ""

temporal server start-dev
