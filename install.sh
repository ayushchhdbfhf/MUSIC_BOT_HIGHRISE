#!/bin/bash
echo "============================================================"
echo "🔧 Highrise Music Bot - Installation Script"
echo "============================================================"
echo "This script installs all dependencies for bot hosting"
echo "============================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    elif [ -f /etc/debian_version ]; then
        OS="debian"
    elif [ -f /etc/redhat-release ]; then
        OS="centos"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        OS="unknown"
    fi
    echo -e "${BLUE}📱 Detected OS: $OS${NC}"
}

# Install system dependencies
install_system_deps() {
    echo ""
    echo -e "${BLUE}📦 Installing system dependencies...${NC}"
    
    case $OS in
        ubuntu|debian|pop)
            echo "Using apt-get..."
            sudo apt-get update -qq
            sudo apt-get install -y python3 python3-pip python3-venv ffmpeg curl wget
            ;;
        centos|rhel|fedora)
            echo "Using yum/dnf..."
            sudo yum install -y python3 python3-pip ffmpeg curl wget || \
            sudo dnf install -y python3 python3-pip ffmpeg curl wget
            ;;
        arch|manjaro)
            echo "Using pacman..."
            sudo pacman -Syu --noconfirm python python-pip ffmpeg curl wget
            ;;
        alpine)
            echo "Using apk..."
            apk add --no-cache python3 py3-pip ffmpeg curl wget
            ;;
        macos)
            echo "Using Homebrew..."
            if ! command -v brew &> /dev/null; then
                echo "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install python ffmpeg curl wget
            ;;
        *)
            echo -e "${YELLOW}⚠️ Unknown OS. Please install manually:${NC}"
            echo "  - Python 3.10+"
            echo "  - pip3"
            echo "  - FFmpeg"
            echo "  - curl, wget"
            ;;
    esac
}

# Install Python packages
install_python_deps() {
    echo ""
    echo -e "${BLUE}📦 Installing Python packages...${NC}"
    
    # Upgrade pip first
    python3 -m pip install --upgrade pip --quiet 2>/dev/null || pip3 install --upgrade pip --quiet 2>/dev/null
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        python3 -m pip install -r requirements.txt --quiet 2>/dev/null || pip3 install -r requirements.txt --quiet 2>/dev/null
        echo -e "${GREEN}✅ Python packages installed${NC}"
    else
        echo -e "${RED}❌ requirements.txt not found!${NC}"
        echo "Installing core packages manually..."
        pip3 install aiohttp highrise-bot-sdk "yt-dlp[default]" imageio-ffmpeg
    fi
}

