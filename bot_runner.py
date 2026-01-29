#!/usr/bin/env python3
"""
Highrise Bot Standalone Runner
Using Highrise SDK Modular Build
"""

import sys
import os
import subprocess
import logging

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s UTC - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bot_runner')

def ensure_highrise():
    try:
        import highrise  # noqa: F401
        return True
    except Exception as e:
        logger.error(f"❌ highrise SDK not available: {e}")
        return False

def main():
    try:
        from config import HighriseSettings
        logger.info("🤖 Starting Highrise Bot...")
        logger.info(f"🎯 Room: {HighriseSettings.ROOM_ID}")
        logger.info(f"🔑 Token: {HighriseSettings.BOT_TOKEN[:8]}...")
    except Exception as e:
        logger.error(f"❌ Setup Error: {e}")
        return 1
    
    ensure_highrise()
    backoff = 3
    while True:
        try:
            rc = use_alternative_method()
            if rc == 0:
                return 0
        except KeyboardInterrupt:
            logger.info("⏹️ Bot stopped by KeyboardInterrupt")
            return 0
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        try:
            import time
            logger.info(f"🔄 Retrying in {backoff} seconds...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception:
            pass

def use_alternative_method():
    try:
        import asyncio
        from config import HighriseSettings
        from highrise import __main__
        from highrise.__main__ import BotDefinition
        from highrise_music_bot import MusicBot
        async def run():
            try:
                definitions = [BotDefinition(MusicBot(), HighriseSettings.ROOM_ID, HighriseSettings.BOT_TOKEN)]
                await __main__.main(definitions)
                return 0
            except Exception as e:
                logger.error(f"❌ SDK Error: {e}")
                import traceback
                traceback.print_exc()
                return 1
        return asyncio.run(run())
    except Exception as e:
        logger.error(f"❌ Alternative method failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    main()
