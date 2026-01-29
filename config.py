"""
Main Bot Configuration File
"""
import os
from dataclasses import dataclass

@dataclass
class SystemFiles:
    """System File Paths"""
    QUEUE = "queue.txt"
    DEFAULT_PLAYLIST = "default_playlist.txt"
    PLAYLIST_STATE = "playlist_state.json"
    HISTORY = "play_history.txt"
    FAILED_REQUESTS = "failed_requests.txt"
    SONG_NOTIFICATIONS = "song_notifications.json"

@dataclass
class StreamSettings:
    """Stream Settings"""
    ZENO_STREAM_URL = "https://stream.zeno.fm/rtgshmfgkmtuv"
    ZENO_SERVER = "link.zeno.fm"
    ZENO_PORT = 80
    ZENO_USERNAME = "source"
    ZENO_MOUNT_POINT = "rtgshmfgkmtuv"
    ZENO_PASSWORD = os.environ.get("ZENO_PASSWORD", "CWfNWegR")
    ZENO_ENCODING = "MP3"  # or AAC
    MIN_SONG_DURATION = 30
    MAX_RETRY_ATTEMPTS = 3
    STREAM_BITRATE = "64k"
    CACHE_DIR = "song_cache"
    
    AUTO_CLEAN_ENABLED = True
    MAX_CACHE_SIZE_MB = 64
    MAX_CACHED_SONGS = 40
    KEEP_USER_CACHE = False
    KEEP_DEFAULT_CACHE = False
    CACHE_CLEAN_INTERVAL_SEC = 120
    PREDOWNLOAD_ENABLED = False
    NO_CACHE = True

@dataclass
class LogSettings:
    """Logging Settings"""
    # Logging Level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    # Use WARNING or ERROR for servers to reduce spam
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

@dataclass
class HighriseSettings:
    """Highrise Settings"""
    BOT_TOKEN = os.environ.get("HIGHRISE_BOT_TOKEN", "3d811b2c88ccbccfc6958cfc15f784b99806acd5c024408d7e21ca38f6941c3d")
    ROOM_ID = os.environ.get("HIGHRISE_ROOM_ID", "663da7935f9d75c3f42bf455")
    OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "Ayysun")
    
    # Manual Moderators List - You can add usernames here directly
    # Example: MODERATORS = ["username1", "username2"]
    # Note: Bot automatically detects moderators/designers/owners and saves them in staff_cache.json
    MODERATORS = []
    
    VIP_PRICE = 600  # VIP Price in Gold

# Default Songs List
DEFAULT_SONGS = [
    "JadaL - I'm in Love with a Wali",
    "JadaL - Yumain o Leila",
    "JadaL - Ana Bakhaf Min El Commit",
    "JadaL - Malyoun",
    "JadaL - El Makina",
    "Massar Egbari - Nehayat El Hakawy",
    "Massar Egbari - Cherrophobia",
    "Massar Egbari - Toaa we Teoum",
    "Massar Egbari - Matloub Habib",
    "Massar Egbari - Ana Hweit",
    "Tamer Hosny - Nasseny Leh",
    "Tamer Hosny - 180 Daraga",
    "Tamer Hosny - Kifayak Aazar",
    "Tamer Hosny - Eish Besho2ak",
    "Tamer Hosny - Helw El Makan",
    "Cairokee - Kan Lak Ma'aya",
    "Cairokee - Marbout Be Astek",
    "Cairokee - El Sekka Shemal",
    "The Weeknd - Blinding Lights",
    "The Weeknd - Save Your Tears",
    "Arctic Monkeys - Do I Wanna Know",
    "Arctic Monkeys - I Wanna Be Yours",
    "Coldplay - Yellow",
    "Coldplay - Viva La Vida",
    "Imagine Dragons - Believer",
    "Imagine Dragons - Demons",
    "Twenty One Pilots - Stressed Out",
    "Billie Eilish - bad guy",
    "Glass Animals - Heat Waves",
    "Harry Styles - As It Was",
    "Adele - Easy On Me",
    "Ed Sheeran - Shape of You",
    "Dua Lipa - Levitating",
    "Post Malone - Circles",
    "The Neighbourhood - Sweater Weather",
    "Tame Impala - The Less I Know The Better",
    "Foster The People - Pumped Up Kicks",
    "Hozier - Take Me To Church",
    "CKay - Love Nwantiti",
    "Rema - Calm Down",
    "Tom Odell - Another Love",
    "Ruth B. - Dandelions",
    "Stephen Sanchez - Until I Found You",
    "JVKE - Golden Hour",
    "d4vd - Here With Me",
    "Sia - Unstoppable",
    "Sia - Chandelier",
    "ZAYN - Dusk Till Dawn",
    "Maroon 5 - Memories",
    "OneRepublic - Counting Stars",
]