# Install yt-dlp binary (alternative method)
install_ytdlp_binary() {
    echo ""
    echo -e "${BLUE}📦 Installing yt-dlp binary...${NC}"
    
    # Download latest yt-dlp binary
    YTDLP_URL="https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
    
    if command -v curl &> /dev/null; then
        curl -L $YTDLP_URL -o yt-dlp 2>/dev/null
    elif command -v wget &> /dev/null; then
        wget -q $YTDLP_URL -O yt-dlp
    else
        echo -e "${YELLOW}⚠️ curl/wget not found, using pip install${NC}"
        pip3 install -U "yt-dlp[default]"
        return
    fi
    
    chmod +x yt-dlp
    
    # Try to move to system path
    if [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
        mv yt-dlp /usr/local/bin/
        echo -e "${GREEN}✅ yt-dlp installed to /usr/local/bin${NC}"
    elif [ -d "$HOME/.local/bin" ]; then
        mkdir -p "$HOME/.local/bin"
        mv yt-dlp "$HOME/.local/bin/"
        export PATH="$HOME/.local/bin:$PATH"
        echo -e "${GREEN}✅ yt-dlp installed to ~/.local/bin${NC}"
    else
        echo -e "${GREEN}✅ yt-dlp binary downloaded to current directory${NC}"
    fi
}

# Setup directories
setup_directories() {
    echo ""
    echo -e "${BLUE}📁 Creating directories...${NC}"
    mkdir -p song_cache downloads backups
    echo -e "${GREEN}✅ Directories created${NC}"
}

# Create default files
setup_files() {
    echo ""
    echo -e "${BLUE}📝 Setting up data files...${NC}"
    
    # Create empty files if they don't exist
    [ ! -f "queue.txt" ] && touch queue.txt
    [ ! -f "play_history.txt" ] && touch play_history.txt
    [ ! -f "vip_users.json" ] && echo "[]" > vip_users.json
    [ ! -f "tickets_data.json" ] && echo "{}" > tickets_data.json
    [ ! -f "staff_cache.json" ] && echo "{}" > staff_cache.json
    [ ! -f "playlist_state.json" ] && echo "{\"current_default_index\": 0, \"current_song\": null, \"is_playing_user_request\": false}" > playlist_state.json
    [ ! -f "song_notifications.json" ] && echo "{}" > song_notifications.json
    [ ! -f "owners.json" ] && echo "[]" > owners.json
    
    echo -e "${GREEN}✅ Data files ready${NC}"
}

# Verify installation
verify_installation() {
    echo ""
    echo "============================================================"
    echo -e "${BLUE}🔍 Verifying installation...${NC}"
    echo "============================================================"
    
    ERRORS=0
    
    # Python
    if command -v python3 &> /dev/null; then
        VERSION=$(python3 --version)
        echo -e "${GREEN}✅ $VERSION${NC}"
    else
        echo -e "${RED}❌ Python 3 not found${NC}"
        ERRORS=$((ERRORS + 1))
    fi
    
    # pip
    if command -v pip3 &> /dev/null; then
        echo -e "${GREEN}✅ pip3 found${NC}"
    else
        echo -e "${RED}❌ pip3 not found${NC}"
        ERRORS=$((ERRORS + 1))
    fi
    
    # FFmpeg
    if command -v ffmpeg &> /dev/null; then
        echo -e "${GREEN}✅ FFmpeg found${NC}"
    else
        echo -e "${RED}❌ FFmpeg not found${NC}"
        ERRORS=$((ERRORS + 1))
    fi
    
    # yt-dlp
    if command -v yt-dlp &> /dev/null || [ -f "./yt-dlp" ]; then
        echo -e "${GREEN}✅ yt-dlp found${NC}"
    else
        # Check if available as Python module
        if python3 -c "import yt_dlp" 2>/dev/null; then
            echo -e "${GREEN}✅ yt-dlp (Python module) found${NC}"
        else
            echo -e "${RED}❌ yt-dlp not found${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    fi
    
    # Python packages
    echo ""
    echo "Checking Python packages..."
    PACKAGES=("aiohttp" "highrise" "requests" "yt_dlp" "flask")
    for pkg in "${PACKAGES[@]}"; do
        if python3 -c "import $pkg" 2>/dev/null; then
            echo -e "${GREEN}  ✅ $pkg${NC}"
        else
            echo -e "${RED}  ❌ $pkg${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    done
    
    echo ""
    if [ $ERRORS -eq 0 ]; then
        echo -e "${GREEN}============================================================${NC}"
        echo -e "${GREEN}✅ All dependencies installed successfully!${NC}"
        echo -e "${GREEN}============================================================${NC}"
        echo ""
        echo "To start the bot, run:"
        echo "  ./startup.sh"
        echo "  or"
        echo "  python3 main.py"
    else
        echo -e "${RED}============================================================${NC}"
        echo -e "${RED}❌ $ERRORS errors found. Please fix them before running.${NC}"
        echo -e "${RED}============================================================${NC}"
    fi
}

# Main installation
main() {
    detect_os
    install_system_deps
    install_python_deps
    install_ytdlp_binary
    setup_directories
    setup_files
    verify_installation
}

# Run main
main
