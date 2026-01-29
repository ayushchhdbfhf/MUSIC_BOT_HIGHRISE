"""
Main entry point for Highrise Music Bot system
Runs bot and streamer services in separate threads
"""

import logging
import sys
import os
import threading
import time
from pathlib import Path
from datetime import datetime
from config import HighriseSettings, LogSettings, StreamSettings

# Setup logging
logging.basicConfig(
    level=getattr(logging, LogSettings.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('main')

class BotSystemSetup:
    """Class to check environment and required files"""
    
    REQUIRED_FILES = [
        'config.py',
        'highrise_music_bot.py',
        'streamer.py',
        'continuous_playlist_manager.py',
    ]
    
    REQUIRED_DIRS = [
        'song_cache',
        'downloads',
        'backups'
    ]
    
    REQUIRED_DATA_FILES = {
        'default_playlist.txt': '# Default playlist\n',
        'queue.txt': '',
        'owners.json': '[]',
        'vip_users.json': '[]',
        'staff_cache.json': '{}',
        'tickets_data.json': '{}',
        'bot_dances.json': '{}',
        'bot_position.json': '{}',
        'playlist_state.json': '{"current_index": 0, "is_user_request": false}',
        'song_notifications.json': '{}',
        'play_history.txt': ''
    }
    
    @staticmethod
    def check_required_files():
        """Check for required files"""
        logger.info("🔍 Checking required files...")
        missing_files = []
        
        for file in BotSystemSetup.REQUIRED_FILES:
            if not Path(file).exists():
                missing_files.append(file)
        
        if missing_files:
            logger.error(f"❌ Missing files: {', '.join(missing_files)}")
            return False
        
        logger.info("✅ All required files found")
        return True
    
    @staticmethod
    def create_required_directories():
        """Create required directories"""
        logger.info("📁 Creating required directories...")
        
        for dir_path in BotSystemSetup.REQUIRED_DIRS:
            Path(dir_path).mkdir(exist_ok=True)
            logger.info(f"✅ Directory ready: {dir_path}")
    
    @staticmethod
    def create_required_data_files():
        """Create required data files"""
        logger.info("📝 Creating data files...")
        
        for filename, default_content in BotSystemSetup.REQUIRED_DATA_FILES.items():
            file_path = Path(filename)
            if not file_path.exists():
                try:
                    file_path.write_text(default_content)
                    logger.info(f"✅ Created: {filename}")
                except Exception as e:
                    logger.error(f"❌ Failed to create {filename}: {e}")
                    return False
            else:
                logger.info(f"✅ Exists: {filename}")
        
        return True
    
    @staticmethod
    def check_environment_variables():
        """Check environment variables"""
        logger.info("🔐 Checking environment variables...")
        
        required_vars = {
            'HIGHRISE_BOT_TOKEN': 'Bot Token',
            'HIGHRISE_ROOM_ID': 'Room ID',
            'ZENO_PASSWORD': 'Zeno Password'
        }
        
        missing_vars = []
        for var, description in required_vars.items():
            value = os.environ.get(var)
            if not value:
                # Check config.py fallback
                if hasattr(HighriseSettings, var.replace('HIGHRISE_', '')) or hasattr(StreamSettings, var):
                     logger.info(f"✅ {var} found in config.py")
                else:
                    missing_vars.append(f"{var} ({description})")
            else:
                masked_value = value[:4] + "***" + value[-4:] if len(value) > 8 else "***"
                logger.info(f"✅ {var} = {masked_value}")
        
        if missing_vars:
            logger.warning(f"⚠️ Missing environment variables:\n{chr(10).join(f'  • {v}' for v in missing_vars)}")
            logger.warning("⚠️ Bot will attempt to use default values from config.py")
        else:
            logger.info("✅ All environment variables found")
    
    @staticmethod
    def check_python_dependencies():
        """Check required python packages"""
        logger.info("📦 Checking required libraries...")
        
        required_packages = [
            'aiohttp',
            'highrise',
            'requests',
            'yt_dlp',
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
                logger.info(f"✅ {package}")
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            logger.error(f"❌ Missing libraries: {', '.join(missing_packages)}")
            return False
        
        return True
    
    @staticmethod
    def run_all_checks():
        """Run all system checks"""
        logger.info("\n" + "="*60)
        logger.info("🚀 Starting Highrise Music Bot System Check")
        logger.info("="*60 + "\n")
        
        checks = [
            ("Required Files", BotSystemSetup.check_required_files),
            ("Required Libraries", BotSystemSetup.check_python_dependencies),
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            logger.info(f"\n📋 {check_name}...")
            try:
                if not check_func():
                    all_passed = False
                    logger.warning(f"⚠️ Warning: Check failed: {check_name}")
            except Exception as e:
                all_passed = False
                logger.warning(f"⚠️ Warning: Error in check {check_name}: {e}")
        
        logger.info("\n📁 Setting up environment...")
        BotSystemSetup.create_required_directories()
        BotSystemSetup.create_required_data_files()
        
        logger.info("\n🔍 Additional checks...")
        BotSystemSetup.check_environment_variables()
        
        logger.info("\n" + "="*60)
        if all_passed:
            logger.info("✅ All checks passed successfully!")
        else:
            logger.warning("⚠️ Some warnings found, but proceeding startup...")
        logger.info("="*60 + "\n")
        return True

def run_bot():
    """Run Highrise Bot in a separate thread"""
    try:
        time.sleep(1)
        logger.info("🤖 Starting Highrise Bot...")
        
        import subprocess
        backoff = 3
        while True:
            try:
                logger.info("🔌 Connecting to room...")
                bot_runner_path = str(Path(__file__).resolve().parent / 'bot_runner.py')
                result = subprocess.run([sys.executable, bot_runner_path])
                if result.returncode == 0:
                    logger.info("⏹️ Bot stopped normally.")
                else:
                    logger.warning(f"⚠️ Abnormal exit (code={result.returncode}). Restarting in {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                logger.info("🔄 Reconnecting...")
            except Exception as e:
                logger.error(f"❌ Error running bot: {e}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                logger.info("🔄 Retrying...")
    except Exception as e:
        logger.error(f"❌ General bot error: {e}")

def run_streamer():
    """Run Streaming Service"""
    try:
        time.sleep(2)
        logger.info("📡 Starting Streaming Service...")
        from streamer import ZenoStreamer
        backoff = 3
        while True:
            try:
                streamer = ZenoStreamer()
                streamer.run()
                logger.info("⏹️ Streamer stopped normally.")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                logger.info("🔄 Restarting streamer...")
            except MemoryError:
                logger.error("❌ Out of memory. Restarting after delay.")
                time.sleep(max(backoff, 10))
                backoff = min(backoff * 2, 60)
            except Exception as e:
                logger.error(f"❌ Streamer error: {e}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                logger.info("🔄 Restarting streamer...")
    except Exception as e:
        logger.error(f"❌ General streamer error: {e}")

def main():
    """Main execution function"""
    
    try:
        base_dir = Path(__file__).resolve().parent
        os.chdir(base_dir)
        logger.info(f"📂 Changed working directory to: {base_dir}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to change directory: {e}")
    
    try:
        logger.info(f"🐍 Python: {sys.version.split()[0]} | Exec: {sys.executable}")
    except Exception:
        pass
    
    BotSystemSetup.run_all_checks()
    
    logger.info("🚀 Starting Highrise Music Bot System")
    logger.info("="*60)
    logger.info(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60 + "\n")
    
    logger.info("🔄 Starting services...\n")
    
    bot_thread = threading.Thread(target=run_bot, daemon=False, name="HighriseBot")
    streamer_thread = threading.Thread(target=run_streamer, daemon=False, name="ZenoStreamer")
    
    logger.info("✅ Starting Bot Service")
    bot_thread.start()
    
    logger.info("✅ Starting Streamer Service")
    streamer_thread.start()
    
    logger.info("\n" + "="*60)
    logger.info("✨ All services started successfully!")
    logger.info("🤖 Bot is now online in the room!")
    logger.info("📡 Stream is active on Zeno.fm")
    logger.info("="*60 + "\n")
    
    # Initial skip signal to ensure stream starts immediately
    try:
        Path("skip_signal.txt").touch()
        logger.info("🚀 Initial skip signal sent to start stream immediately.")
    except Exception as e:
        logger.error(f"⚠️ Failed to send initial skip signal: {e}")

    # Keep-alive loop
    try:
        counter = 0
        while True:
            time.sleep(1)
            counter += 1
            if counter >= 300: # Log every 5 minutes
                logger.info(f"💓 System Heartbeat - Active for {counter}s")
                counter = 0
    except KeyboardInterrupt:
        logger.info("\n⏹️ Stop signal received, shutting down services...")
        logger.info("✅ System stopped")
        sys.exit(0)

if __name__ == "__main__":
    main()
