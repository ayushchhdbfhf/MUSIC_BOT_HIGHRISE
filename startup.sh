#!/bin/bash
echo "============================================================"
echo "🚀 Highrise Music Bot - Startup Script"
echo "============================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
echo "📋 Checking Python..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python 3 not found!${NC}"
    echo "Please install Python 3.10 or higher"
    exit 1
fi

# Check pip
echo "📋 Checking pip..."
if command_exists pip3; then
    echo -e "${GREEN}✅ pip3 found${NC}"
else
    echo -e "${YELLOW}⚠️ pip3 not found, trying pip...${NC}"
    if ! command_exists pip; then
        echo -e "${RED}❌ pip not found!${NC}"
        exit 1
    fi
fi

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt --quiet --upgrade 2>/dev/null || pip install -r requirements.txt --quiet --upgrade

# Check and install yt-dlp
echo ""
echo "📋 Checking yt-dlp..."
if command_exists yt-dlp; then
    YTDLP_VERSION=$(yt-dlp --version 2>&1)
    echo -e "${GREEN}✅ yt-dlp version: $YTDLP_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️ yt-dlp not found in PATH, installing...${NC}"
    pip3 install -U "yt-dlp[default]" 2>/dev/null || pip install -U "yt-dlp[default]"
    
    # Try to add to PATH
    if [ -d "$HOME/.local/bin" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
    
    if command_exists yt-dlp; then
        echo -e "${GREEN}✅ yt-dlp installed successfully${NC}"
    else
        echo -e "${YELLOW}⚠️ yt-dlp will be used via Python module${NC}"
    fi
fi

# Check FFmpeg
echo ""
echo "📋 Checking FFmpeg..."
if command_exists ffmpeg; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n1)
    echo -e "${GREEN}✅ $FFMPEG_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️ FFmpeg not found!${NC}"
    echo "Attempting to install FFmpeg..."
    
    # Try different package managers
    if command_exists apt-get; then
        sudo apt-get update && sudo apt-get install -y ffmpeg 2>/dev/null
    elif command_exists yum; then
        sudo yum install -y ffmpeg 2>/dev/null
    elif command_exists pacman; then
        sudo pacman -S --noconfirm ffmpeg 2>/dev/null
    elif command_exists brew; then
        brew install ffmpeg 2>/dev/null
    elif command_exists apk; then
        apk add --no-cache ffmpeg 2>/dev/null
    fi
    
    if command_exists ffmpeg; then
        echo -e "${GREEN}✅ FFmpeg installed successfully${NC}"
    else
        echo -e "${RED}❌ Could not install FFmpeg automatically${NC}"
        echo "Please install FFmpeg manually:"
        echo "  Ubuntu/Debian: sudo apt-get install ffmpeg"
        echo "  CentOS/RHEL: sudo yum install ffmpeg"
        echo "  macOS: brew install ffmpeg"
        echo "  Alpine: apk add ffmpeg"
        exit 1
    fi
fi

# Check FFprobe
echo ""
echo "📋 Checking FFprobe..."
if command_exists ffprobe; then
    echo -e "${GREEN}✅ ffprobe found${NC}"
else
    echo -e "${RED}❌ ffprobe not found (usually comes with FFmpeg)${NC}"
fi

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p song_cache downloads backups
echo -e "${GREEN}✅ Directories ready${NC}"

# Check environment variables
echo ""
echo "🔐 Checking environment variables..."
MISSING_VARS=0

if [ -z "$HIGHRISE_BOT_TOKEN" ]; then
    echo -e "${YELLOW}⚠️ HIGHRISE_BOT_TOKEN not set${NC}"
    MISSING_VARS=1
fi

if [ -z "$HIGHRISE_ROOM_ID" ]; then
    echo -e "${YELLOW}⚠️ HIGHRISE_ROOM_ID not set${NC}"
    MISSING_VARS=1
fi

if [ -z "$ZENO_PASSWORD" ]; then
    echo -e "${YELLOW}⚠️ ZENO_PASSWORD not set${NC}"
    MISSING_VARS=1
fi

if [ $MISSING_VARS -eq 0 ]; then
    echo -e "${GREEN}✅ All environment variables set${NC}"
else
    echo -e "${YELLOW}⚠️ Some environment variables missing - will use defaults from config.py${NC}"
fi

echo ""
echo "============================================================"
echo -e "${GREEN}🚀 Starting Highrise Music Bot...${NC}"
echo "============================================================"
echo ""

# Run the bot
python3 main.py
