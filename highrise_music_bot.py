#!/usr/bin/env python3
"""
Highrise Music Bot Control
"""

import asyncio
import json
import logging
import os
import re
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta
from highrise import BaseBot, User, Position, AnchorPosition
from highrise.models import SessionMetadata, GetMessagesRequest
from config import HighriseSettings, SystemFiles, StreamSettings, LogSettings

# Define logger before import with timezone offset
import time
logging.Formatter.converter = time.gmtime  # Use UTC
logging.basicConfig(
    level=getattr(logging, LogSettings.LOG_LEVEL, logging.WARNING),
    format='%(asctime)s UTC - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('highrise_bot')


class BotResponses:
    STARTUP_MESSAGE = ("🎵 Hi! I'm the music bot. Type !play to request a song", "music")
    WELCOME_MESSAGE = """🎉 Welcome {username}!
📋 Available commands:
!play <song name> - Request a song (requires a ticket)
!np - See the currently playing song
!queue - View the queue
!skip - Skip current song (VIP/Staff only)
!tickets - Check your tickets
!ticketslist - See all users with tickets
!listowners - See all owners
💡 Send a tip to the bot to get tickets (10g = 5 tickets)"""
    PLAY_NO_SONG_NAME = ("❌ Please write the song name. Example: !play Fairuz", "error")
    SEARCHING = ("🔍 Searching for: {query}...", "info")
    SEARCH_TIMEOUT = ("⏱️ Search took too long. Please try again", "warning")
    SEARCH_FAILED = ("❌ Search failed, please try again", "error")
    NO_RESULTS = ("❌ No results found", "error")
    SEARCH_ERROR = ("❌ An error occurred during search", "error")
    SEARCH_RESULTS = ("🎵 Results for '{query}':{remaining_time}", "music")
    CHOOSE_SONG_MORE = ("Enter the song number or + to see more", "info")
    CHOOSE_SONG = ("Enter the song number", "info")
    NO_MORE_RESULTS = ("❌ No more results", "error")
    INVALID_CHOICE = ("❌ Invalid choice. Choose from 1 to {max}", "error")
    SONG_ADDED = ("✅ Done, added: {title}\n⏱️ Duration: {duration}", "success")
    SELECTION_ERROR = ("❌ An error occurred during selection", "error")
    SONG_REQUESTED = """<#FF69B4>@{username} Requested:
<#00FFFF>♫ {title}
<#FFD700>⏱️ Duration: {duration}
<#87CEEB>👁️ Views: {views}
<#90EE90>📅 Released: {released}
<#FFA500>📋 Queue Position: #{position}"""
    NOW_PLAYING = """🎶 Now playing:
'{title}'

{elapsed} [{progress_bar}] {total}

Requested by: @{username}"""
    NOW_PLAYING_DEFAULT = """🎶 Now playing:
'{title}'

{elapsed} [{progress_bar}] {total}"""
    NO_SONG_INFO = ("🎵 No information about the current song", "music")
    SONG_INFO_ERROR = ("❌ An error occurred while fetching information", "error")
    SONG_SKIPPED = """<#FF4500>⏭️ Skipped:
<#00FFFF>{title}
<#FFD700>👤 By @{username}"""
    QUEUE_EMPTY = ("📋 The queue is empty", "info")
    QUEUE_STATUS = ("📋 Queue ({count} requests):", "info")
    QUEUE_SONG_ITEM = ("{number}. {song}", "default")
    QUEUE_MORE_ITEMS = ("... and {count} more", "info")
    SKIPPING_DEFAULT_FOR_REQUEST = ("⏭️ Skipping default song to play your request...", "info")
    SKIP_NOT_OWNER = ("❌ Sorry {username}, this command is for the owner only ({owner})", "error")
    SKIPPING_SONG = ("⏭️ Skipping song...", "info")
    SKIP_SUCCESS = ("✅ Song skipped\n🎵 Next: {next_song}", "success")
    SKIP_TRYING = ("⚠️ Trying to skip...", "warning")
    INVALID_QUEUE_INDEX = ("❌ Invalid number. Choose from 1 to {max}", "error")
    PLAYING_FROM_QUEUE = ("🎵 Playing '{song}' from queue, requested by @{username}", "music")
    SKIP_ERROR = ("❌ An error occurred while skipping", "error")
    DPLAY_NO_QUERY = ("❌ Please write part of the song name. Example: !dplay Fairuz", "error")
    DPLAY_NO_PLAYLIST = ("⚠️ Default playlist is empty or does not exist.", "warning")
    DPLAY_NOT_FOUND = ("❌ No song matching '{query}' found in default playlist.", "error")
    DPLAY_SUCCESS = ("🎵 Playing '{song}' from default playlist...", "music")
    RMQUEUE_NO_INDEX = ("❌ Please specify the song number to delete. Example: !rmqueue 1", "error")
    RMQUEUE_INVALID_INDEX = ("❌ Invalid number. Choose from 1 to {max}", "error")
    RMQUEUE_SUCCESS = ("🗑️ Song #{index} ('{title}') deleted by @{username}", "success")
    NO_DANCES_SAVED = ("⚠️ No dances saved for the bot", "warning")
    DANCE_STARTED = ("💃 Started dancing! ({count} dances)", "dance")
    DANCE_ALREADY_RUNNING = ("💃 I'm already dancing!", "dance")
    DANCE_ALREADY_STOPPED = ("⚠️ Dancing is already stopped", "warning")
    DANCE_STOPPED = ("⏹️ Stopped dancing", "warning")
    NO_TICKETS = ("❌ Sorry {username}, you don't have any tickets. Buy 5 tickets for 10g", "error")
    TICKET_USED = ("✅ One ticket deducted. Remaining: {remaining} tickets", "success")
    TICKETS_INFO = ("🎫 You have {count} tickets", "info")
    TIP_RECEIVED = ("💰 Thanks {username}!\nReceived {gold}g and got {tickets} tickets\n🎫 Total tickets: {total}", "success")
    TIP_TOO_SMALL = ("❌ Sorry {username}, the tip is too small. Minimum 10g required to get tickets", "warning")
    TICKETS_LIST = ("📋 Users with tickets:", "info")
    NO_USERS_WITH_TICKETS = ("📋 No users have tickets", "info")
    USER_TICKET_ITEM = ("🎫 {username}: {tickets} tickets", "default")
    DUPLICATE_SONG_IN_QUEUE = ("⚠️ Song '{title}' is already in the queue.", "warning")
    COMMANDS_LIST = """📋 Available commands:
!play <song> - Request a song
!np - Now playing
!queue - View queue
!tickets - Check tickets
!skip - Skip song (VIP/Staff)"""
    VIP_RECEIVED = ("⭐ Congratulations {username}!\n💎 You are now VIP\n✨ Unlimited !play and !skip access", "success")
    VIP_ALREADY = ("⭐ {username} is already VIP", "warning")
    VIP_SKIP_UNLIMITED = ("⏭️ Unlimited skip", "info")
    NOT_VIP_OR_STAFF = ("❌ Sorry {username}, this command is for VIP, Staff, or Owner only", "error")
    VIP_PLAY_UNLIMITED = ("🎵 Unlimited requests (no tickets needed)", "info")
    STAFF_DETECTED = ("🔑 {username} detected as {privilege} - Unlimited access granted", "success")
    VIP_REMINDER = ("💎 Want unlimited songs?\n⭐ Subscribe to VIP for {price}g!\n✨ Unlimited requests + Unlimited skip", "info")
    TIME_REMAINING = ("⏰ Time remaining: {minutes}:{seconds:02d}\n🎵 Next: {next_song}", "default")
    SEARCH_RESULT_ITEM = ("{number}. {title} ({duration})", "default")
    STREAM_STARTING = ("🎵 Starting live streaming service", "info")
    STREAM_SEARCHING = ("🔍 Searching for: {query}", "info")
    STREAM_DOWNLOADING = ("⬇️ Downloading: {title}", "info")
    STREAM_PLAYING = ("▶️ Now streaming: {title}", "music")
    STREAM_ENDED = ("✅ Stream ended: {title}", "success")
    STREAM_ERROR = ("❌ Error during streaming: {error}", "error")
    STREAM_DOWNLOAD_ERROR = ("❌ Download failed: {error}", "error")
    STREAM_RETRY = ("🔄 Retrying... ({attempt}/{max_attempts})", "warning")
    STREAM_SKIP_SIGNAL = ("⏭️ Skip signal detected", "info")
    STREAM_SWITCHING_DEFAULT = ("🎶 Switching to default song", "info")
    STREAM_NO_SONGS = ("⚠️ No songs available", "warning")
    STREAM_QUEUE_EMPTY = ("📋 Queue is empty", "info")
    PLAYLIST_LOADED = ("✅ Loaded {count} default songs", "success")
    PLAYLIST_LOADED_ERROR = ("❌ Failed to load default playlist", "error")
    PLAYLIST_CREATED = ("✅ Created default playlist with {count} songs", "success")
    PLAYLIST_STATE_LOADED = ("✅ Loaded saved playback state", "success")
    PLAYLIST_STATE_NOT_FOUND = ("⚠️ No saved state found", "warning")
    PLAYLIST_STATE_LOAD_ERROR = ("❌ Failed to load playlist state", "error")
    PLAYLIST_STATE_SAVED = ("✅ Playlist state saved", "success")
    PLAYLIST_STATE_SAVE_ERROR = ("❌ Failed to save playlist state", "error")
    PLAYLIST_USER_REQUEST = ("🎵 User request (preview, attempt {attempt}): {song}", "info")
    PLAYLIST_DEFAULT_SONG = ("🎶 Default song: {song}", "info")
    PLAYLIST_REQUEST_SUCCESS = ("✅ Successfully started user request: {song}", "success")
    PLAYLIST_REQUEST_DELETED = ("✅ Request deleted after successful playback", "success")
    PLAYLIST_REQUEST_FAILED = ("❌ Request failed {song} - Attempt {attempt}/{max_attempts}", "error")
    PLAYLIST_MAX_ATTEMPTS = ("⚠️ Max attempts reached for: {song}", "warning")
    PLAYLIST_MOVED_TO_END = ("🔄 Failed request moved to end of queue: {song}", "info")
    PLAYLIST_SONG_FINISHED = ("✅ Song finished: {song}", "success")
    PLAYLIST_QUEUE_CLEARED = ("🧹 Queue cleared (empty)", "info")
    PLAYLIST_SONG_ADDED = ("✅ Song added to default playlist: {song}", "success")
    PLAYLIST_SONG_EXISTS = ("⚠️ Song already exists: {song}", "warning")
    PLAYLIST_SONG_REMOVED = ("✅ Song removed: {song}", "success")
    PLAYLIST_SONG_NOT_FOUND = ("⚠️ Song not found in playlist: {song}", "warning")
    PLAYLIST_NOW_PLAYING = ("▶️ Now playing: {song}", "music")
    PLAYLIST_END = ("✅ Playlist ended", "info")
    PLAYLIST_USING_DEFAULT = ("🎶 Using default playlist", "info")
    PLAYLIST_EMPTY = ("⚠️ Playlist is empty", "warning")
    PLAYLIST_SONG_SKIPPED = ("⏭️ Song skipped: {song}", "info")
    PLAYLIST_MANAGER_STARTED = ("🎵 Continuous playlist manager started", "info")
    PLAYLIST_NO_SONGS_AVAILABLE = ("⚠️ No songs available", "warning")
    STREAM_SKIP_IGNORED_DOWNLOADING = ("🔒 Skip signal ignored - downloading user request", "info")
    STREAM_SKIP_DEFAULT_FOR_USER = ("⏭️ Skipping default song to play user request immediately", "info")
    STREAM_DEFAULT_STOPPED = ("✅ Default song stopped", "success")
    STREAM_SKIP_DEFAULT_SPECIAL = ("⏭️ Skipping default song (special signal)", "info")
    STREAM_SKIP_IGNORED_USER_REQUEST = ("🔒 Skip signal ignored - current song is user request", "info")
    STREAM_SKIP_CURRENT_FOR_USER = ("⏭️ Skipping current song to play user request immediately", "info")
    SYSTEM_STARTING = ("🚀 Starting Highrise Music Bot system", "info")
    SYSTEM_BOT_STARTING = ("🤖 Starting Highrise bot...", "info")
    SYSTEM_STREAMER_STARTING = ("📡 Starting streaming service...", "info")
    SYSTEM_STOPPING = ("⏹️ Stopping system...", "info")
    SYSTEM_TOKEN_MISSING = ("❌ Please set HIGHRISE_BOT_TOKEN and HIGHRISE_ROOM_ID in Secrets", "error")
    BOT_VIP_REMINDER_SENT = ("💎 VIP reminder sent", "info")
    BOT_STAFF_CHECK_PERIODIC = ("🔍 Starting periodic staff check...", "info")
    BOT_STAFF_CHECK_INITIAL = ("🔍 Starting initial staff check...", "info")
    BOT_NO_NEW_STAFF = ("✅ No new staff found", "success")
    BOT_NO_DANCES_SAVED = ("⚠️ No dances saved for continuous dancing", "warning")
    BOT_CONTINUOUS_DANCE_STARTED = ("✅ Continuous dancing started", "success")
    BOT_CONTINUOUS_DANCE_STOPPED = ("⏹️ Continuous dancing stopped", "info")
    OWNER_ONLY_COMMAND = ("❌ Sorry {username}, this command is for the main owner only ({owner})", "error")
    ADDOWNER_NO_USERNAME = ("❌ Please specify the username. Example: !add username", "error")
    ADDOWNER_SUCCESS = ("✅ {username} added as additional owner", "success")
    ADDOWNER_ALREADY_OWNER = ("⚠️ {username} is already an additional owner", "warning")
    ADDOWNER_ALREADY_MAIN_OWNER = ("⚠️ This is the main owner account", "warning")
    REMOVEOWNER_NO_USERNAME = ("❌ Please specify the username. Example: !rem username", "error")
    REMOVEOWNER_SUCCESS = ("✅ {username} removed from additional owners", "success")
    REMOVEOWNER_NOT_OWNER = ("⚠️ {username} is not an additional owner", "warning")
    REMOVEOWNER_CANNOT_REMOVE_MAIN = ("❌ Cannot remove the main owner", "error")
    LISTOWNERS_HEADER = ("👑 Owners List:", "info")
    LISTOWNERS_MAIN_OWNER = ("👑 Main Owner: {username}", "success")
    LISTOWNERS_ADDITIONAL_OWNER = ("⭐ Additional Owner: {username}", "default")
    LISTOWNERS_NO_ADDITIONAL = ("ℹ️ No additional owners", "info")
    ADDTICKETS_NO_ARGS = ("❌ Usage: !addtickets <username> <amount>", "error")
    ADDTICKETS_SUCCESS = ("✅ Added {tickets} tickets to {username}\n🎫 New Balance: {total}", "success")
    WITHDRAW_NO_ARGS = ("❌ Usage: !withdraw <username> [amount]\nExample: !withdraw user 10 to withdraw 10 tickets\nOr: !withdraw user to withdraw all", "error")
    WITHDRAW_SUCCESS = ("✅ Withdrew all tickets from {username} ({tickets} tickets)", "success")
    WITHDRAW_AMOUNT_SUCCESS = ("✅ Withdrew {tickets} tickets from {username}\n🎫 Remaining: {remaining}", "success")
    WITHDRAW_NO_TICKETS = ("⚠️ {username} has no tickets", "warning")
    WITHDRAWALL_SUCCESS = ("✅ Withdrew all tickets from {count} users\n🎫 Total: {total} tickets", "success")
    WITHDRAWALL_NO_USERS = ("⚠️ No users have tickets", "warning")
    ALLTK_NO_AMOUNT = ("❌ Usage: -alltk <amount>", "error")
    ALLTK_SUCCESS = ("✅ Gave {tickets} tickets to {count} users", "success")
    FREE_NO_USERNAME = ("❌ Usage: -free <username>", "error")
    FREE_SUCCESS = ("✅ {username} is now VIP for free!", "success")
    FREE_ALREADY = ("⚠️ {username} is already VIP", "warning")
    UNFREE_NO_USERNAME = ("❌ Usage: -unfree <username>", "error")
    UNFREE_SUCCESS = ("✅ Removed VIP from {username}", "success")
    UNFREE_NOT_VIP = ("⚠️ {username} is not VIP", "warning")
    BALANCE_INFO = ("💰 Wallet Balance: {balance}g", "info")
    SYNC_SUCCESS = ("✅ Wallet synced\n💰 Balance: {balance}g", "success")
    SYNC_ERROR = ("❌ Sync failed", "error")
    GIVE_NO_ARGS = ("❌ Usage: -give <username> <amount>", "error")
    GIVE_SUCCESS = ("✅ Sent {amount}g to {username}", "success")
    GIVE_INSUFFICIENT = ("❌ Insufficient balance", "error")
    CLEARQUEUE_SUCCESS = ("✅ Queue cleared ({count} songs)", "success")
    CLEARQUEUE_EMPTY = ("⚠️ Queue is already empty", "warning")
    MAXQUEUE_NO_NUMBER = ("❌ Usage: -maxqueue <number>", "error")
    MAXQUEUE_SUCCESS = ("✅ Queue limit set to: {max} songs", "success")
    MAXREQUESTS_NO_NUMBER = ("❌ Usage: -maxrequests <number>", "error")
    MAXREQUESTS_SUCCESS = ("✅ Requests limit set to: {max} per user", "success")
    DEV_MODE_INFO = ("🔧 Developer Mode: {status}\n📊 Stats: {stats}", "info")
    DEV_ON = ("✅ Developer Mode Enabled", "success")
    DEV_OFF = ("✅ Developer Mode Disabled", "success")
    RESET_CONFIRM_REQUIRED = ("⚠️ This will delete all data!\nTo confirm type: confirm reset", "warning")
    RESET_SUCCESS = ("✅ All data has been reset", "success")
    TICKET_PRICE_LIST = """<#FF69B4>💰 Ticket Prices: 
 50G   = 3  ticket 
 100G  = 6  ticket 
 500G  = 30 ticket 
 600G  = VIP ⭐"""
    VERIFY_SUCCESS = ("✅ You were granted 3 tickets via -hello\n🎫 Your balance: {total}", "success")
    VERIFY_ALREADY_USED = ("⚠️ You have used -hello before", "warning")
    ADMIN_ONLY = ("❌ This command is for Room Owner, Bot Owner, or Developers only", "error")
    ADDMOD_SUCCESS = ("✅ {username} added as developer", "success")
    ADDMOD_ALREADY = ("⚠️ {username} is already a developer", "warning")
    RMOD_SUCCESS = ("✅ {username} removed from developers", "success")
    RMOD_NOT_FOUND = ("⚠️ {username} is not a developer", "warning")
    COMMAND_ERROR = ("❌ An error occurred while executing the command", "error")
    HELP_MENU = """<#BA55D3>🔧 Manager 🔧 

Choose: 
1️⃣ Normal Commands 
2️⃣ Manager Commands 

Reply with: 1 or 2 (You must be owner to use option 2)"""
    HELP_USER_PAGE1 = """<#FF69B4>🎵 Commands 🎵 

🎶 -play — Request song 
🎵 -np — Now Playing 
📋 -queue — Queue 
🎫 -wallet — Tickets 
💰 -rlist — Prices 
📞 hello — 3 Tickets"""
    HELP_USER_PAGE2 = """<#FF69B4>⏭️ -next — Next Song 
⏩ -skip — Skip 
🔎 -dump N — Info 
▶️ -dplay text — From Default 
🗑️ -rmqueue N — Remove from Queue 
🎁 -gift [song] @user — Gift Song
💸 -give [amount] @user — Transfer
❤️ -like | -unlike — Like Song
⭐ -addfav — Add to Favorites
❓ -help — This Message"""
    HELP_MANAGER_USERS = """<#BA55D3>👥 Management: 
-add @user — Add Owner 
-rem @user — Rem Owner 
-addv @user — Add VIP 
-remv @user — Rem VIP 
-listowners — List Owners 
-removeowner @user — Remove Owner"""
    HELP_MANAGER_MONEY1 = """<#BA55D3>💰 Tickets: 
-addtickets @user N — Add 
-give @user N — Give Tickets (Owner)
-withdraw @user [N] — Withdraw 
-withdrawall — Withdraw All 
-alltk N — Give All 
-ticketslist — List Tickets
-check @user — Check Balance"""
    HELP_MANAGER_MONEY2 = """<#BA55D3>💰 Wallet: 
-bwallet — Balance 
-sync — Sync Wallet"""
    HELP_MANAGER_SETTINGS = """<#BA55D3>⚙️ Settings: 
<#BA55D3>-clearqueue — Clear Queue 
<#BA55D3>-cleancache — Clean Cache 
<#BA55D3>-cacheinfo — Cache Info 
<#BA55D3>-maxqueue N — Max Queue 
<#BA55D3>-maxrequests N — Max Requests 
<#BA55D3>-equip @user — Copy Outfit 
<#BA55D3>-equipid id — Equip by ID 
<#BA55D3>-cbit — Bitrate 
<#BA55D3>-fplay [name|index] — Play Fav
<#BA55D3>-setbot — Teleport Bot 
<#BA55D3>-invite — Invite Verified 
<#BA55D3>-reset — Reset (Type: confirm reset)
<#BA55D3>-dance — Toggle Dance
<#BA55D3>-autotip [amount] — Auto Tip"""
    INFO_SECTION = """<#BA55D3>📊 Info & Fun: 
-accs — Top 10 Tickets 
-info @user — User Info + Tickets 
-block @user — Block User 
-unblock @user — Unblock User 
-sblocked — Show Blocked
-lb — Leaderboard
-summon @user — Summon User
-tipall — Tip All
-randomtip [amount] — Random Tip"""


class TicketsSystem:
    def __init__(self, tickets_file: str = "tickets_data.json", vip_file: str = "vip_users.json", dev_file: str = "dev_users.json", subs_file: str = "subscribers.json", mod_file: str = "moderators.json", blocked_file: str = "blocked_users.json", song_stats_file: str = "song_stats.json"):
        self.tickets_file = tickets_file
        self.vip_file = vip_file
        self.dev_file = dev_file
        self.subs_file = subs_file
        self.mod_file = mod_file
        self.blocked_file = blocked_file
        self.song_stats_file = song_stats_file
        self.regen_file = "tickets_regen.json"
        self.tickets_data = {}
        self.vip_users = {}  # Changed to dict for rich data
        self.dev_users = []
        self.moderators = []
        self.subscribers = []
        self.blocked_users = []
        self.song_stats = {}
        self.regen_data = {}
        self.autotip_amount = 0
        self._ensure_file_exists()
        self._load_data()
        self._verify_key = "__verify_used_users"
        self._ticket_price = 1  # Default 1 gold per ticket

    def _ensure_file_exists(self):
        if not Path(self.tickets_file).exists():
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        if not Path(self.vip_file).exists():
            with open(self.vip_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        if not Path(self.dev_file).exists():
            with open(self.dev_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        if not Path(self.subs_file).exists():
            with open(self.subs_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        if not Path(self.mod_file).exists():
            with open(self.mod_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        if not Path(self.blocked_file).exists():
            with open(self.blocked_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        if not Path(self.song_stats_file).exists():
            with open(self.song_stats_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        if not Path(self.regen_file).exists():
            with open(self.regen_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

    def _load_data(self):
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                self.tickets_data = json.load(f)
        except:
            self.tickets_data = {}
        try:
            with open(self.vip_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Migrate old list format to dict
                    self.vip_users = {u: {"expiry": None, "daily_songs": 0, "daily_gifts": 0, "last_reset": str(datetime.now().date())} for u in data}
                else:
                    self.vip_users = data
        except:
            self.vip_users = {}
        try:
            with open(self.dev_file, 'r', encoding='utf-8') as f:
                self.dev_users = json.load(f)
        except:
            self.dev_users = []
        try:
            with open(self.mod_file, 'r', encoding='utf-8') as f:
                self.moderators = json.load(f)
        except:
            self.moderators = []
        try:
            with open(self.subs_file, 'r', encoding='utf-8') as f:
                self.subscribers = json.load(f)
        except:
            self.subscribers = []
        try:
            with open(self.blocked_file, 'r', encoding='utf-8') as f:
                self.blocked_users = json.load(f)
        except:
            self.blocked_users = []
        try:
            with open(self.song_stats_file, 'r', encoding='utf-8') as f:
                self.song_stats = json.load(f)
        except:
            self.song_stats = {}
        try:
            with open(self.regen_file, 'r', encoding='utf-8') as f:
                self.regen_data = json.load(f)
        except:
            self.regen_data = {}

    def save_blocked(self):
        with open(self.blocked_file, 'w', encoding='utf-8') as f:
            json.dump(self.blocked_users, f, ensure_ascii=False, indent=2)

    def save_vip(self):
        with open(self.vip_file, 'w', encoding='utf-8') as f:
            json.dump(self.vip_users, f, ensure_ascii=False, indent=2)

    def save_song_stats(self):
        with open(self.song_stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.song_stats, f, ensure_ascii=False, indent=2)

    def is_blocked(self, username: str) -> bool:
        return username in self.blocked_users

    def block_user(self, username: str):
        if username not in self.blocked_users:
            self.blocked_users.append(username)
            self.save_blocked()
            return True
        return False

    def unblock_user(self, username: str):
        if username in self.blocked_users:
            self.blocked_users.remove(username)
            self.save_blocked()
            return True
        return False

    def add_vip(self, username: str, days: int = 15):
        expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        self.vip_users[username] = {
            "expiry": expiry,
            "daily_songs": 0,
            "daily_gifts": 0,
            "last_reset": str(datetime.now().date())
        }
        self.save_vip()
        return True

    def remove_vip(self, username: str):
        if username in self.vip_users:
            del self.vip_users[username]
            self.save_vip()
            return True
        return False

    def is_vip(self, username: str) -> bool:
        if username not in self.vip_users:
            return False
        data = self.vip_users[username]
        if data.get("expiry"):
            expiry = datetime.strptime(data["expiry"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expiry:
                self.remove_vip(username)
                return False
        return True

    def get_vip_data(self, username: str):
        return self.vip_users.get(username)

    def check_vip_daily_limit(self, username: str, limit_type: str = "songs") -> bool:
        if not self.is_vip(username):
            return False
        data = self.vip_users[username]
        today = str(datetime.now().date())
        
        # Reset if new day
        if data.get("last_reset") != today:
            data["daily_songs"] = 0
            data["daily_gifts"] = 0
            data["last_reset"] = today
            self.save_vip()
        
        if limit_type == "songs":
            return data.get("daily_songs", 0) < 50
        elif limit_type == "gifts":
            return data.get("daily_gifts", 0) < 5
        return False

    def increment_vip_usage(self, username: str, limit_type: str = "songs"):
        if username in self.vip_users:
            data = self.vip_users[username]
            if limit_type == "songs":
                data["daily_songs"] = data.get("daily_songs", 0) + 1
            elif limit_type == "gifts":
                data["daily_gifts"] = data.get("daily_gifts", 0) + 1
            self.save_vip()

    def record_song_play(self, song_title: str):
        self.song_stats[song_title] = self.song_stats.get(song_title, 0) + 1
        self.save_song_stats()

    def set_autotip_amount(self, amount: int):
        self.autotip_amount = amount
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data["__autotip_amount"] = amount
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving autotip: {e}")

    def get_autotip_amount(self) -> int:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("__autotip_amount", 0)
        except:
            return 0

    def get_top_songs(self, limit: int = 5):
        return sorted(self.song_stats.items(), key=lambda x: x[1], reverse=True)[:limit]

    def add_like(self, song_title: str):
        # We can store likes in song_stats or a new file. 
        # For simplicity, let's use a new key in song_stats or just a separate dict in memory for now?
        # User wants "displays total likes". 
        # I'll use song_stats_file but with a specific key suffix or a new file.
        # Let's use a new file "song_likes.json" to be clean.
        pass # Will implement in main class or here. 
        # Actually, let's just use song_stats for Plays and a new dict for Likes.



    def check_regeneration(self, username: str):
        try:
            with open(self.regen_file, 'r', encoding='utf-8') as f:
                regen_data = json.load(f)
            
            now = datetime.now()
            last_regen_str = regen_data.get(username)
            
            if not last_regen_str:
                # Initialize new user with 5 free tickets if not exists
                with open(self.tickets_file, 'r', encoding='utf-8') as f:
                    tickets_data = json.load(f)
                
                if username not in tickets_data:
                    tickets_data[username] = 5
                    with open(self.tickets_file, 'w', encoding='utf-8') as f:
                        json.dump(tickets_data, f, ensure_ascii=False, indent=2)
                
                regen_data[username] = str(now)
                with open(self.regen_file, 'w', encoding='utf-8') as f:
                    json.dump(regen_data, f, ensure_ascii=False, indent=2)
                return

            try:
                last_regen = datetime.strptime(last_regen_str, "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                try:
                    last_regen = datetime.strptime(last_regen_str, "%Y-%m-%d %H:%M:%S")
                except:
                    last_regen = now

            diff = now - last_regen
            minutes = diff.total_seconds() / 60
            
            if minutes >= 25:
                intervals = int(minutes // 25)
                if intervals > 0:
                    with open(self.tickets_file, 'r', encoding='utf-8') as f:
                        tickets_data = json.load(f)
                    
                    current = tickets_data.get(username, 0)
                    if current < 5:
                        to_add = intervals
                        if current + to_add > 5:
                            to_add = 5 - current
                        
                        if to_add > 0:
                            tickets_data[username] = current + to_add
                            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                                json.dump(tickets_data, f, ensure_ascii=False, indent=2)
                    
                    # Update regen time
                    if tickets_data.get(username, 0) >= 5:
                        new_regen_time = now
                    else:
                        new_regen_time = last_regen + timedelta(minutes=intervals * 25)
                        
                    regen_data[username] = str(new_regen_time)
                    with open(self.regen_file, 'w', encoding='utf-8') as f:
                        json.dump(regen_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Error in regeneration: {e}")

    def get_user_tickets(self, username: str) -> int:
        self.check_regeneration(username)
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get(username, 0)
        except Exception as e:
            logger.error(f"Error reading tickets: {e}")
            return 0

    def add_tickets(self, username: str, amount: int) -> int:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
            current = data.get(username, 0)
            new_total = current + amount
            data[username] = new_total
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Added {amount} tickets for {username} (Total: {new_total})")
            return new_total
        except Exception as e:
            logger.error(f"Error adding tickets: {e}")
            return 0

    def use_ticket(self, username: str, amount: int = 1) -> bool:
        self.check_regeneration(username)
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            current = data.get(username, 0)
            if current < amount:
                return False
            data[username] = current - amount
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"🎫 {username} used {amount} tickets (Remaining: {current - amount})")
            return True
        except Exception as e:
            logger.error(f"Error using ticket: {e}")
            return False

    def get_all_users_with_tickets(self) -> dict:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {k: v for k, v in data.items() if v > 0}
        except Exception as e:
            logger.error(f"Error reading list: {e}")
            return {}

    def set_user_tickets(self, username: str, amount: int) -> bool:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data[username] = amount
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Set tickets for {username} to {amount}")
            return True
        except Exception as e:
            logger.error(f"Error setting tickets: {e}")
            return False

    def save_tickets(self):
        try:
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump(self.tickets_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving tickets: {e}")

    def save_vip_users(self):
        try:
            with open(self.vip_file, 'w', encoding='utf-8') as f:
                json.dump(self.vip_users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving VIP: {e}")

    def add_dev(self, username: str) -> bool:
        try:
            with open(self.dev_file, 'r', encoding='utf-8') as f:
                devs = json.load(f)
            if username in devs:
                return False
            devs.append(username)
            with open(self.dev_file, 'w', encoding='utf-8') as f:
                json.dump(devs, f, ensure_ascii=False, indent=2)
            self.dev_users = devs
            return True
        except Exception as e:
            logger.error(f"Error adding developer: {e}")
            return False

    def remove_dev(self, username: str) -> bool:
        try:
            with open(self.dev_file, 'r', encoding='utf-8') as f:
                devs = json.load(f)
            if username not in devs:
                return False
            devs.remove(username)
            with open(self.dev_file, 'w', encoding='utf-8') as f:
                json.dump(devs, f, ensure_ascii=False, indent=2)
            self.dev_users = devs
            return True
        except Exception as e:
            logger.error(f"Error removing developer: {e}")
            return False

    def is_dev(self, username: str) -> bool:
        try:
            with open(self.dev_file, 'r', encoding='utf-8') as f:
                devs = json.load(f)
            return username in devs
        except Exception as e:
            logger.error(f"Error reading developers: {e}")
            return False

    def add_moderator(self, username: str) -> bool:
        try:
            with open(self.mod_file, 'r', encoding='utf-8') as f:
                mods = json.load(f)
            if username in mods:
                return False
            mods.append(username)
            with open(self.mod_file, 'w', encoding='utf-8') as f:
                json.dump(mods, f, ensure_ascii=False, indent=2)
            self.moderators = mods
            return True
        except Exception as e:
            logger.error(f"Error adding moderator: {e}")
            return False

    def remove_moderator(self, username: str) -> bool:
        try:
            with open(self.mod_file, 'r', encoding='utf-8') as f:
                mods = json.load(f)
            if username not in mods:
                return False
            mods.remove(username)
            with open(self.mod_file, 'w', encoding='utf-8') as f:
                json.dump(mods, f, ensure_ascii=False, indent=2)
            self.moderators = mods
            return True
        except Exception as e:
            logger.error(f"Error removing moderator: {e}")
            return False

    def is_moderator_user(self, username: str) -> bool:
        try:
            with open(self.mod_file, 'r', encoding='utf-8') as f:
                mods = json.load(f)
            return username in mods
        except Exception as e:
            logger.error(f"Error reading moderators: {e}")
            return False

    def set_ticket_price(self, price: int):
        self._ticket_price = price
        # Could save this to a config file if persistence is needed
        # For now, we will assume it's runtime only or saved in a separate config
        # But user asked to "set slot price manually".
        # I should probably save it. I'll add it to tickets_file or a new config.
        # Let's save it to tickets_file under a special key or separate file.
        # Saving to tickets_file is easier as it's already loaded.
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data["__ticket_price"] = price
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving ticket price: {e}")

    def get_ticket_price(self) -> int:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("__ticket_price", 1)
        except Exception:
            return 1

    def has_used_verify(self, username: str) -> bool:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            used_list = data.get(self._verify_key, [])
            if not isinstance(used_list, list):
                return False
            return username in used_list
        except Exception as e:
            logger.error(f"Error reading verify status: {e}")
            return False

    def mark_verify_used(self, username: str) -> bool:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
            used_list = data.get(self._verify_key, [])
            if not isinstance(used_list, list):
                used_list = []
            if username not in used_list:
                used_list.append(username)
                data[self._verify_key] = used_list
                with open(self.tickets_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error recording verify status: {e}")
            return False

    def get_verified_users(self) -> list:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            used_list = data.get(self._verify_key, [])
            if not isinstance(used_list, list):
                return []
            return used_list
        except Exception as e:
            logger.error(f"Error reading verified list: {e}")
            return []

    def _blocked_key(self) -> str:
        return "__blocked_users"

    def is_blocked(self, username: str) -> bool:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            blocked = data.get(self._blocked_key(), [])
            if not isinstance(blocked, list):
                return False
            return username in blocked
        except Exception as e:
            logger.error(f"Error reading blocked list: {e}")
            return False

    def block_user(self, username: str) -> bool:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
            blocked = data.get(self._blocked_key(), [])
            if not isinstance(blocked, list):
                blocked = []
            if username not in blocked:
                blocked.append(username)
                data[self._blocked_key()] = blocked
                with open(self.tickets_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            return False

    def unblock_user(self, username: str) -> bool:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            blocked = data.get(self._blocked_key(), [])
            if not isinstance(blocked, list):
                blocked = []
            if username in blocked:
                blocked.remove(username)
                data[self._blocked_key()] = blocked
                with open(self.tickets_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error unblocking user: {e}")
            return False

    def list_blocked(self) -> list:
        try:
            with open(self.tickets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            blocked = data.get(self._blocked_key(), [])
            if not isinstance(blocked, list):
                return []
            return blocked
        except Exception as e:
            logger.error(f"Error reading blocked list: {e}")
            return []

    def get_subs(self) -> list:
        try:
            with open(self.subs_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading subscribers: {e}")
            return []

    def add_sub(self, user_id: str, username: str, conversation_id: str = None) -> bool:
        try:
            subs = self.get_subs()
            for sub in subs:
                if sub.get('id') == user_id:
                    if conversation_id and not sub.get('conversation_id'):
                        sub['conversation_id'] = conversation_id
                        with open(self.subs_file, 'w', encoding='utf-8') as f:
                            json.dump(subs, f, ensure_ascii=False, indent=2)
                        self.subscribers = subs
                        return True
                    return False
            new_sub = {
                "id": user_id,
                "username": username,
                "joined_at": datetime.now().isoformat()
            }
            if conversation_id:
                new_sub["conversation_id"] = conversation_id
            subs.append(new_sub)
            with open(self.subs_file, 'w', encoding='utf-8') as f:
                json.dump(subs, f, ensure_ascii=False, indent=2)
            self.subscribers = subs
            return True
        except Exception as e:
            logger.error(f"Error adding subscriber: {e}")
            return False

    def is_owner(self, username: str) -> bool:
        return username in self.dev_users

    def is_moderator(self, username: str) -> bool:
        return False

# ==================== Bot Position Management ====================
def save_bot_position(position_data: dict):
    """Save bot position to file"""
    try:
        with open("bot_position.json", 'w', encoding='utf-8') as f:
            json.dump(position_data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Bot position saved: {position_data}")
    except Exception as e:
        logger.error(f"❌ Error saving bot position: {e}")

def load_bot_position() -> dict:
    """Load bot position from file"""
    try:
        if Path("bot_position.json").exists():
            with open("bot_position.json", 'r', encoding='utf-8') as f:
                position_data = json.load(f)
                logger.info(f"📂 Bot position loaded: {position_data}")
                return position_data
    except Exception as e:
        logger.error(f"❌ Error loading bot position: {e}")
    return None

class MusicBot(BaseBot):
    """Highrise Music Bot"""
    
    def __init__(self):
        super().__init__()
        self.queue_file = SystemFiles.QUEUE
        self.notifications_file = SystemFiles.SONG_NOTIFICATIONS
        self.stream_url = StreamSettings.ZENO_STREAM_URL
        self.current_song = None
        self.bot_dances_file = "bot_dances.json"
        self.favorites_file = "favorites.txt"
        self.staff_cache_file = "staff_cache.json"
        self.owners_file = "owners.json"
        self.default_playlist_file = SystemFiles.DEFAULT_PLAYLIST
        self.owner_username = HighriseSettings.OWNER_USERNAME
        self.bot_username = None  # Will be set on start
        
        # Tickets System
        self.tickets_system = TicketsSystem()
        
        # Continuous Bot Dance System
        self.is_dancing = False
        self.dance_task = None
        
        # Connection Status - For background task control
        self.is_connected = False
        
        # Developer Mode
        self.dev_mode = False
        
        # Store detected staff and designers
        self.detected_staff = self._load_staff_cache()
        
        # Store additional owners
        self.additional_owners = self._load_owners()
        
        # Message delay (in seconds)
        self.message_delay = 0.5
        
        # Save bot position
        self.saved_position = load_bot_position()
        try:
            logger.info(f"🎧 Stream URL for listeners: {self.stream_url}")
        except Exception:
            pass
        
        # Create files if they don't exist
        Path(self.queue_file).touch()
        Path(self.favorites_file).touch()
        if not Path(self.bot_dances_file).exists():
            with open(self.bot_dances_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def _load_staff_cache(self) -> dict:
        """Load saved staff and designers list"""
        if Path(self.staff_cache_file).exists():
            try:
                with open(self.staff_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def is_blocked(self, username: str) -> bool:
        """Check if user is blocked"""
        return username in self.blocked_users

    def block_user(self, username: str) -> bool:
        """Block a user"""
        if username not in self.blocked_users:
            self.blocked_users.append(username)
            self._save_blocked()
            return True
        return False

    def unblock_user(self, username: str) -> bool:
        """Unblock a user"""
        if username in self.blocked_users:
            self.blocked_users.remove(username)
            self._save_blocked()
            return True
        return False
        
    def list_blocked(self) -> list:
        """List all blocked users"""
        return self.blocked_users

    def _save_blocked(self):
        try:
            with open(self.blocked_file, 'w', encoding='utf-8') as f:
                json.dump(self.blocked_users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving blocked users: {e}")

    def get_vip_data(self, username: str) -> dict:
        """Get VIP user data"""
        return self.vip_users.get(username, {})

    def is_vip(self, username: str) -> bool:
        """Check if user is VIP"""
        return username in self.vip_users

    def check_vip_daily_limit(self, username: str, limit_type: str = "songs", max_limit: int = 50) -> bool:
        """Check if VIP user has reached daily limit"""
        if username not in self.vip_users:
            return False
            
        data = self.vip_users[username]
        today = str(datetime.now().date())
        
        # Reset if new day
        if data.get("last_reset") != today:
            data["last_reset"] = today
            data["daily_songs"] = 0
            data["daily_gifts"] = 0
            self._save_vip()
            
        current = data.get(f"daily_{limit_type}", 0)
        return current < max_limit

    def increment_vip_usage(self, username: str, limit_type: str = "songs"):
        """Increment VIP usage"""
        if username in self.vip_users:
            self.vip_users[username][f"daily_{limit_type}"] = self.vip_users[username].get(f"daily_{limit_type}", 0) + 1
            self._save_vip()

    def _save_vip(self):
        try:
            with open(self.vip_file, 'w', encoding='utf-8') as f:
                json.dump(self.vip_users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving VIP users: {e}")

    
    def _load_owners(self) -> list:
        """Load additional owners list"""
        if Path(self.owners_file).exists():
            try:
                with open(self.owners_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_owners(self):
        """Save additional owners list"""
        try:
            with open(self.owners_file, 'w', encoding='utf-8') as f:
                json.dump(self.additional_owners, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ Error saving owners: {e}")
    
    def add_owner(self, username: str) -> bool:
        """Add additional owner"""
        if username not in self.additional_owners:
            self.additional_owners.append(username)
            self._save_owners()
            logger.info(f"✅ Added {username} as additional owner")
            return True
        return False
    
    def remove_owner(self, username: str) -> bool:
        """Remove additional owner"""
        if username in self.additional_owners:
            self.additional_owners.remove(username)
            self._save_owners()
            logger.info(f"✅ Removed {username} from additional owners")
            return True
        return False
    
    def is_owner(self, username: str) -> bool:
        """Check if user is owner (main or additional)"""
        return username == self.owner_username or username in self.additional_owners
    
    async def is_management_allowed(self, user: User) -> bool:
        if self.is_owner(user.username):
            return True
        try:
            if self.tickets_system.is_dev(user.username):
                return True
            if self.tickets_system.is_moderator_user(user.username):
                return True
        except Exception:
            pass
        try:
            privilege = await self.highrise.get_room_privilege(user.id)
            if isinstance(privilege, str) and privilege == "owner":
                return True
        except:
            pass
        return self.detected_staff.get(user.username) == "Developer"
    
    def _normalize_youtube_url(self, url: str) -> str:
        """Normalize YouTube URL to base format (e.g. https://www.youtube.com/watch?v=VIDEO_ID)"""
        match = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|v/|shorts/|live/))([\w-]{11})", url)
        if match:
            return f"https://www.youtube.com/watch?v={match.group(1)}"
        return url # Return original URL if not a known YouTube format
    
    async def is_main_owner(self, user: User) -> bool:
        """Check if user is owner (for management commands)"""
        try:
            if self.tickets_system.is_dev(user.username):
                return True
        except Exception:
            pass
        return self.is_owner(user.username)
    
    def colorize(self, message: str, color_type: str = "default") -> str:
        """Add color to message start based on type"""
        colors = {
            "default": "#FFD700",    # Gold
            "success": "#00FF00",    # Green
            "error": "#FF0000",      # Red
            "info": "#00BFFF",       # Light Blue
            "warning": "#FFA500",    # Orange
            "music": "#FF69B4",      # Pink
            "dance": "#9370DB"       # Purple
        }
        color = colors.get(color_type, colors["default"])
        return f"<{color}>{message}"
    
    async def send_whisper_safe(self, user: User, message: str):
        try:
            await self.highrise.send_whisper(user.id, message)
        except Exception:
            pass
    
    async def send_whisper_long(self, user: User, message: str, max_len: int = 240):
        try:
            text = str(message)
            chunks = []
            current = ""
            for line in text.splitlines():
                sep = "\n" if current else ""
                if len(current) + len(sep) + len(line) <= max_len:
                    current = current + (sep + line if sep else line)
                else:
                    if current:
                        chunks.append(current)
                    if len(line) <= max_len:
                        current = line
                    else:
                        start = 0
                        while start < len(line):
                            end = min(start + max_len, len(line))
                            chunks.append(line[start:end])
                            start = end
                        current = ""
            if current:
                chunks.append(current)
            for c in chunks:
                await self.send_whisper_safe(user, c)
        except Exception:
            await self.send_whisper_safe(user, text[:max_len])

    async def send_chat_long(self, message: str, color: str = None):
        """Send a long message to chat, splitting it if necessary"""
        try:
            text = str(message)
            max_len = 250 # Safe margin below 255
            chunks = []
            current = ""
            
            for line in text.splitlines():
                sep = "\n" if current else ""
                if len(current) + len(sep) + len(line) <= max_len:
                    current = current + (sep + line if sep else line)
                else:
                    if current:
                        chunks.append(current)
                    if len(line) <= max_len:
                        current = line
                    else:
                        start = 0
                        while start < len(line):
                            end = min(start + max_len, len(line))
                            chunks.append(line[start:end])
                            start = end
                        current = ""
            if current:
                chunks.append(current)
            
            for c in chunks:
                if color:
                    await self.highrise.chat(self.colorize(c, color))
                else:
                    await self.highrise.chat(c)
                await asyncio.sleep(0.5) # Anti-spam delay
        except Exception as e:
            logger.error(f"Error sending long chat: {e}")
            await self.highrise.chat(text[:max_len] if not color else self.colorize(text[:max_len], color))

    
    def _mk_item(self, id: str, active_palette: int = -1):
        return {
            "type": "clothing",
            "amount": 1,
            "id": id,
            "account_bound": False,
            "active_palette": active_palette
        }
    
    def _normalize_outfit(self, items):
        ids = [i.get("id") if isinstance(i, dict) else getattr(i, "id", "") for i in (items or [])]
        out = []
        for i in (items or []):
            if isinstance(i, dict):
                out.append(i)
            else:
                out.append({
                    "type": getattr(i, "type", "clothing"),
                    "amount": getattr(i, "amount", 1),
                    "id": getattr(i, "id", ""),
                    "account_bound": getattr(i, "account_bound", False),
                    "active_palette": getattr(i, "active_palette", -1)
                })
        have_body = any(s.startswith("body-flesh") or s == "body-flesh" for s in ids)
        have_eye = any(s.startswith("eye-") for s in ids)
        have_brow = any(s.startswith("eyebrow-") for s in ids)
        have_nose = any(s.startswith("nose-") for s in ids)
        have_mouth = any(s.startswith("mouth-") or s == "mouth" for s in ids)
        has_dress = any(s.startswith("dress-") for s in ids)
        has_fullsuit = any(s.startswith("fullsuit-") for s in ids)
        has_shirt = any(s.startswith("shirt-") for s in ids)
        has_bottom = any(s.startswith(("pants-", "skirt-", "shorts-")) for s in ids)
        if not have_body:
            out.append(self._mk_item("body-flesh", 27))
        if not have_eye:
            out.append(self._mk_item("eye-n_basic2018malesquaresleepy", 7))
        if not have_brow:
            out.append(self._mk_item("eyebrow-n_basic2018newbrows07", 0))
        if not have_nose:
            out.append(self._mk_item("nose-n_basic2018newnose05", 0))
        if not have_mouth:
            out.append(self._mk_item("mouth-basic2018chippermouth", -1))
        if not (has_dress or has_fullsuit or (has_shirt and has_bottom)):
            if not has_shirt:
                out.append(self._mk_item("shirt-n_starteritems2019tankwhite", -1))
            if not has_bottom:
                out.append(self._mk_item("shorts-f_pantyhoseshortsnavy", -1))
        return out
    
    async def _get_inventory_ids(self) -> set:
        try:
            inv = await self.highrise.get_inventory()
            items = []
            if hasattr(inv, "items"):
                items = inv.items
            elif hasattr(inv, "content"):
                items = inv.content
            else:
                items = inv or []
            ids = set()
            for it in (items or []):
                if isinstance(it, dict):
                    iid = it.get("id") or it.get("item_id")
                else:
                    iid = getattr(it, "id", None) or getattr(it, "item_id", None)
                if iid:
                    ids.add(iid)
            return ids
        except Exception:
            return set()
    
    async def _filter_outfit_by_inventory(self, normalized: list) -> list:
        try:
            owned = await self._get_inventory_ids()
            result = []
            for i in normalized:
                iid = i.get("id")
                # Always allow basic free items even if not in inventory
                if iid and (iid.startswith(("body-flesh", "eye-", "eyebrow-", "nose-", "mouth-")) or iid in owned):
                    result.append(i)
            # Re-normalize to ensure required categories
            return self._normalize_outfit(result)
        except Exception:
            return normalized
    
    async def _apply_outfit_and_verify(self, items: list) -> bool:
        try:
            # Converting to Item is required to support set_outfit reliably
            from highrise import Item
            converted = [Item(type=i["type"], amount=i["amount"], id=i["id"], account_bound=i["account_bound"], active_palette=i["active_palette"]) for i in items]
            await self.highrise.set_outfit(converted)
            # Verify by fetching current bot outfit
            try:
                my = await self.highrise.get_my_outfit()
                my_items = []
                if isinstance(my, list):
                    my_items = my
                elif hasattr(my, "outfit"):
                    my_items = my.outfit
                else:
                    my_items = []
                tgt_ids = {i["id"] for i in items if isinstance(i, dict)}
                cur_ids = {getattr(i, "id", None) or (i.get("id") if isinstance(i, dict) else None) for i in my_items}
                cur_ids = {i for i in cur_ids if i}
                # Consider success if it includes basic categories and matches a good portion of items
                have_body = any(s.startswith("body-flesh") or s == "body-flesh" for s in cur_ids)
                basic_ok = have_body
                same_or_subset = len(tgt_ids & cur_ids) >= max(1, len(tgt_ids) // 2)
                return basic_ok and same_or_subset
            except Exception:
                # Cannot verify without get_my_outfit
                return False
        except Exception:
            return False
    
    async def _fetch_outfit_for_username(self, username: str):
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url1 = f"https://webapi.highrise.game/users/user?username={username}"
                try:
                    async with session.get(url1, timeout=15) as resp1:
                        data1 = await resp1.json(content_type=None)
                    outfit = None
                    if isinstance(data1, dict):
                        if "outfit" in data1 and data1["outfit"]:
                            outfit = data1["outfit"]
                        elif "user" in data1 and isinstance(data1["user"], dict):
                            outfit = data1["user"].get("outfit")
                    if outfit:
                        return self._normalize_outfit(outfit)
                except Exception:
                    pass
                url2 = f"https://webapi.highrise.game/users?username={username}"
                try:
                    async with session.get(url2, timeout=15) as resp2:
                        data2 = await resp2.json(content_type=None)
                    if isinstance(data2, dict) and isinstance(data2.get("users"), list):
                        for u in data2["users"]:
                            if isinstance(u, dict):
                                un = (u.get("username") or u.get("name") or "").lower()
                                if un == username.lower():
                                    outfit = u.get("outfit") or (u.get("user") or {}).get("outfit")
                                    if outfit:
                                        return self._normalize_outfit(outfit)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"fetch outfit error: {e}")
        return None
    
    async def _fetch_user_info(self, username: str):
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # 1) users/{username} — High priority as requested
                try:
                    async with session.get(f"https://webapi.highrise.game/users/{username}", timeout=15) as resp3:
                        data3 = await resp3.json(content_type=None)
                    if isinstance(data3, dict):
                        return data3.get("user") or data3
                except Exception:
                    pass
                # 2) users/user?username=
                try:
                    async with session.get(f"https://webapi.highrise.game/users/{username}", timeout=15) as resp1:
                        data1 = await resp1.json(content_type=None)
                    if isinstance(data1, dict):
                        if "user" in data1 and isinstance(data1["user"], dict):
                            return data1["user"]
                        if "username" in data1:
                            return data1
                except Exception:
                    pass
                # 3) users?username=
                try:
                    async with session.get(f"https://webapi.highrise.game/{username}", timeout=15) as resp2:
                        data2 = await resp2.json(content_type=None)
                    if isinstance(data2, dict) and isinstance(data2.get("users"), list):
                        for u in data2["users"]:
                            if isinstance(u, dict):
                                un = (u.get("username") or u.get("name") or "").lower()
                                if un == username.lower():
                                    return u.get("user") or u
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"fetch user info error: {e}")
        return None
    
    async def _resolve_user_id(self, username: str) -> str | None:
        """Return user_id via Web API or Room"""
        try:
            # First: Search in room
            try:
                room_users_response = await self.highrise.get_room_users()
                for u, _ in room_users_response.content:
                    if u.username.lower() == username.lower():
                        return u.id
            except Exception:
                pass
            # Second: Via Web API users/{username}
            info = await self._fetch_user_info(username)
            if isinstance(info, dict):
                return info.get("id") or info.get("user_id")
        except Exception as e:
            logger.error(f"resolve user id error: {e}")
        return None
    
    async def info_user_command(self, user: User, args: str):
        try:
            if not await self.is_management_allowed(user):
                await self.send_whisper_safe(user, "❌ This command is for Moderators/Owner only")
                return
            target = args.strip().lstrip('@')
            if not target:
                await self.send_whisper_safe(user, "⚠️ Usage: -info @user")
                return
            info = await self._fetch_user_info(target)
            tickets = self.tickets_system.get_user_tickets(target)
            if info:
                uname = info.get("username", target)
                uid = info.get("id") or info.get("user_id") or "N/A"
                nf = info.get("num_followers") or info.get("followers") or 0
                nfr = info.get("num_friends") or info.get("friends") or 0
                nfg = info.get("num_following") or info.get("following") or 0
                joined = info.get("joined_at") or info.get("created_at")
                last_online = info.get("last_online_at") or info.get("last_online_in")
                def fmt_dt(s: str) -> str:
                    try:
                        from datetime import datetime, timezone
                        dt = None
                        try:
                            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                        except Exception:
                            dt = None
                        if not dt:
                            return s
                        local = dt.astimezone()
                        return f"{local:%H:%M} — {local:%m/%d}"
                    except Exception:
                        return s
                msg_lines = []
                msg_lines.append(f"📊 Info @{uname}")
                msg_lines.append(f"🆔 ID: {uid}")
                msg_lines.append(f"👥 Followers: {int(nf)}")
                msg_lines.append(f"🤝 Friends: {int(nfr)}")
                msg_lines.append(f"➡️ Following: {int(nfg)}")
                if joined:
                    msg_lines.append(f"📅 Joined: {fmt_dt(joined)}")
                if last_online:
                    msg_lines.append(f"⏱️ Last Online: {fmt_dt(last_online)}")
                msg_lines.append(f"🎫 Tickets: {tickets}")
                await self.send_whisper_safe(user, "\n".join(msg_lines))
            else:
                await self.send_whisper_safe(user, f"❌ Unable to fetch info for @{target}")
        except Exception as e:
            logger.error(f"Error in /info: {e}")
    

    
    async def accs_command(self, user: User):
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            users = self.tickets_system.get_all_users_with_tickets()
            if not users:
                await self.highrise.chat(self.colorize("📭 No ticket records", "info"))
                return
            top = sorted(users.items(), key=lambda kv: kv[1], reverse=True)[:10]
            await self.highrise.chat(self.colorize("🏆 Top 10 by tickets:", "info"))
            for i, (uname, tk) in enumerate(top, start=1):
                await self.highrise.chat(self.colorize(f"{i}. @{uname} — {tk} ticket", "default"))
        except Exception as e:
            logger.error(f"Error in /accs: {e}")
    
    async def give_tickets_command(self, user: User, args: str):
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            parts = args.split()
            if len(parts) < 2:
                await self.highrise.chat(self.colorize("⚠️ Usage: -give @user N", "warning"))
                return
            target = parts[0].lstrip('@')
            try:
                amount = int(parts[1])
            except:
                await self.highrise.chat(self.colorize("❌ Invalid number", "error"))
                return
            total = self.tickets_system.add_tickets(target, amount)
            await self.highrise.chat(self.colorize(f"✅ Given @{target} {amount} tickets (Total: {total})", "success"))
        except Exception as e:
            logger.error(f"Error in /give tickets: {e}")
    
    async def send_with_delay(self, message: str, color_type: str = "default"):
        """Send message with delay to avoid spam"""
        if not self.is_connected:
            return
        await asyncio.sleep(self.message_delay)
        if not self.is_connected:
            return
        await self.highrise.chat(self.colorize(message, color_type))
    
    async def vip_reminder_task(self):
        """Periodic VIP reminder every 3 minutes"""
        while self.is_connected:
            try:
                await asyncio.sleep(180)  # 3 minutes
                
                if not self.is_connected:
                    break
                
                msg, color = BotResponses.VIP_REMINDER
                vip_price = HighriseSettings.VIP_PRICE
                reminder_msg = msg.format(price=vip_price)
                await self.send_with_delay(reminder_msg, color)
                logger.info("💎 VIP reminder sent")
                
            except Exception as e:
                if "closing transport" in str(e).lower() or "connection" in str(e).lower():
                    logger.warning("⚠️ VIP reminder stopped - Connection closed")
                    self.is_connected = False
                    break
                logger.error(f"❌ Error in VIP reminder: {e}")
    
    async def audio_help_reminder_task(self):
        """Periodic audio help reminder every 15 minutes"""
        while self.is_connected:
            try:
                await asyncio.sleep(600)  # 15 minutes
                
                if not self.is_connected:
                    break
                
                audio_msg = """🎵 If you have audio issues:
✅ Mute the radio and unmute it again
Thank you for your cooperation!"""

                await self.send_with_delay(audio_msg, "info")
                logger.info("🔊 Audio help reminder sent")
                
            except Exception as e:
                if "closing transport" in str(e).lower() or "connection" in str(e).lower():
                    logger.warning("⚠️ Audio help reminder stopped - Connection closed")
                    self.is_connected = False
                    break
                logger.error(f"❌ Error in audio help reminder: {e}")
    
    async def heartbeat_loop(self):
        """Heartbeat system to keep bot connection active"""
        heartbeat_interval = 120  # Every 2 minutes
        consecutive_failures = 0
        max_failures = 5
        
        while self.is_connected:
            try:
                await asyncio.sleep(heartbeat_interval)
                
                if not self.is_connected:
                    break
                
                # Check connection by getting room users
                try:
                    room_users = await self.highrise.get_room_users()
                    if room_users and hasattr(room_users, 'content'):
                        user_count = len(room_users.content)
                        logger.info(f"💓 Heartbeat: Bot connected | {user_count} users in room")
                        consecutive_failures = 0  # Reset counter
                    else:
                        logger.warning("⚠️ Heartbeat: Unexpected response")
                        consecutive_failures += 1
                except Exception as hb_error:
                    consecutive_failures += 1
                    logger.warning(f"⚠️ Heartbeat failed ({consecutive_failures}/{max_failures}): {hb_error}")
                    
                    if consecutive_failures >= max_failures:
                        logger.error("❌ Heartbeat failure limit reached - Attempting reconnection...")
                        self.is_connected = False
                        # Create restart signal file
                        try:
                            Path("restart_signal.txt").write_text(f"heartbeat_failure_{datetime.now().isoformat()}")
                            logger.info("📝 Restart signal created")
                        except:
                            pass
                        break
                
            except asyncio.CancelledError:
                logger.info("⏹️ Heartbeat cancelled")
                break
            except Exception as e:
                if "closing transport" in str(e).lower() or "connection" in str(e).lower():
                    logger.warning("⚠️ Heartbeat stopped - Connection closed")
                    self.is_connected = False
                    break
                logger.error(f"❌ Error in Heartbeat: {e}")
                await asyncio.sleep(10)
    
    async def connection_monitor(self):
        """Monitor connection continuity and check bot status"""
        check_interval = 60  # Check every minute
        
        while self.is_connected:
            try:
                await asyncio.sleep(check_interval)
                
                if not self.is_connected:
                    break
                
                # Try getting room info to confirm connection
                try:
                    room_users = await self.highrise.get_room_users()
                    if room_users and hasattr(room_users, 'content'):
                        logger.info(f"🔗 Connection Monitor: OK ({len(room_users.content)} users)")
                    else:
                        logger.warning("🔗 Connection Monitor: Unexpected response")
                except Exception as conn_error:
                    error_str = str(conn_error).lower()
                    if "connection" in error_str or "transport" in error_str:
                        logger.error(f"❌ Connection Monitor: Connection lost - {conn_error}")
                        self.is_connected = False
                        break
                    logger.warning(f"⚠️ Connection Monitor: {conn_error}")
                
            except asyncio.CancelledError:
                logger.info("⏹️ Connection Monitor cancelled")
                break
            except Exception as e:
                if "closing transport" in str(e).lower() or "connection" in str(e).lower():
                    logger.warning("⚠️ Connection Monitor stopped - Connection closed")
                    self.is_connected = False
                    break
                logger.error(f"❌ Error in Connection Monitor: {e}")
                await asyncio.sleep(10)
    
    async def has_unlimited_access(self, user: User, show_message: bool = False) -> bool:
        """Check if user has unlimited access (VIP, Moderator, Designer, or Owner)"""
        # Check VIP
        if self.tickets_system.is_vip(user.username):
            return True
        
        # Check Developers
        if self.tickets_system.is_dev(user.username):
            logger.info(f"🔑 {user.username} = Developer")
            return True
        
        # Check Primary Owner
        if user.username == self.owner_username:
            logger.info(f"🔑 {user.username} = Owner")
            return True
        
        # Check Additional Owners
        if user.username in self.additional_owners:
            logger.info(f"🔑 {user.username} = Additional Owner")
            return True
        
        # Check Moderators in Manual List
        if user.username in HighriseSettings.MODERATORS:
            logger.info(f"🔑 {user.username} = Moderator (Manual)")
            return True
        
        # Check Cached Staff
        if user.username in self.detected_staff:
            privilege_name = self.detected_staff[user.username]
            logger.info(f"🔑 {user.username} = {privilege_name} (Cached)")
            return True
        
        # Auto-check Room Privileges (Moderator or Designer)
        try:
            privilege = await self.highrise.get_room_privilege(user.id)
            
            # Check privilege type - can be object or string
            is_moderator = False
            is_designer = False
            privilege_name = None
            
            # If privilege is RoomPermissions object
            if hasattr(privilege, 'moderator') and hasattr(privilege, 'designer'):
                is_moderator = getattr(privilege, 'moderator', False)
                is_designer = getattr(privilege, 'designer', False)
                
                if is_designer and is_moderator:
                    privilege_name = "Designer & Moderator"
                elif is_designer:
                    privilege_name = "Designer"
                elif is_moderator:
                    privilege_name = "Moderator"
            # If privilege is string (legacy system)
            elif isinstance(privilege, str):
                if privilege in ["owner", "designer", "moderator"]:
                    privilege_name = {
                        "owner": "Owner",
                        "designer": "Designer", 
                        "moderator": "Moderator"
                    }.get(privilege, privilege)
                    is_moderator = privilege == "moderator"
                    is_designer = privilege == "designer"
            
            # If has privileges
            if privilege_name and (is_moderator or is_designer):
                # Save to cache
                if user.username not in self.detected_staff:
                    self.detected_staff[user.username] = privilege_name
                    self._save_staff_cache()
                    logger.info(f"💾 Saved {user.username} as {privilege_name}")
                
                logger.info(f"🔑 {user.username} = {privilege_name} (Auto-detected)")
                return True
        except Exception as e:
            logger.error(f"❌ Error checking privileges: {e}")
        
        return False
    
    async def periodic_staff_check(self):
        """Periodic check for moderators and designers every 3 minutes"""
        while self.is_connected:
            try:
                await asyncio.sleep(180)  # 3 minutes
                
                if not self.is_connected:
                    break
                
                logger.info("🔍 Starting periodic staff check...")
                
                room_users = await self.highrise.get_room_users()
                
                new_staff_count = 0
                for user, position in room_users.content:
                    if not self.is_connected:
                        break
                    
                    if self.bot_username and user.username == self.bot_username:
                        continue
                    
                    try:
                        privilege = await self.highrise.get_room_privilege(user.id)
                        
                        is_moderator = False
                        is_designer = False
                        privilege_name = None
                        
                        if hasattr(privilege, 'moderator') and hasattr(privilege, 'designer'):
                            is_moderator = getattr(privilege, 'moderator', False)
                            is_designer = getattr(privilege, 'designer', False)
                            
                            if is_designer and is_moderator:
                                privilege_name = "Designer & Moderator"
                            elif is_designer:
                                privilege_name = "Designer"
                            elif is_moderator:
                                privilege_name = "Moderator"
                        elif isinstance(privilege, str):
                            if privilege in ["owner", "designer", "moderator"]:
                                privilege_name = {
                                    "owner": "Owner",
                                    "designer": "Designer", 
                                    "moderator": "Moderator"
                                }.get(privilege, privilege)
                                is_moderator = privilege == "moderator"
                                is_designer = privilege == "designer"
                        
                        if privilege_name and (is_moderator or is_designer):
                            if user.username not in self.detected_staff:
                                self.detected_staff[user.username] = privilege_name
                                self._save_staff_cache()
                                new_staff_count += 1
                                logger.info(f"💾 New discovery: {user.username} = {privilege_name}")
                    except Exception as e:
                        logger.debug(f"Skipping {user.username}: {e}")
                        continue
                
                if new_staff_count > 0:
                    logger.info(f"✅ Discovered {new_staff_count} new staff members")
                else:
                    logger.info("✅ No new staff found")
                    
            except Exception as e:
                if "closing transport" in str(e).lower() or "connection" in str(e).lower():
                    logger.warning("⚠️ Periodic staff check stopped - Connection closed")
                    self.is_connected = False
                    break
                logger.error(f"❌ Error in periodic staff check: {e}")
    
    async def before_start(self, tg=None):
        """Before bot start - run background tasks"""
        try:
            if tg is not None and hasattr(tg, 'create_task'):
                tg.create_task(self.vip_reminder_task())
                tg.create_task(self.periodic_staff_check())
                logger.info("✅ Background tasks started (TaskGroup)")
            else:
                asyncio.create_task(self.vip_reminder_task())
                asyncio.create_task(self.periodic_staff_check())
                logger.info("✅ Background tasks started (asyncio)")
        except Exception as e:
            logger.error(f"❌ Error in before_start: {e}")
    
    async def on_start(self, session_metadata: SessionMetadata):
        """On bot start"""
        self.is_connected = True
        self.bot_username = session_metadata.user_id.split('|')[0] if '|' in session_metadata.user_id else None
        logger.info(f"🎵 Music Bot connected to Highrise! Bot Name: {self.bot_username}")
        
        
        
        # Show saved staff
        if self.detected_staff:
            staff_list = ', '.join([f"{name} ({role})" for name, role in self.detected_staff.items()])
            logger.info(f"📋 Saved Staff: {staff_list}")
        
        # Initial staff check
        logger.info("🔍 Starting initial staff check...")
        try:
            room_users = await self.highrise.get_room_users()
            total_users = len(room_users.content)
            logger.info(f"👥 Users in room: {total_users}")
            
            for user, position in room_users.content:
                logger.info(f"🔍 Checking user: {user.username} (ID: {user.id})")
                
                if self.bot_username and user.username == self.bot_username:
                    logger.info(f"⏭️ Skipping bot: {user.username}")
                    continue
                
                # Check privileges with detailed logging
                try:
                    privilege = await self.highrise.get_room_privilege(user.id)
                    logger.info(f"🔑 {user.username} privileges: {privilege}")
                    
                    # Check privilege type
                    has_privilege = False
                    
                    # If privilege is RoomPermissions object
                    if hasattr(privilege, 'moderator') and hasattr(privilege, 'designer'):
                        is_moderator = getattr(privilege, 'moderator', False)
                        is_designer = getattr(privilege, 'designer', False)
                        has_privilege = is_moderator or is_designer
                    # If privilege is string (legacy system)
                    elif isinstance(privilege, str):
                        has_privilege = privilege in ["owner", "designer", "moderator"]
                    
                    if has_privilege:
                        await self.has_unlimited_access(user, show_message=False)
                    else:
                        logger.info(f"ℹ️ {user.username} has no privileges (privilege: {privilege})")
                except Exception as priv_error:
                    logger.error(f"❌ Error checking privileges for {user.username}: {priv_error}")
                    
        except Exception as e:
            logger.error(f"❌ Error in initial check: {e}")
        
        # Start periodic check every 3 minutes
        asyncio.create_task(self.periodic_staff_check())
        
        # Start VIP reminder every 3 minutes
        asyncio.create_task(self.vip_reminder_task())
        
        # Start monitoring current song
        asyncio.create_task(self.monitor_current_song())
        
        # Start periodic announcement every 5 minutes
        asyncio.create_task(self.announce_song_status())
        
        # Start heartbeat system to prevent room exit
        asyncio.create_task(self.heartbeat_loop())
        
        # Start connection monitoring
        asyncio.create_task(self.connection_monitor())
        
        # Start continuous dancing
        await self.start_continuous_dancing()
    
    async def on_user_join(self, user: User, position: Position | AnchorPosition):
        """On user join"""
        try:
            # Check ticket regeneration
            self.tickets_system.check_regeneration(user.username)

            # Auto-detect moderators and designers
            await self.has_unlimited_access(user, show_message=False)
            
            # Format time
            now = datetime.now().strftime("(%d-%m-%Y)(%H:%M:%S)")
            
            # Determine Role and Message
            if user.username == HighriseSettings.OWNER_USERNAME or (user.username in self.tickets_system.dev_users):
                role = "Owner"
                msg = f"\n<#FFFFFF>Hy <#39FF14>@{user.username} 👑<#FFFFFF> WELCOME TO ⚡ THE LEGENDS ⚡ : Last seen {now}"
            elif user.username in self.tickets_system.vip_users:
                role = "VIP"
                msg = f"\n<#FFFFFF>Hy <#FFFF00>@{user.username} ⭐<#FFFFFF> WELCOME TO ✨ THE LEGENDS ✨ : Last seen {now}"
            elif await self.is_management_allowed(user): # Moderator check
                role = "Moderator"
                msg = f"\n<#FFFFFF>Hy <#FF0000>@{user.username} 🛡️<#FFFFFF> WELCOME TO ⚔️ THE LEGENDS ⚔️ : Last seen {now}"
            else:
                role = "Normal Player"
                msg = f"\nHy @{user.username} 👤 WELCOME TO 🌀 THE LEGENDS 🌀 : Last seen {now}"

            # Send welcome message to public chat
            await self.highrise.chat(msg)
            
            # Auto-tip logic (if enabled)
            autotip_amount = self.tickets_system.get_autotip_amount()
            if autotip_amount > 0:
                try:
                    # Check bot balance first to avoid errors
                    wallet = await self.highrise.get_wallet()
                    balance = wallet.content[0].amount if wallet.content else 0
                    if balance >= autotip_amount:
                        # Convert amount to bars
                        bars_dictionary = {
                             10000: "gold_bar_10k", 5000: "gold_bar_5000", 1000: "gold_bar_1k",
                             500: "gold_bar_500", 100: "gold_bar_100", 50: "gold_bar_50",
                             10: "gold_bar_10", 5: "gold_bar_5", 1: "gold_bar_1"
                        }
                        tip_str = ""
                        remaining = autotip_amount
                        for bar_val in sorted(bars_dictionary.keys(), reverse=True):
                            if remaining >= bar_val:
                                count = remaining // bar_val
                                remaining %= bar_val
                                tip_str += ("," + bars_dictionary[bar_val]) * count
                        tip_str = tip_str.lstrip(",")
                        
                        if tip_str:
                            await self.highrise.tip_user(user.id, tip_str)
                except Exception as e:
                    logger.error(f"Auto-tip error: {e}")

        except Exception as e:
            logger.error(f"❌ Error in welcome message: {e}")
    
    async def on_tip(self, sender: User, receiver: User, tip):
        """On tip received"""
        try:
            # Extract amount from CurrencyItem
            tip_amount: int = 0
            if hasattr(tip, 'amount'):
                tip_amount = int(tip.amount) if isinstance(tip.amount, (int, float, str)) else 0
            elif isinstance(tip, (int, float)):
                tip_amount = int(tip)
            else:
                logger.error(f"❌ Invalid tip amount: {tip}")
                return
            
            if tip_amount <= 0:
                logger.error(f"❌ Invalid tip amount: {tip_amount}")
                return
            
            logger.info(f"💰 Tip: From {sender.username} to {receiver.username} = {tip_amount}g")
            
            # Check if tip is for the bot
            # If bot name is not saved, accept any tip
            if self.bot_username and receiver.username != self.bot_username:
                logger.info(f"⚠️ Tip not for bot (Receiver: {receiver.username})")
                return
            
            # Check VIP (600g = VIP)
            if tip_amount >= HighriseSettings.VIP_PRICE:
                # Check if user is already VIP
                if self.tickets_system.is_vip(sender.username):
                    msg, color = BotResponses.VIP_ALREADY
                    await self.highrise.chat(self.colorize(msg.format(username=sender.username), color))
                else:
                    # Add VIP
                    self.tickets_system.add_vip(sender.username)
                    msg, color = BotResponses.VIP_RECEIVED
                    await self.highrise.chat(self.colorize(msg.format(username=sender.username), color))
                    logger.info(f"⭐ {sender.username} became VIP")
                return
            
            # New ticket price system
            price_per_ticket = self.tickets_system.get_ticket_price()
            tickets_to_add = tip_amount // price_per_ticket
            
            if tickets_to_add > 0:
                total_tickets = self.tickets_system.add_tickets(sender.username, tickets_to_add)
                msg, color = BotResponses.TIP_RECEIVED
                await self.highrise.chat(self.colorize(
                    msg.format(
                        username=sender.username,
                        gold=tip_amount,
                        tickets=tickets_to_add,
                        total=total_tickets
                    ),
                    color
                ))
                logger.info(f"✅ {sender.username} got {tickets_to_add} tickets (Total: {total_tickets})")
            else:
                msg_text = BotResponses.TICKET_PRICE_LIST
                await self.highrise.chat(msg_text)
            
        except Exception as e:
            logger.error(f"❌ Error processing tip: {e}")
    
    async def on_chat(self, user: User, message: str):
        """On chat message received"""
        message = message.strip()
        
        # Commands to save bot position and return to it (Owner only)
        if message.lower() == "add":
            if user.username.lower() != self.owner_username.lower():
                return
            
            try:
                room_users_response = await self.highrise.get_room_users()
                for u, pos in room_users_response.content:
                    if u.id == user.id:
                        self.saved_position = {"x": pos.x, "y": pos.y, "z": pos.z, "facing": pos.facing}
                        save_bot_position(self.saved_position)
                        await self.highrise.chat("✅ Bot position saved.")
                        return
                
                await self.highrise.chat("❌ Couldn't find your position.")
            except Exception as e:
                logger.error(f"Error saving position: {e}")
                await self.highrise.chat("❌ Failed to save position.")
            return
        
        if message.lower() == "go":
            if user.username.lower() != self.owner_username.lower():
                return
            
            if not self.saved_position:
                self.saved_position = load_bot_position()
            
            if not self.saved_position:
                await self.highrise.chat("❌ No saved position.")
                return
            
            try:
                pos = Position(
                    x=self.saved_position["x"],
                    y=self.saved_position["y"],
                    z=self.saved_position["z"],
                    facing=self.saved_position.get("facing", "FrontRight")
                )
                await self.highrise.walk_to(pos)
                await self.highrise.chat("🚶 Bot walked to saved position.")
            except Exception as e:
                logger.error(f"Error walking to position: {e}")
                await self.highrise.chat("❌ Failed to walk to saved position.")
            return
        
        # Support commands starting with - only
        if message.startswith("-") or message in ["confirm reset", "withdraw", "1", "2"] or message.lower() == "hello":
            await self.handle_command(user, message)
    
    async def on_message(self, user_id: str, conversation_id: str, is_new_conversation: bool) -> None:
        """On private message received - Show command list"""
        try:
            response = await self.highrise.get_messages(conversation_id)
            last_text = None
            sender_username = None
            # Extract last message, type and sender name if available
            if response and getattr(response, "messages", None):
                msgs = list(getattr(response, "messages", []))
                if msgs:
                    m = msgs[-1]
                    last_text = getattr(m, "content", None) or getattr(m, "text", None)
                    author = getattr(m, "author", None) or getattr(m, "sender", None)
                    if author:
                        if getattr(author, "id", None) == user_id:
                            sender_username = getattr(author, "username", None)
                    # Extra attempts if author not available
                    if not sender_username:
                        if getattr(m, "username", None):
                            sender_username = getattr(m, "username", None)
                # If username not found, try searching in room
                if not sender_username:
                    try:
                        room_users_response = await self.highrise.get_room_users()
                        for u, _ in room_users_response.content:
                            if u.id == user_id:
                                sender_username = u.username
                                break
                    except Exception:
                        pass
                # Final attempt: Get conversation owner name from conversation list
                if not sender_username:
                    try:
                        convs = await self.highrise.get_conversations(False, None)
                        for c in getattr(convs, "conversations", []) or []:
                            cid = getattr(c, "id", None) or getattr(c, "conversation_id", None)
                            if cid == conversation_id:
                                u = getattr(c, "user", None)
                                if u and getattr(u, "id", None) == user_id:
                                    sender_username = getattr(u, "username", None)
                                    break
                    except Exception:
                        pass
            # Handle /verify or hello in PM
            if isinstance(last_text, str):
                clean_text = last_text.strip().lower()
                if clean_text in ["hello", "!hello", "-hello"] or clean_text.startswith(("-verify", "!verify")):
                    if sender_username:
                        try:
                            # Register subscription with conversation_id
                            await self._sub(user_id, sender_username, conversation_id)

                            # Required messages in order
                            await self.highrise.send_message(conversation_id, "✅ Account verified!")
                            
                            if not self.tickets_system.has_used_verify(sender_username):
                                self.tickets_system.add_tickets(sender_username, 3)
                                self.tickets_system.mark_verify_used(sender_username)
                                await self.highrise.send_message(conversation_id, "🎫 You got 3 free tickets!")
                            else:
                                # If verified before, don't give tickets but send other messages
                                pass

                            # Useful commands message
                            help_msg = (
                                "📜 Useful Commands: \n"
                                " 🎶 -play + Song name or Link \n"
                                " 🎫 -wallet — Check your tickets \n"
                                " 💰 -rlist — Buy tickets and VIP \n"
                                " 📲 -help — View all available commands"
                            )
                            await self.highrise.send_message(conversation_id, help_msg)

                            # Send invite card
                            try:
                                await self.highrise.send_message(conversation_id, "", "invite", HighriseSettings.ROOM_ID)
                            except Exception as e:
                                logger.error(f"Failed to send invite card in verify: {e}")
                                invite_link = f"https://webapi.highrise.game/rooms/{HighriseSettings.ROOM_ID}"
                                await self.highrise.send_message(conversation_id, invite_link)
                                
                            logger.info(f"✅ PM Verify: {sender_username}")
                        except Exception as e:
                            logger.error(f"❌ Error in PM verify: {e}")
                            await self.highrise.send_message(conversation_id, "❌ Error during verification.")
                    else:
                        await self.highrise.send_message(conversation_id, "❌ Could not identify your username. Try again from inside the room.")
                    return
            if isinstance(last_text, str):
                txt = last_text.strip().lower()
                if txt in ["-help", "!help", "help"]:
                    await self.highrise.send_message(conversation_id, BotResponses.HELP_USER_PAGE1)
                    await self.highrise.send_message(conversation_id, BotResponses.HELP_USER_PAGE2)
        except Exception as e:
            logger.error(f"❌ Error processing private message: {e}")
    
    async def handle_command(self, user: User, message: str):
        """Handle commands with universal prefix support (-, /, !)"""
        # Strip prefix and split
        if not message:
            return
            
        # Normalize prefix: remove -, /, ! from start
        clean_message = message
        if message[0] in ["-", "/", "!"]:
            clean_message = message[1:]
        
        parts = clean_message.split(maxsplit=1)
        command_raw = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Prevent blocked users
        if hasattr(self.tickets_system, "is_blocked") and self.tickets_system.is_blocked(user.username):
            return

        # Alias Map
        alias_map = {
            "p": "play",
            "s": "skip",
            "q": "queue",
            "addv": "addvip",
            "remv": "rvip",
            "bwallet": "balance",
            "setbot": "setbot",
            "pslot": "pslot",
            "mod": "addmod",
            "demod": "rmod",
            "rdev": "rmod",
            "addowner": "addowner",
            "rowner": "removeowner",
            "addvip": "addvip",
            "buyvip": "buyvip",
            "remvip": "rvip",
            "copy": "equip",
            "dance": "dance",
            "block": "block",
            "unblock": "unblock",
            "wallet": "botwallet", # User requested -Wallet for Bot Balance
            "bal": "tickets",      # User requested -bal for User Balance (Tickets)
            "give": "give",
            "autotip": "autotip",
            "tipall": "tipall",
            "randomtip": "randomtip",
            "clear": "clearqueue",
            "gift": "gift",
            "fplay": "fplay",
            "remove": "rmqueue",
            "check": "check_user",
            "lb": "leaderboard",
            "summon": "summon",
            "help": "help",
            "play": "play",
            "np": "now",
            "like": "like",
            "unlike": "unlike",
            "addfav": "fav",
            "skip": "skip",
            "commands": "help",
            "listowners": "listowners",
            "ownerlist": "listowners",
            "add": "addowner",
            "rem": "removeowner",
            "2": "help_2",
            "tickets": "tickets",
            "set": "set",
            "ticketslist": "ticketslist",
            "withdraw": "withdraw",
            "withdrawall": "withdrawall",
            "alltk": "alltk",
            "free": "free",
            "unfree": "unfree",
            "balance": "balance",
            "sync": "sync",
            "cash": "cash",
            "invite": "invite",
            "info": "info",
            "sblocked": "sblocked",
            "accs": "accs",
            "clear": "clearqueue",
            "cleancache": "cleancache",
            "cacheinfo": "cacheinfo",
            "maxqueue": "maxqueue",
            "maxrequests": "maxrequests",
            "dev": "dev",
            "devon": "devon",
            "devoff": "devoff",
            "reset": "reset",
            "equip": "equip",
            "equipid": "equipid",
            "cbit": "cbit",
            "stoprn": "stoprn",
            "startrn": "startrn",
            "stopdance": "stopdance",
            "startdance": "startdance",
            "numinvite": "numinvite",
            "dplay": "dplay",
            "hello": "verify",
            "radio": "stream",
            "stream": "stream",
            "cfav": "cfav",
            "modlist": "modlist",
            "viplist": "viplist",
            "his": "history",
            "history": "history",
            "1": "help_1",
            "2": "help_2"
        }

        command = alias_map.get(command_raw, command_raw)
        
        # Command Routing
        if command == "play":
            if args:
                await self.search_and_show_results(user, args)
            else:
                msg, color = BotResponses.PLAY_NO_SONG_NAME
                await self.highrise.chat(self.colorize(msg, color))

        elif command == "dance":
            await self.start_continuous_dancing()

        elif command == "stopdance":
            await self.stop_continuous_dancing()

        elif command == "buyvip":
            await self.buy_vip_command(user, args)

        elif command == "addvip":
            await self.add_vip_command(user, args)

        elif command == "rvip":
            await self.remove_vip_command(user, args)

        elif command == "addmod":
            await self.mod_command(user, args)

        elif command == "rmod":
            await self.demod_command(user, args)

        elif command == "addowner":
            await self.add_owner_command(user, args)

        elif command == "removeowner":
            await self.remove_owner_command(user, args)
            
        elif command == "listowners":
            await self.list_owners_command()

        elif command == "modlist":
            await self.show_mod_list_command(user)

        elif command == "viplist":
            await self.show_vip_list_command(user)

        elif command in ["now", "np"]:
            await self.send_current_song()

        elif command.startswith("next") and len(command_raw) > 4 and command_raw[4:].isdigit():
             await self.play_from_queue_by_index(user, int(command_raw[4:]))

        elif command == "next":
            await self.next_command(user)

        elif command == "tickets":
            await self.show_user_tickets(user)
            
        elif command == "ticketslist":
            await self.show_all_tickets()

        elif command == "rlist":
            await self.show_prices_command()

        elif command == "dump":
            await self.dump_command(args)

        elif command == "verify":
            try:
                await self.highrise.chat(self.colorize("📞 Use hello in PM to get 3 tickets", "info"))
            except Exception:
                pass

        elif command == "stream":
            try:
                await self.highrise.chat(self.colorize(f"🎧 Listen to live stream here: {self.stream_url}", "info"))
            except Exception:
                pass

        elif command == "fav":
            await self.fav_command(user, args)

        elif command == "cfav":
            await self.clear_fav_command(user, args)

        elif command == "fplay":
            await self.mod_fplay_command(user, args)

        elif command == "numinvite":
            msg = await self._numinvite()
            await self.highrise.chat(msg)

        elif command == "dplay":
            await self.play_from_default_playlist(user, args)

        elif command == "rmqueue":
            await self.mod_remove_command(user, args)

        elif command in ["queue", "playlist"]:
            await self.send_queue_status(user)

        elif command == "skip":
            await self.mod_skip_command(user) # User logic handled inside if needed

        elif command == "stoprn":
            # ... existing logic for stoprn ...
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            try:
                state = {}
                if Path(SystemFiles.PLAYLIST_STATE).exists():
                    with open(SystemFiles.PLAYLIST_STATE, 'r', encoding='utf-8') as f:
                        try:
                            state = json.load(f) or {}
                        except Exception:
                            state = {}
                state['disable_default_playlist'] = True
                with open(SystemFiles.PLAYLIST_STATE, 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
                try:
                    Path("skip_default_only.txt").touch()
                except Exception:
                    pass
                await self.highrise.chat(self.colorize("✅ Default playlist stopped", "success"))
            except Exception:
                msg, color = BotResponses.COMMAND_ERROR
                await self.highrise.chat(self.colorize(msg, color))

        elif command == "startrn":
            # ... existing logic for startrn ...
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            try:
                state = {}
                if Path(SystemFiles.PLAYLIST_STATE).exists():
                    with open(SystemFiles.PLAYLIST_STATE, 'r', encoding='utf-8') as f:
                        try:
                            state = json.load(f) or {}
                        except Exception:
                            state = {}
                state['disable_default_playlist'] = False
                with open(SystemFiles.PLAYLIST_STATE, 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
                try:
                    Path("skip_default_only.txt").unlink(missing_ok=True)
                except Exception:
                    pass
                await self.highrise.chat(self.colorize("✅ Default playlist restarted", "success"))
            except Exception:
                msg, color = BotResponses.COMMAND_ERROR
                await self.highrise.chat(self.colorize(msg, color))

        elif command == "addtickets":
            await self.add_tickets_command(user, args)

        elif command == "withdraw":
            await self.withdraw_tickets_command(user, args)

        elif command == "withdrawall":
            await self.withdraw_all_tickets_command(user)

        elif command == "alltk":
            await self.give_all_tickets_command(user, args)

        elif command == "free":
            await self.free_vip_command(user, args)

        elif command == "unfree":
            await self.unfree_vip_command(user, args)

        elif command == "balance":
            await self.check_balance_command(user) # Existing wallet check (Owner)
            
        elif command == "botwallet":
            await self.bot_wallet_command(user) # New -Wallet command (DM)

        elif command == "sync":
            await self.sync_wallet_command(user)

        elif command == "give":
            await self.give_command_dispatcher(user, args)

        elif command == "cash":
            await self.cash_command(user, args)

        elif command == "invite":
            await self.invite_verified_command(user)

        elif command == "info":
            await self.info_user_command(user, args)

        elif command == "block":
            await self.block_user_command(user, args)

        elif command == "unblock":
            await self.unblock_user_command(user, args)

        elif command == "sblocked":
            await self.show_blocked_command(user)

        elif command == "accs":
            await self.accs_command(user)

        elif command == "clearqueue":
            await self.clear_queue_command(user)

        elif command == "cleancache":
            await self.clean_cache_command(user)

        elif command == "cacheinfo":
            await self.cache_info_command(user)

        elif command == "maxqueue":
            await self.max_queue_command(user, args)

        elif command == "maxrequests":
            await self.max_requests_command(user, args)

        elif command == "dev":
            await self.dev_info_command(user)

        elif command == "devon":
            await self.dev_on_command(user)

        elif command == "devoff":
            await self.dev_off_command(user)

        elif command == "reset" or message == "confirm reset":
            await self.reset_command(user, message)

        elif command == "equip":
            await self.equip_outfit_command(user, args)

        elif command == "equipid":
            await self.equip_outfit_by_id_command(user, args)

        elif command == "cbit":
            await self.cbit_command(user)

        elif command == "set":
            await self.set_command(user, args)

        elif command == "setbot":
            await self.setbot_command(user, args)

        elif command == "pslot":
            await self.pslot_command(user, args)
            
        elif command == "autotip":
            await self.autotip_command(user, args)
            
        elif command == "tipall":
            await self.tip_all_command(user, args)
            
        elif command == "randomtip":
            await self.random_tip_command(user, args)
            
        elif command == "gift":
            await self.gift_song_command(user, args)
            
        elif command == "check_user":
            await self.mod_check_balance_command(user, args)
            
        elif command == "leaderboard":
            await self.leaderboard_command(user)
            
        elif command == "summon":
            await self.summon_command(user, args)
            
        elif command == "like":
            await self.like_song_command(user)
            
        elif command == "unlike":
            await self.unlike_song_command(user)

        elif command in ["help", "commands"]:
            await self.show_commands_list(user)

        elif command == "help_1":
            await self.send_whisper_safe(user, BotResponses.HELP_USER_PAGE1)
            await self.send_whisper_safe(user, BotResponses.HELP_USER_PAGE2)

        elif command == "help_2":
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.send_whisper_safe(user, self.colorize(msg, color))
                return
            # Show User Commands first
            await self.send_whisper_safe(user, BotResponses.HELP_USER_PAGE1)
            await self.send_whisper_safe(user, BotResponses.HELP_USER_PAGE2)
            # Show Manager Commands
            await self.send_whisper_long(user, BotResponses.HELP_MANAGER_USERS)
            await self.send_whisper_long(user, BotResponses.HELP_MANAGER_MONEY1)
            await self.send_whisper_long(user, BotResponses.HELP_MANAGER_MONEY2)
            await self.send_whisper_long(user, BotResponses.HELP_MANAGER_SETTINGS)
            if hasattr(BotResponses, "INFO_SECTION"):
                await self.send_whisper_long(user, BotResponses.INFO_SECTION)


    async def _sub(self, user_id: str, username: str | None, conversation_id: str = None):
        try:
            self.tickets_system.add_sub(user_id, username or "", conversation_id)
            return "Subscribed"
        except Exception:
            return "Failed to subscribe"

    async def _numinvite(self):
        try:
            subs = self.tickets_system.get_subs()
            n = len(subs or [])
            return f"Subscribers: {n}"
        except Exception:
            return "Failed to count subscribers"

    async def _invite(self):
        try:
            room_id = HighriseSettings.ROOM_ID
            subs = self.tickets_system.get_subs()
            if not subs:
                return "No subscribers"

            # Try to update conversation map from API (fallback)
            conv_map = {}
            try:
                convs = await self.highrise.get_conversations(False, None)
                if convs:
                    for c in getattr(convs, "conversations", []) or []:
                        u = getattr(c, "user", None)
                        uid = getattr(u, "id", None) if u else getattr(c, "user_id", None)
                        cid = getattr(c, "id", None) or getattr(c, "conversation_id", None)
                        if uid and cid:
                            conv_map[uid] = cid
            except Exception:
                pass
            
            sent = 0
            for s in subs:
                uid = s.get("id")
                # Priority to saved conversation_id, then from current map
                cid = s.get("conversation_id") or conv_map.get(uid)
                
                if not cid:
                    continue
                
                try:
                    # Send room invite (Invite Card)
                    await self.highrise.send_message(cid, "", "invite", room_id)
                    sent += 1
                except Exception:
                    # Fallback: Send room web link
                    try:
                        invite_link = f"https://webapi.highrise.game/rooms/{room_id}"
                        await self.highrise.send_message(cid, invite_link)
                        sent += 1
                    except Exception:
                        pass
            
            return f"Sent invite to {sent} subscribers"
        except Exception:
            return "Failed to invite"

    async def _inviteall(self, user_id: str, username: str):
        # Using existing permission checks
        is_owner = await self.is_main_owner(User(user_id, username))
        is_mod = await self.is_management_allowed(User(user_id, username)) # Approximate check
        
        if not (is_owner or is_mod):
            return "Unauthorized"
        return await self._invite()

    async def invite_verified_command(self, user: User):
        """Invite all subscribers (subs)"""
        try:
            result = await self._inviteall(user.id, user.username)
            if result == "Unauthorized":
                 await self.send_whisper_safe(user, "❌ This command is for Staff/Owner only")
            else:
                 await self.send_whisper_safe(user, f"✅ {result}")
        except Exception as e:
            logger.error(f"Error sending invites: {e}")
            await self.send_whisper_safe(user, "❌ Failed to send invites")
    
    async def show_next_song(self):
        """Show next song in queue"""
        try:
            next_song = None
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                    if lines:
                        parts = lines[0].split('|||')
                        if len(parts) == 3:
                            username, _, title = parts
                            next_song = f"{title} - @{username}"
                        elif len(parts) == 2:
                            username, song_query = parts
                            next_song = f"{song_query} - @{username}"
                        else:
                            next_song = lines[0]
            if next_song:
                await self.highrise.chat(self.colorize(f"⏭️ Next song: {next_song}", "info"))
            else:
                await self.highrise.chat(self.colorize("📋 No songs in queue", "warning"))
        except Exception as e:
            logger.error(f"❌ Error showing next song: {e}")
    
    async def next_command(self, user: User):
        """Skip current song and play next, deducting ticket for non-VIP users"""
        try:
            # Check if user owns the current song
            is_own_song = False
            try:
                if Path(self.notifications_file).exists():
                    with open(self.notifications_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if data.get('requested_by') == user.username:
                        is_own_song = True
            except:
                pass

            if is_own_song:
                 await self.highrise.chat(self.colorize(f"⏭️ @{user.username} skipped their own song.", "success"))
                 Path("skip_signal.txt").touch()
                 return

            is_unlimited = await self.has_unlimited_access(user, show_message=True)
            if not is_unlimited:
                remaining = self.tickets_system.get_user_tickets(user.username)
                if remaining <= 0:
                    msg, color = BotResponses.NO_TICKETS
                    await self.highrise.chat(self.colorize(msg.format(username=user.username), color))
                    return
                self.tickets_system.use_ticket(user.username)
                msg, color = BotResponses.TICKET_USED
                await self.highrise.chat(self.colorize(msg.format(remaining=self.tickets_system.get_user_tickets(user.username)), color))
            else:
                msg, color = BotResponses.VIP_SKIP_UNLIMITED
                await self.highrise.chat(self.colorize(msg, color))
            
            Path("skip_signal.txt").touch()
            msg, color = BotResponses.SKIPPING_SONG
            await self.highrise.chat(self.colorize(msg, color))
        except Exception as e:
            logger.error(f"❌ Error executing next: {e}")
            msg, color = BotResponses.SKIP_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def show_prices_command(self):
        """Show ticket and VIP prices"""
        try:
            await self.highrise.chat(BotResponses.TICKET_PRICE_LIST)
        except Exception as e:
            logger.error(f"❌ Error showing prices: {e}")
    
    async def verify_command(self, user: User):
        """Grant 3 tickets to user via /verify"""
        try:
            if self.tickets_system.has_used_verify(user.username):
                msg, color = BotResponses.VERIFY_ALREADY_USED
                await self.highrise.chat(self.colorize(msg, color))
                return
            total = self.tickets_system.add_tickets(user.username, 3)
            self.tickets_system.mark_verify_used(user.username)
            try:
                await self.send_whisper_safe(user, "✅ Account verified!")
                await self.send_whisper_safe(user, "🎫 You got 3 free tickets!")
            except Exception:
                pass
            conv_id = None
            try:
                convs = await self.highrise.get_conversations(False, None)
                for c in getattr(convs, "conversations", []) or []:
                    u = getattr(c, "user", None)
                    uid = getattr(u, "id", None) if u else getattr(c, "user_id", None)
                    if uid == user.id:
                        conv_id = getattr(c, "id", None) or getattr(c, "conversation_id", None)
                        break
            except Exception:
                conv_id = None
            try:
                self.tickets_system.add_sub(user.id, user.username, conv_id)
            except Exception:
                pass
            if conv_id:
                try:
                    await self.highrise.send_message(conv_id, "", "invite", HighriseSettings.ROOM_ID)
                except Exception:
                    pass
            msg, color = BotResponses.VERIFY_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(total=total), color))
        except Exception as e:
            logger.error(f"❌ Error in verification: {e}")
    
    async def dump_command(self, args: str):
        """Show detailed info: dump N or current"""
        try:
            if args.strip().isdigit():
                index = int(args.strip())
                if not Path(self.queue_file).exists():
                    await self.highrise.chat(self.colorize("📋 Queue is empty", "info"))
                    return
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    queue_lines = [line.strip() for line in f.readlines() if line.strip()]
                if index <= 0 or index > len(queue_lines):
                    await self.highrise.chat(self.colorize(f"❌ Invalid index. Choose 1 to {len(queue_lines)}", "error"))
                    return
                item = queue_lines[index - 1]
                parts = item.split('|||')
                if len(parts) == 3:
                    username, query_for_streamer, title = parts
                elif len(parts) == 2:
                    username, title = parts
                    query_for_streamer = title
                else:
                    username = "Unknown"
                    query_for_streamer = item
                    title = item
                await self.highrise.chat(self.colorize(f"🔎 Info #{index}:", "info"))
                await self.highrise.chat(self.colorize(f"👤 @{username}", "default"))
                await self.highrise.chat(self.colorize(f"🎵 {title}", "music"))
                await self.highrise.chat(self.colorize(f"🔗 {query_for_streamer}", "info"))
            else:
                if Path(self.notifications_file).exists():
                    with open(self.notifications_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    title = data.get('song_title', 'N/A')
                    duration_seconds = data.get('duration_seconds', 0)
                    requested_by = data.get('requested_by', '')
                    is_user_request = data.get('is_user_request', False)
                    await self.highrise.chat(self.colorize("🔎 Current info:", "info"))
                    await self.highrise.chat(self.colorize(f"🎵 {title}", "music"))
                    await self.highrise.chat(self.colorize(f"⏱️ {self.format_time(duration_seconds)}", "default"))
                    if is_user_request and requested_by:
                        await self.highrise.chat(self.colorize(f"👤 @{requested_by}", "default"))
                else:
                    await self.highrise.chat(self.colorize("🎵 No current info", "info"))
        except Exception as e:
            logger.error(f"❌ Error in dump: {e}")
    
    async def fav_command(self, user: User, args: str):
        try:
            favs = []
            try:
                if Path(self.favorites_file).exists():
                    with open(self.favorites_file, 'r', encoding='utf-8') as f:
                        favs = [line.strip() for line in f.readlines() if line.strip()]
            except Exception:
                favs = []
            
            failed = []
            try:
                failed_file = SystemFiles.FAILED_REQUESTS
                Path(failed_file).touch()
                with open(failed_file, 'r', encoding='utf-8') as f:
                    failed = [line.strip() for line in f.readlines() if line.strip()]
            except Exception:
                failed = []
            
            if args.strip():
                name = args.strip()
                existing = set(favs)
                if name not in existing:
                    with open(self.favorites_file, 'a', encoding='utf-8') as f:
                        f.write(name + "\n")
                    await self.send_whisper_safe(user, self.colorize(f"✅ '{name}' saved to favorites", "success"))
                else:
                    await self.send_whisper_safe(user, self.colorize(f"⚠️ '{name}' already in favorites", "warning"))
                return
            
            # Don't show favorites list on /fav by default
            
            if favs:
                await self.send_whisper_safe(user, self.colorize("⭐ Favorites:", "info"))
                fav_lines = [f"{i}. {s}" for i, s in enumerate(favs[:20], start=1)]
                full_text = "\n".join(fav_lines)
                await self.send_whisper_long(user, full_text)
            else:
                await self.send_whisper_safe(user, self.colorize("📋 No favorites yet", "info"))
        except Exception as e:
            logger.error(f"❌ Error in fav: {e}")
    
    async def clear_fav_command(self, user: User, args: str):
        try:
            favs = []
            if Path(self.favorites_file).exists():
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    favs = [line.strip() for line in f.readlines() if line.strip()]
            if not args.strip():
                with open(self.favorites_file, 'w', encoding='utf-8') as f:
                    f.write("")
                await self.highrise.chat(self.colorize("🗑️ All favorites cleared", "success"))
                return
            arg = args.strip()
            removed = False
            new_favs = []
            if arg.isdigit():
                idx = int(arg)
                for i, s in enumerate(favs, start=1):
                    if i == idx and not removed:
                        removed = True
                        continue
                    new_favs.append(s)
            else:
                name = arg
                for s in favs:
                    if s == name and not removed:
                        removed = True
                        continue
                    new_favs.append(s)
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                for s in new_favs:
                    f.write(s + "\n")
            if removed:
                await self.highrise.chat(self.colorize("✅ Removed from favorites", "success"))
            else:
                await self.highrise.chat(self.colorize("⚠️ Item not found", "warning"))
        except Exception as e:
            logger.error(f"❌ Error in cfav: {e}")
    
    def format_views(self, view_count: int) -> str:
        """Convert view count to readable format"""
        if view_count is None:
            return "N/A"
        if view_count >= 1_000_000_000:
            return f"{view_count / 1_000_000_000:.1f}B"
        elif view_count >= 1_000_000:
            return f"{view_count / 1_000_000:.1f}M"
        elif view_count >= 1_000:
            return f"{view_count / 1_000:.1f}K"
        else:
            return str(view_count)
    
    def format_upload_date(self, upload_date: str) -> str:
        """Convert upload date to 'X years/months/days ago'"""
        if not upload_date:
            return "N/A"
        try:
            # Date format YYYYMMDD
            year = int(upload_date[:4])
            month = int(upload_date[4:6])
            day = int(upload_date[6:8])
            upload = datetime(year, month, day)
            now = datetime.now()
            diff = now - upload
            
            days = diff.days
            if days < 1:
                return "Today"
            elif days == 1:
                return "Yesterday"
            elif days < 7:
                return f"{days} days ago"
            elif days < 30:
                weeks = days // 7
                return f"{weeks} week{'s' if weeks > 1 else ''} ago"
            elif days < 365:
                months = days // 30
                return f"{months} month{'s' if months > 1 else ''} ago"
            else:
                years = days // 365
                return f"{years} year{'s' if years > 1 else ''} ago"
        except:
            return "N/A"
    
    def generate_progress_bar(self, elapsed_seconds: int, total_seconds: int, bar_length: int = 10) -> str:
        """Create progress bar for song"""
        if total_seconds <= 0:
            return "▱" * bar_length
        
        progress = min(elapsed_seconds / total_seconds, 1.0)
        filled = int(progress * bar_length)
        empty = bar_length - filled
        return "▰" * filled + "▱" * empty
    
    def format_time(self, seconds: int) -> str:
        """Convert seconds to mm:ss"""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
    
    async def bot_wallet_command(self, user: User):
        """Check bot's wallet balance (Owner only)"""
        if not await self.is_main_owner(user):
            await self.send_whisper_safe(user, "❌ This command is for the Owner only")
            return
        
        try:
            wallet = await self.highrise.get_wallet()
            content = wallet.content
            amount = 0
            for item in content:
                if item.type == 'currency':
                    amount = item.amount
                    break
            await self.send_whisper_safe(user, f"💰 Bot Wallet Balance: {amount} Gold")
        except Exception as e:
            logger.error(f"Error checking wallet: {e}")
            await self.send_whisper_safe(user, "❌ Failed to check wallet balance")

    async def _send_tip(self, user_id: str, amount: int):
        """Helper to send tip"""
        bars = {
            1: "gold_bar_1", 5: "gold_bar_5", 10: "gold_bar_10",
            50: "gold_bar_50", 100: "gold_bar_100", 500: "gold_bar_500",
            1000: "gold_bar_1000", 5000: "gold_bar_5000", 10000: "gold_bar_10000"
        }
        if amount in bars:
             await self.highrise.tip_user(user_id, bars[amount])
        else:
             remaining = amount
             sorted_bars = sorted(bars.keys(), reverse=True)
             for val in sorted_bars:
                 while remaining >= val:
                     await self.highrise.tip_user(user_id, bars[val])
                     remaining -= val
                     await asyncio.sleep(0.5)

    async def tip_all_command(self, user: User, args: str):
        """Tip all users in the room"""
        if not await self.is_main_owner(user):
             await self.send_whisper_safe(user, "❌ This command is for the Owner only")
             return

        amount = self.tickets_system.get_autotip_amount()
        if args and args.strip().isdigit():
            amount = int(args.strip())
        
        if amount <= 0:
            await self.highrise.chat("❌ Please specify amount or set Autotip first")
            return

        try:
            room_users = await self.highrise.get_room_users()
            count = 0
            await self.highrise.chat(f"💰 Tipping {amount}g to everyone...")
            for u, _ in room_users.content:
                if u.id != user.id: 
                     try:
                         await self._send_tip(u.id, amount)
                         count += 1
                         await asyncio.sleep(1)
                     except Exception:
                         pass
            await self.highrise.chat(f"✅ Tipped {count} users")
        except Exception as e:
            logger.error(f"Error in tipall: {e}")
            await self.highrise.chat("❌ Error executing tipall")

    async def random_tip_command(self, user: User, args: str):
        """Tip a random user"""
        if not await self.is_main_owner(user):
             await self.send_whisper_safe(user, "❌ This command is for the Owner only")
             return

        if not args.strip().isdigit():
            await self.highrise.chat("❌ Usage: -randomtip <amount>")
            return
        
        amount = int(args.strip())
        try:
            room_users = await self.highrise.get_room_users()
            others = [u for u, _ in room_users.content if u.id != user.id]
            if not others:
                await self.highrise.chat("⚠️ No other users in room")
                return
            
            lucky = random.choice(others)
            await self._send_tip(lucky.id, amount)
            await self.highrise.chat(f"🎲 Random tip! {lucky.username} got {amount}g")
        except Exception as e:
            logger.error(f"Error in randomtip: {e}")

    async def clear_queue_command(self, user: User):
        """Clear the song queue"""
        if not await self.is_management_allowed(user):
            await self.send_whisper_safe(user, "❌ This command is for Staff/Owner only")
            return
            
        try:
            count = 0
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    count = len(lines)
                
                with open(self.queue_file, 'w', encoding='utf-8') as f:
                    f.write("")
            
            if count > 0:
                await self.highrise.chat(self.colorize(f"✅ Queue cleared ({count} songs)", "success"))
            else:
                await self.highrise.chat(self.colorize("⚠️ Queue is already empty", "warning"))
        except Exception as e:
            logger.error(f"Error clearing queue: {e}")



    async def mod_fplay_command(self, user: User, args: str):
        """Force play a song (Front of queue)"""
        if not await self.is_management_allowed(user):
            await self.send_whisper_safe(user, "❌ This command is for Staff/Owner only")
            return
            
        if not args:
            await self.send_whisper_safe(user, "❌ Usage: -fplay <song name>")
            return
            
        try:
            entry = f"{user.username}|||{args}|||{args}"
            lines = []
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
            
            lines.insert(0, entry)
            
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
                
            await self.send_whisper_safe(user, f"✅ Added '{args}' to front of queue")
        except Exception as e:
            logger.error(f"Error in fplay: {e}")

    async def mod_remove_command(self, user: User, args: str):
        """Remove song from queue by index"""
        if not await self.is_management_allowed(user):
            await self.send_whisper_safe(user, "❌ This command is for Staff/Owner only")
            return
            
        if not args.isdigit():
            await self.send_whisper_safe(user, "❌ Usage: -remove <number>")
            return
            
        index = int(args)
        try:
            if not Path(self.queue_file).exists():
                await self.send_whisper_safe(user, "⚠️ Queue is empty")
                return
                
            lines = []
            with open(self.queue_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                
            if index < 1 or index > len(lines):
                await self.send_whisper_safe(user, f"❌ Invalid number. Choose 1 to {len(lines)}")
                return
                
            removed = lines.pop(index - 1)
            
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n' if lines else "")
                
            parts = removed.split('|||')
            title = parts[-1] if len(parts) > 1 else removed
            await self.highrise.chat(f"🗑️ Removed song #{index}: {title}")
        except Exception as e:
            logger.error(f"Error removing song: {e}")

    async def mod_check_balance_command(self, user: User, args: str):
        """Check another user's balance"""
        if not await self.is_management_allowed(user):
            await self.send_whisper_safe(user, "❌ This command is for Staff/Owner only")
            return
            
        target = args.strip().lstrip('@')
        if not target:
            await self.send_whisper_safe(user, "❌ Usage: -Check @user")
            return
            
        tickets = self.tickets_system.get_user_tickets(target)
        await self.send_whisper_safe(user, f"🎫 {target} has {tickets} tickets")

    async def mod_skip_command(self, user: User):
        """Skip current song (Staff/VIP or Own Song)"""
        allowed = False
        
        # Check if user owns the current song
        is_own_song = False
        try:
            if Path(self.notifications_file).exists():
                with open(self.notifications_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get('requested_by') == user.username:
                    is_own_song = True
        except:
            pass

        if is_own_song:
             await self.highrise.chat(self.colorize(f"⏭️ @{user.username} skipped their own song.", "success"))
             Path("skip_signal.txt").touch()
             return

        if await self.is_management_allowed(user):
            allowed = True
        elif self.is_vip(user.username):
             allowed = True
        
        if not allowed:
            await self.highrise.chat(self.colorize("❌ This command is for VIP/Staff only, or skip your own song.", "error"))
            return
            
        try:
            self.current_likes = set()
            Path("skip_signal.txt").touch()
            await self.highrise.chat(self.colorize("⏭️ Skipping song...", "success"))
        except Exception as e:
            logger.error(f"Error skipping: {e}")

    async def leaderboard_command(self, user: User):
        """Show Top 5 most played songs"""
        if not await self.is_management_allowed(user):
            return
            
        try:
            stats = {}
            if Path(self.tickets_system.song_stats_file).exists():
                with open(self.tickets_system.song_stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            
            if not stats:
                await self.send_whisper_safe(user, "📊 No song data yet")
                return
                
            sorted_songs = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:5]
            
            msg = ["🏆 Top 5 Songs:"]
            for i, (song, count) in enumerate(sorted_songs, 1):
                msg.append(f"{i}. {song} ({count} plays)")
            
            await self.send_whisper_long(user, "\n".join(msg))
        except Exception as e:
            logger.error(f"Error in leaderboard: {e}")

    async def summon_command(self, user: User, args: str):
        """Summon a user"""
        allowed = False
        if await self.is_management_allowed(user):
            allowed = True
        elif self.is_vip(user.username):
            allowed = True
            
        if not allowed:
            await self.send_whisper_safe(user, "❌ This command is for VIP/Staff only")
            return
            
        target_name = args.strip().lstrip('@')
        if not target_name:
            await self.send_whisper_safe(user, "❌ Usage: -summon @user")
            return
            
        target_id = await self._resolve_user_id(target_name)
        if not target_id:
             await self.send_whisper_safe(user, f"❌ User {target_name} not found")
             return
             
        try:
            await self.highrise.send_whisper(target_id, f"📣 {user.username} is summoning you!")
            await self.send_whisper_safe(user, f"✅ Summon sent to {target_name}")
        except Exception:
            await self.send_whisper_safe(user, "❌ Failed to send summon")

    async def like_song_command(self, user: User):
        """Like current song"""
        if not hasattr(self, "current_likes"):
            self.current_likes = set()
            
        if user.username in self.current_likes:
            await self.send_whisper_safe(user, "⚠️ You already liked this song")
            return
            
        self.current_likes.add(user.username)
        await self.highrise.chat(f"❤️ {user.username} liked this song! (Total: {len(self.current_likes)})")

    async def unlike_song_command(self, user: User):
        """Unlike current song"""
        if not hasattr(self, "current_likes"):
            self.current_likes = set()
            
        if user.username not in self.current_likes:
            await self.send_whisper_safe(user, "⚠️ You haven't liked this song")
            return
            
        self.current_likes.remove(user.username)
        await self.highrise.chat(f"💔 {user.username} unliked. (Total: {len(self.current_likes)})")

    async def search_and_show_results(self, user: User, query: str, offset: int = 0):
        """Search YouTube and show results"""
        # Check if query is a number (to request song from queue)
        try:
            queue_index = int(query)
            await self.play_from_queue_by_index(user, queue_index)
            return
        except ValueError:
            pass # Not a number, proceed with normal search
        try:
            # Clean query from repeated commands like "!play !play song"
            if query.lower().startswith("!play"):
                query = query.split(maxsplit=1)[-1]

            is_url = "youtu.be/" in query or "youtube.com/" in query
            # Clean YouTube URL from extra parameters like 'si', 'list', 't'
            if is_url:
                query = re.sub(r"(\?|&).*", "", query)

            # Check permissions and tickets
            is_unlimited = await self.has_unlimited_access(user, show_message=True)
            if not is_unlimited:
                user_tickets = self.tickets_system.get_user_tickets(user.username)
                if user_tickets <= 0:
                    msg, color = BotResponses.NO_TICKETS
                    await self.highrise.chat(self.colorize(msg.format(username=user.username), color))
                    return
                else:
                    pass
            else:
                msg, color = BotResponses.VIP_PLAY_UNLIMITED
                await self.highrise.chat(self.colorize(msg, color))
            
            msg, color = BotResponses.SEARCHING
            await self.highrise.chat(self.colorize(msg.format(query=query), color))
            
            # Search using yt-dlp with full info (no flat-playlist to get views and upload_date)
            cmd = [
                sys.executable, "-m", "yt_dlp",  # Use Python module for compatibility
                "--dump-json",
                "--skip-download",
                "--no-warnings",
                "--no-check-certificates",
            ]
            
            # Add cookies if available
            if Path("cookies.txt").exists() and Path("cookies.txt").stat().st_size > 100:
                cmd.extend(["--cookies", "cookies.txt"])
                
            # Use URL directly if it is a URL, or search if it is text
            if is_url:
                cmd.append(query)
            else:
                cmd.append(f"ytsearch1:{query}")
            
            # Use asyncio for asynchronous search
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
            except asyncio.TimeoutError:
                process.kill()
                msg, color = BotResponses.SEARCH_TIMEOUT
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            if process.returncode != 0:
                # Fallback: Search for first 10 results and take the first one
                fallback_cmd = [
                    sys.executable, "-m", "yt_dlp",
                    "--dump-json",
                    "--skip-download",
                    "--no-warnings",
                    "--no-check-certificates",
                    f"ytsearch10:{query}"
                ]
                process2 = await asyncio.create_subprocess_exec(
                    *fallback_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout2, stderr2 = await process2.communicate()
                if process2.returncode != 0 or not stdout2:
                    msg, color = BotResponses.SEARCH_FAILED
                    await self.highrise.chat(self.colorize(msg, color))
                    logger.error(f"Search error: {stderr.decode() or stderr2.decode()}")
                    return
                # Take first JSON line from results
                output_lines = [l for l in stdout2.decode().splitlines() if l.strip()]
                if not output_lines:
                    msg, color = BotResponses.NO_RESULTS
                    await self.highrise.chat(self.colorize(msg, color))
                    return
                output = output_lines[0]
            else:
                output = stdout.decode().strip()
            
            if not output:
                msg, color = BotResponses.NO_RESULTS
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            try:
                # Define variables with default values to avoid errors
                title = 'Untitled'
                webpage_url = ''
                
                data = json.loads(output)
                title = data.get('title', 'Untitled')
                webpage_url = data.get('webpage_url', '') # Extract URL from data
                duration = data.get('duration', 0)
                view_count = data.get('view_count', 0)
                upload_date = data.get('upload_date', '')
                
                # Convert duration to readable format
                minutes = int(duration) // 60
                seconds = int(duration) % 60
                duration_str = f"{minutes}:{seconds:02d}"
                
                # Convert views and upload date
                views_str = self.format_views(view_count)
                released_str = self.format_upload_date(upload_date)
                
                # Determine what to pass to streamer (clean URL or original search query)
                # URL is cleaned here after confirming its existence
                normalized_url = self._normalize_youtube_url(webpage_url)
                query_for_streamer = normalized_url if is_url else query
                
                # Prevent duplicate song for the same user only
                if Path(self.queue_file).exists():
                    with open(self.queue_file, 'r', encoding='utf-8') as f:
                        existing_queue_items = [line.strip() for line in f.readlines() if line.strip()]
                    
                    for item in existing_queue_items:
                        parts = item.split('|||')
                        if len(parts) >= 2:  # username|||query_for_streamer|||title_for_display
                            existing_username = parts[0]
                            existing_query_for_streamer_in_queue = parts[1]
                            
                            # Same user?
                            if existing_username.lower() == user.username.lower():
                                if is_url:
                                    # Compare clean URLs
                                    if normalized_url and self._normalize_youtube_url(existing_query_for_streamer_in_queue) == normalized_url:
                                        msg, color = BotResponses.DUPLICATE_SONG_IN_QUEUE
                                        await self.highrise.chat(self.colorize(msg.format(title=title), color))
                                        logger.info(f"⚠️ Duplicate prevention for user: {user.username} - {title}")
                                        return
                                else:
                                    # Compare search text after simple cleaning
                                    def norm_text(s: str) -> str:
                                        return re.sub(r"\s+", " ", s).strip().lower()
                                    if norm_text(existing_query_for_streamer_in_queue) == norm_text(query):
                                        msg, color = BotResponses.DUPLICATE_SONG_IN_QUEUE
                                        await self.highrise.chat(self.colorize(msg.format(title=title), color))
                                        logger.info(f"⚠️ Duplicate prevention for user: {user.username} - {title}")
                                        return



            except Exception as e:
                logger.error(f"Error parsing results: {e}")
                msg, color = BotResponses.SEARCH_ERROR
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            # Read current queue to add song at the beginning
            queue_lines = []
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    queue_lines = [line.strip() for line in f.readlines() if line.strip()]
            
            # Add song to queue with new format: username|||query_for_streamer|||title_for_display
            item_to_queue_full = f"{user.username}|||{query_for_streamer}|||{title}"
            
            # Add new request at the end of the queue to maintain order
            queue_lines.append(item_to_queue_full)

            # Write updated queue
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                for line in queue_lines:
                    f.write(f"{line}\n")

            # Disable default playlist as long as there is a queue
            try:
                state = {}
                if Path(SystemFiles.PLAYLIST_STATE).exists():
                    with open(SystemFiles.PLAYLIST_STATE, 'r', encoding='utf-8') as f:
                        try:
                            state = json.load(f) or {}
                        except Exception:
                            state = {}
                state['disable_default_playlist'] = True
                with open(SystemFiles.PLAYLIST_STATE, 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

            # Deduct ticket if not VIP
            if not is_unlimited:
                self.tickets_system.use_ticket(user.username)

            # Determine song position in queue
            queue_position = len(queue_lines)
            
            # Song request confirmation message in new format
            request_msg = BotResponses.SONG_REQUESTED.format(
                username=user.username,
                title=title,
                duration=duration_str,
                views=views_str,
                released=released_str,
                position=queue_position
            )
            await self.highrise.chat(request_msg)
            logger.info(f"🎵 Added '{title}' ({query_for_streamer}) to queue by {user.username}")
            
            # Auto-save to favorites if user is owner or developer
            try:
                if self.is_owner(user.username) or self.tickets_system.is_dev(user.username):
                    favs = []
                    if Path(self.favorites_file).exists():
                        with open(self.favorites_file, 'r', encoding='utf-8') as f:
                            favs = [line.strip() for line in f.readlines() if line.strip()]
                    if title not in set(favs):
                        with open(self.favorites_file, 'a', encoding='utf-8') as f:
                            f.write(title + "\n")
                        logger.info(f"⭐ Automatically added '{title}' to favorites by @{user.username}")
            except Exception as e:
                logger.debug(f"Failed to auto-save favorites: {e}")
            
            try:
                Path("skip_default_only.txt").touch()
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            msg, color = BotResponses.SEARCH_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def dance_once_command(self):
        """Stop dances and play floss dance"""
        try:
            await self.stop_continuous_dancing()
            await self.highrise.send_emote("dance-floss")
            await self.highrise.chat(self.colorize("💃 Playing floss dance", "dance"))
        except Exception as e:
            logger.error(f"❌ Dance execution error: {e}")
    
    async def send_current_song(self):
        """Send current song info with progress bar"""
        try:
            if Path(self.notifications_file).exists():
                with open(self.notifications_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                song_title = data.get('song_title', 'No song')
                duration_seconds = data.get('duration_seconds', 0)
                start_time_str = data.get('start_time')
                is_user_request = data.get('is_user_request', False)
                requested_by = data.get('requested_by', '')
                
                # Calculate elapsed time
                elapsed_seconds = 0
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str)
                        elapsed_seconds = int((datetime.now() - start_time).total_seconds())
                        elapsed_seconds = max(0, min(elapsed_seconds, duration_seconds))
                    except:
                        pass
                
                # Create progress bar
                progress_bar = self.generate_progress_bar(elapsed_seconds, duration_seconds)
                elapsed_str = self.format_time(elapsed_seconds)
                total_str = self.format_time(duration_seconds)
                
                # Send message in new format
                if is_user_request and requested_by:
                    msg = BotResponses.NOW_PLAYING.format(
                        title=song_title,
                        elapsed=elapsed_str,
                        progress_bar=progress_bar,
                        total=total_str,
                        username=requested_by
                    )
                else:
                    msg = BotResponses.NOW_PLAYING_DEFAULT.format(
                        title=song_title,
                        elapsed=elapsed_str,
                        progress_bar=progress_bar,
                        total=total_str
                    )
                await self.highrise.chat(msg)
            else:
                msg, color = BotResponses.NO_SONG_INFO
                await self.highrise.chat(self.colorize(msg, color))
        except Exception as e:
            logger.error(f"❌ Error reading current song: {e}")
            msg, color = BotResponses.SONG_INFO_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def send_queue_status(self, user: User = None):
        """Send queue status"""
        try:
            queue_items = []
            
            # 1. Add current song (Now Playing)
            try:
                display_name = None
                if Path(self.notifications_file).exists():
                    with open(self.notifications_file, 'r', encoding='utf-8') as nf:
                        nd = json.load(nf)
                        title = nd.get('song_title')
                        is_user_req = nd.get('is_user_request', False)
                        requester = nd.get('requested_by', '')
                        if title:
                            display_name = f"{title} - @{requester}" if is_user_req and requester else title
                if not display_name and Path(SystemFiles.PLAYLIST_STATE).exists():
                    with open(SystemFiles.PLAYLIST_STATE, 'r', encoding='utf-8') as f:
                        state = json.load(f)
                        current_song = state.get('current_song')
                        if current_song:
                            display_name = current_song if "|||" not in current_song else f"{current_song.split('|||')[-1]} - @{current_song.split('|||')[0]}"
                if display_name:
                    prefix = "<#FFD700>▶️ NOW : "
                    queue_items.append(f"\u202A{prefix}{display_name}\u202C")
            except Exception as e:
                logger.error(f"Error reading current song: {e}")

            # 2. Read queue
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    file_lines = [line.strip() for line in f.readlines() if line.strip()]
                
                for i, line in enumerate(file_lines, 1):
                    parts = line.split('|||')
                    if len(parts) == 3: # New format: username|||query_for_streamer|||title_for_display
                        username, _, title = parts
                        display_song = title[:50] + "..." if len(title) > 50 else title
                        # \u202A to force LTR embedding for the whole line
                        queue_items.append(f"\u202A{i}. {display_song} - @{username}\u202C")
                    elif len(parts) == 2: # Old format: username|||song_query
                        username, song_query = parts
                        display_song = song_query[:50] + "..." if len(song_query) > 50 else song_query
                        queue_items.append(f"\u202A{i}. {display_song} - @{username}\u202C")
                    else:
                        display_song = line[:50] + "..." if len(line) > 50 else line
                        queue_items.append(f"\u202A{i}. {display_song}\u202C")

            if not queue_items:
                msg, color = BotResponses.QUEUE_EMPTY
                text = self.colorize(msg, color)
                if user:
                    await self.send_whisper_safe(user, text)
                else:
                    await self.highrise.chat(text)
                return

            # 3. Display queue (whisper and split)
            # Add separator line between first item (Next) and rest of queue for clarity
            if len(queue_items) > 1:
                queue_items.insert(1, "─────────────────")

            full_text = "\n".join(queue_items)
            
            if user:
                await self.send_whisper_long(user, full_text)
            else:
                # Fallback
                chunk_size = 5
                for i in range(0, len(queue_items), chunk_size):
                    chunk = queue_items[i:i + chunk_size]
                    message = "\n".join(chunk)
                    await self.highrise.chat(self.colorize(message, "default"))
                    await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"❌ Error reading queue: {e}")
    
    async def add_owner_command(self, user: User, username: str):
        """Add additional owner (Main owner only)"""
        try:
            if user.username != self.owner_username:
                msg, color = BotResponses.OWNER_ONLY_COMMAND
                await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=self.owner_username), color))
                return
            
            if not username:
                msg, color = BotResponses.ADDOWNER_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            username = username.strip().lstrip('@')  # Remove @ if present
            
            if username == self.owner_username:
                msg, color = BotResponses.ADDOWNER_ALREADY_MAIN_OWNER
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            if self.add_owner(username):
                msg, color = BotResponses.ADDOWNER_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.ADDOWNER_ALREADY_OWNER
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
                
        except Exception as e:
            logger.error(f"❌ Error adding owner: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def remove_owner_command(self, user: User, username: str):
        """Remove additional owner (Main owner only)"""
        try:
            if user.username != self.owner_username:
                msg, color = BotResponses.OWNER_ONLY_COMMAND
                await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=self.owner_username), color))
                return
            
            if not username:
                msg, color = BotResponses.REMOVEOWNER_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            username = username.strip().lstrip('@')  # Remove @ if present
            
            if username == self.owner_username:
                msg, color = BotResponses.REMOVEOWNER_CANNOT_REMOVE_MAIN
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            if self.remove_owner(username):
                # Remove from staff cache as well if present
                if username in self.detected_staff:
                    del self.detected_staff[username]
                    self._save_staff_cache()
                    logger.info(f"✅ Removed {username} from staff cache")
                
                msg, color = BotResponses.REMOVEOWNER_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.REMOVEOWNER_NOT_OWNER
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
                
        except Exception as e:
            logger.error(f"❌ Error removing owner: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def list_owners_command(self):
        """Show owners list"""
        try:
            msg, color = BotResponses.LISTOWNERS_HEADER
            await self.highrise.chat(self.colorize(msg, color))
            
            msg, color = BotResponses.LISTOWNERS_MAIN_OWNER
            await self.highrise.chat(self.colorize(msg.format(username=self.owner_username), color))
            
            if self.additional_owners:
                for owner in self.additional_owners:
                    msg, color = BotResponses.LISTOWNERS_ADDITIONAL_OWNER
                    await self.highrise.chat(self.colorize(msg.format(username=owner), color))
            else:
                msg, color = BotResponses.LISTOWNERS_NO_ADDITIONAL
                await self.highrise.chat(self.colorize(msg, color))
                
        except Exception as e:
            logger.error(f"❌ Error listing owners: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
        
    async def add_vip_command(self, user: User, username: str):
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            if not username:
                msg, color = BotResponses.FREE_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = username.strip().lstrip('@')
            if self.tickets_system.is_vip(username):
                msg, color = BotResponses.VIP_ALREADY
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
                return
            if self.tickets_system.add_vip(username):
                msg, color = BotResponses.VIP_RECEIVED
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.COMMAND_ERROR
                await self.highrise.chat(self.colorize(msg, color))
        except Exception as e:
            logger.error(f"❌ Error adding VIP: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def remove_vip_command(self, user: User, username: str):
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            if not username:
                msg, color = BotResponses.UNFREE_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = username.strip().lstrip('@')
            if self.tickets_system.remove_vip(username):
                msg, color = BotResponses.UNFREE_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.UNFREE_NOT_VIP
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
        except Exception as e:
            logger.error(f"❌ Error removing VIP: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def add_mod_command(self, user: User, username: str):
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            if not username:
                msg, color = BotResponses.ADDOWNER_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = username.strip().lstrip('@')
            if self.detected_staff.get(username) == "Developer":
                msg, color = BotResponses.ADDMOD_ALREADY
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
                return
            self.detected_staff[username] = "Developer"
            self._save_staff_cache()
            msg, color = BotResponses.ADDMOD_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(username=username), color))
        except Exception as e:
            logger.error(f"❌ Error adding mod: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def remove_mod_command(self, user: User, username: str):
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            if not username:
                msg, color = BotResponses.REMOVEOWNER_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = username.strip().lstrip('@')
            if self.detected_staff.get(username) != "Developer":
                msg, color = BotResponses.RMOD_NOT_FOUND
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
                return
            del self.detected_staff[username]
            self._save_staff_cache()
            msg, color = BotResponses.RMOD_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(username=username), color))
        except Exception as e:
            logger.error(f"❌ Error removing mod: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    async def skip_song(self, user: User):
        """Skip current song immediately (VIP, Mods, or Owner only)"""
        try:
            # Check permissions (VIP, Mod, or Owner)
            if not await self.has_unlimited_access(user, show_message=True):
                msg, color = BotResponses.NOT_VIP_OR_STAFF
                await self.highrise.chat(self.colorize(msg.format(username=user.username), color))
                logger.info(f"⛔ {user.username} tried to skip song (not allowed)")
                return
            
            # VIP message
            msg, color = BotResponses.VIP_SKIP_UNLIMITED
            await self.highrise.chat(self.colorize(msg, color))
            
            # Save current song info for announcement
            skipped_title = self.current_song or "Unknown"
            skipped_by = ""
            
            # Read skipped song info
            if Path(self.notifications_file).exists():
                try:
                    with open(self.notifications_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    skipped_title = data.get('song_title', skipped_title)
                    skipped_by = data.get('requested_by', '')
                except:
                    pass
            
            # Check for next song
            next_song = "Default Song"
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                    if lines:
                        next_song = lines[0]
            
            # Send skip signal
            Path("skip_signal.txt").touch()
            msg, color = BotResponses.SKIPPING_SONG
            await self.highrise.chat(self.colorize(msg, color))
            logger.info(f"⏭️ {user.username} requested skip")
            
            # Wait and verify skip success (short delay for faster response)
            await asyncio.sleep(0.5)
            
            # Check if song changed or skip signal gone
            skip_file_gone = not Path("skip_signal.txt").exists()
            song_changed = self.current_song != skipped_title
            
            if skip_file_gone or song_changed:
                # Send Skipped message in new format
                if skipped_by:
                    skip_msg = BotResponses.SONG_SKIPPED.format(
                        title=skipped_title,
                        username=skipped_by
                    )
                    await self.highrise.chat(skip_msg)
                else:
                    msg, color = BotResponses.SKIP_SUCCESS
                    await self.highrise.chat(self.colorize(msg.format(next_song=next_song), color))
            else:
                msg, color = BotResponses.SKIP_TRYING
                await self.highrise.chat(self.colorize(msg, color))
                
        except Exception as e:
            logger.error(f"❌ Error skipping song: {e}")
            msg, color = BotResponses.SKIP_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def play_from_queue_by_index(self, user: User, index: int):
        """Play specific song from queue by index"""
        try:
            if not Path(self.queue_file).exists():
                msg, color = BotResponses.QUEUE_EMPTY
                await self.highrise.chat(self.colorize(msg, color))
                return

            with open(self.queue_file, 'r', encoding='utf-8') as f:
                queue_lines = [line.strip() for line in f.readlines() if line.strip()]

            if not queue_lines:
                msg, color = BotResponses.QUEUE_EMPTY
                await self.highrise.chat(self.colorize(msg, color))
                return

            if index <= 0 or index > len(queue_lines):
                msg, color = BotResponses.INVALID_QUEUE_INDEX
                await self.highrise.chat(self.colorize(msg.format(max=len(queue_lines)), color))
                return

            # Get requested item from queue
            requested_item_full = queue_lines[index - 1] # -1 because queue starts at 1 for user
            
            # Extract parts (username, streamer query, title)
            parts = requested_item_full.split('|||')
            if len(parts) == 3:
                original_requester_username, query_for_streamer, song_title = parts
            elif len(parts) == 2: # Handle old format
                original_requester_username, song_query = parts
                query_for_streamer = song_query # Use original query for streamer
                song_title = song_query # Use query as title
            else: # Handle invalid lines
                original_requester_username = "Unknown"
                query_for_streamer = requested_item_full
                song_title = requested_item_full

            # Check permissions (VIP, Mod, or Owner)
            is_unlimited = await self.has_unlimited_access(user, show_message=True)
            
            if not is_unlimited:
                # Check tickets for normal user
                user_tickets = self.tickets_system.get_user_tickets(user.username)
                if user_tickets <= 0:
                    msg, color = BotResponses.NO_TICKETS
                    await self.highrise.chat(self.colorize(msg.format(username=user.username), color))
                    return
                self.tickets_system.use_ticket(user.username)
                msg, color = BotResponses.TICKET_USED
                await self.highrise.chat(self.colorize(msg.format(remaining=self.tickets_system.get_user_tickets(user.username)), color))
            else:
                msg, color = BotResponses.VIP_PLAY_UNLIMITED
                await self.highrise.chat(self.colorize(msg, color))

            # Remove song from current position
            del queue_lines[index - 1]

            # Add to start of queue (to play next)
            new_queue_entry = f"{user.username}|||{query_for_streamer}|||{song_title}"
            queue_lines.insert(0, new_queue_entry)

            with open(self.queue_file, 'w', encoding='utf-8') as f:
                for line in queue_lines:
                    f.write(f"{line}\n")
            
            msg, color = BotResponses.PLAYING_FROM_QUEUE
            await self.highrise.chat(self.colorize(msg.format(song=song_title, username=user.username), color))
            logger.info(f"🎵 {user.username} requested to play '{song_title}' from queue index {index}")

            # Send signal to streamer to play next song immediately
            Path("skip_signal.txt").touch()

        except Exception as e:
            logger.error(f"❌ Error playing song from queue by index: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def play_from_default_playlist(self, user: User, query: str):
        """Search in default playlist and play a song immediately"""
        try:
            if not query:
                msg, color = BotResponses.DPLAY_NO_QUERY
                await self.highrise.chat(self.colorize(msg, color))
                return

            # Check permissions (VIP or Staff or Owner)
            is_unlimited = await self.has_unlimited_access(user, show_message=True)
            if not is_unlimited:
                msg, color = BotResponses.NOT_VIP_OR_STAFF
                await self.highrise.chat(self.colorize(msg.format(username=user.username), color))
                return

            # Load default playlist
            if not Path(self.default_playlist_file).exists():
                msg, color = BotResponses.DPLAY_NO_PLAYLIST
                await self.highrise.chat(self.colorize(msg, color))
                return

            with open(self.default_playlist_file, 'r', encoding='utf-8') as f:
                default_playlist = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]

            if not default_playlist:
                msg, color = BotResponses.DPLAY_NO_PLAYLIST
                await self.highrise.chat(self.colorize(msg, color))
                return

            # Search for song in default playlist
            found_song = None
            for song in default_playlist:
                if query.lower() in song.lower():
                    found_song = song
                    break

            if not found_song:
                msg, color = BotResponses.DPLAY_NOT_FOUND
                await self.highrise.chat(self.colorize(msg.format(query=query), color))
                return

            # Add song to start of queue to play immediately
            queue_lines = []
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    queue_lines = [line.strip() for line in f.readlines() if line.strip()]

            item_to_queue_full = f"{user.username}|||{found_song}|||{found_song}"
            queue_lines.insert(0, item_to_queue_full)

            with open(self.queue_file, 'w', encoding='utf-8') as f:
                for line in queue_lines:
                    f.write(f"{line}\n")

            Path("skip_signal.txt").touch()
            msg, color = BotResponses.DPLAY_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(song=found_song), color))
            logger.info(f"🎵 {user.username} requested to play '{found_song}' from default playlist.")

        except Exception as e:
            logger.error(f"❌ Error playing from default playlist: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))

    async def remove_from_queue_command(self, user: User, args: str):
        """Remove song from queue using its index (for VIP/Staff)"""
        try:
            # Check permissions
            if not await self.has_unlimited_access(user, show_message=False):
                msg, color = BotResponses.NOT_VIP_OR_STAFF
                await self.highrise.chat(self.colorize(msg.format(username=user.username), color))
                return

            if not args.strip().isdigit():
                msg, color = BotResponses.RMQUEUE_NO_INDEX
                await self.highrise.chat(self.colorize(msg, color))
                return

            index_to_remove = int(args.strip())

            if not Path(self.queue_file).exists():
                msg, color = BotResponses.QUEUE_EMPTY
                await self.highrise.chat(self.colorize(msg, color))
                return

            with open(self.queue_file, 'r', encoding='utf-8') as f:
                queue_lines = [line.strip() for line in f.readlines() if line.strip()]

            if not queue_lines:
                msg, color = BotResponses.QUEUE_EMPTY
                await self.highrise.chat(self.colorize(msg, color))
                return

            if index_to_remove <= 0 or index_to_remove > len(queue_lines):
                msg, color = BotResponses.RMQUEUE_INVALID_INDEX
                await self.highrise.chat(self.colorize(msg.format(max=len(queue_lines)), color))
                return

            removed_item_full = queue_lines.pop(index_to_remove - 1)
            song_title = removed_item_full.split('|||')[-1]

            with open(self.queue_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(queue_lines) + '\n')

            msg, color = BotResponses.RMQUEUE_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(index=index_to_remove, title=song_title, username=user.username), color))
            logger.info(f"🗑️ {user.username} removed song #{index_to_remove} ('{song_title}') from queue.")

        except Exception as e:
            logger.error(f"❌ Error removing song from queue: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def play_from_favorites(self, user: User, args: str):
        """Play song from favorites by name or index (Owner/Staff only)"""
        try:
            # Check permissions (Owner/Staff)
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            # Load favorites
            if not Path(self.favorites_file).exists():
                await self.highrise.chat(self.colorize("📋 Favorites list is empty.", "info"))
                return
            with open(self.favorites_file, 'r', encoding='utf-8') as f:
                favs = [line.strip() for line in f.readlines() if line.strip()]
            if not favs:
                await self.highrise.chat(self.colorize("📋 Favorites list is empty.", "info"))
                return
            
            # Determine target song
            target = None
            arg = args.strip()
            if not arg:
                target = favs[0]
            elif arg.isdigit():
                idx = int(arg)
                if idx <= 0 or idx > len(favs):
                    await self.highrise.chat(self.colorize(f"❌ Invalid index. Choose from 1 to {len(favs)}", "error"))
                    return
                target = favs[idx - 1]
            else:
                # Name matching
                for s in favs:
                    if arg.lower() in s.lower():
                        target = s
                        break
                if not target:
                    await self.highrise.chat(self.colorize(f"❌ '{arg}' not found in favorites.", "error"))
                    return
            
            # Add to start of queue for immediate play
            queue_lines = []
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    queue_lines = [line.strip() for line in f.readlines() if line.strip()]
            item_to_queue_full = f"{user.username}|||{target}|||{target}"
            queue_lines.insert(0, item_to_queue_full)
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                for line in queue_lines:
                    f.write(f"{line}\n")
            
            Path("skip_signal.txt").touch()
            msg, color = BotResponses.DPLAY_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(song=target), color))
            logger.info(f"🎵 @{user.username} played from favorites: '{target}'")
        except Exception as e:
            logger.error(f"❌ Error playing from favorites: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))

    async def buy_vip_command(self, user: User, args: str):
        """Buy VIP status with tickets"""
        try:
            username = user.username
            if self.tickets_system.is_vip(username):
                msg, color = BotResponses.VIP_ALREADY
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
                return

            price = HighriseSettings.VIP_PRICE
            
            if self.tickets_system.use_ticket(username, price):
                self.tickets_system.add_vip(username)
                await self.highrise.chat(self.colorize(f"✅ You bought VIP for {price} Tickets! 🌟", "success"))
            else:
                # 600 tickets = 1200 gold (if 10g=5t)
                await self.highrise.chat(f"<#FF0000>❌ You need {price} Tickets to buy VIP.")
                
        except Exception as e:
            logger.error(f"❌ Error buying VIP: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def add_vip_command(self, user: User, args: str):
        """Add VIP user - for Room Owner/Bot Owner/Dev"""
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = args.strip().lstrip('@')
            if not username:
                msg, color = BotResponses.FREE_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            if self.tickets_system.is_vip(username):
                msg, color = BotResponses.VIP_ALREADY
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
                return
            ok = self.tickets_system.add_vip(username)
            if ok:
                msg, color = BotResponses.VIP_RECEIVED
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.COMMAND_ERROR
                await self.highrise.chat(self.colorize(msg, color))
        except Exception as e:
            logger.error(f"❌ Error adding VIP: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def remove_vip_command(self, user: User, args: str):
        """Remove VIP user - for Room Owner/Bot Owner/Dev"""
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = args.strip().lstrip('@')
            if not username:
                msg, color = BotResponses.UNFREE_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            ok = self.tickets_system.remove_vip(username)
            if ok:
                msg, color = BotResponses.UNFREE_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.UNFREE_NOT_VIP
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
        except Exception as e:
            logger.error(f"❌ Error removing VIP: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def add_mod_command(self, user: User, args: str):
        """Add Dev - Free permissions to play/change songs"""
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = args.strip().lstrip('@')
            if not username:
                msg, color = BotResponses.ADDOWNER_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            if self.tickets_system.is_dev(username):
                msg, color = BotResponses.ADDMOD_ALREADY
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
                return
            ok = self.tickets_system.add_dev(username)
            if ok:
                msg, color = BotResponses.ADDMOD_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.COMMAND_ERROR
                await self.highrise.chat(self.colorize(msg, color))
        except Exception as e:
            logger.error(f"❌ Error adding Dev: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def remove_mod_command(self, user: User, args: str):
        """Remove Dev"""
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = args.strip().lstrip('@')
            if not username:
                msg, color = BotResponses.REMOVEOWNER_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            ok = self.tickets_system.remove_dev(username)
            if ok:
                msg, color = BotResponses.RMOD_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.RMOD_NOT_FOUND
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
        except Exception as e:
            logger.error(f"❌ Error removing Dev: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def add_vip_command(self, user: User, args: str):
        """Add user to VIP (Admin only)"""
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = args.strip().lstrip('@')
            if not username:
                msg, color = BotResponses.FREE_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            if self.tickets_system.is_vip(username):
                msg, color = BotResponses.VIP_ALREADY
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
                return
            if self.tickets_system.add_vip(username):
                msg, color = BotResponses.VIP_RECEIVED
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.COMMAND_ERROR
                await self.highrise.chat(self.colorize(msg, color))
        except Exception as e:
            logger.error(f"❌ Error adding VIP: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def remove_vip_command(self, user: User, args: str):
        """Remove user from VIP (Admin only)"""
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = args.strip().lstrip('@')
            if not username:
                msg, color = BotResponses.UNFREE_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            if self.tickets_system.remove_vip(username):
                msg, color = BotResponses.UNFREE_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.UNFREE_NOT_VIP
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
        except Exception as e:
            logger.error(f"❌ Error removing VIP: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def add_mod_command(self, user: User, args: str):
        """Add developer (Admin only)"""
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = args.strip().lstrip('@')
            if not username:
                msg, color = BotResponses.ADDOWNER_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            if self.tickets_system.is_dev(username):
                msg, color = BotResponses.ADDMOD_ALREADY
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
                return
            if self.tickets_system.add_dev(username):
                msg, color = BotResponses.ADDMOD_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.COMMAND_ERROR
                await self.highrise.chat(self.colorize(msg, color))
        except Exception as e:
            logger.error(f"❌ Error adding developer: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    async def remove_mod_command(self, user: User, args: str):
        """Remove developer (Admin only)"""
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            username = args.strip().lstrip('@')
            if not username:
                msg, color = BotResponses.REMOVEOWNER_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            if self.tickets_system.remove_dev(username):
                msg, color = BotResponses.RMOD_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
            else:
                msg, color = BotResponses.RMOD_NOT_FOUND
                await self.highrise.chat(self.colorize(msg.format(username=username), color))
        except Exception as e:
            logger.error(f"❌ Error removing developer: {e}")
            msg, color = BotResponses.COMMAND_ERROR
            await self.highrise.chat(self.colorize(msg, color))

    async def monitor_current_song(self):
        """Monitor current song and announce it - only user requests with delay to match Zeno buffer"""
        pending_announcement = None
        announcement_time = None
        ZENO_BUFFER_DELAY = 25
        
        while self.is_connected:
            try:
                await asyncio.sleep(3)
                
                if not self.is_connected:
                    break
                
                if pending_announcement and announcement_time:
                    if datetime.now() >= announcement_time:
                        progress_bar = self.generate_progress_bar(0, pending_announcement['duration_seconds'])
                        total_str = self.format_time(pending_announcement['duration_seconds'])
                        
                        if pending_announcement.get('requested_by'):
                            msg = BotResponses.NOW_PLAYING.format(
                                title=pending_announcement['title'],
                                elapsed="0:00",
                                progress_bar=progress_bar,
                                total=total_str,
                                username=pending_announcement['requested_by']
                            )
                        else:
                            msg = BotResponses.NOW_PLAYING_DEFAULT.format(
                                title=pending_announcement['title'],
                                elapsed="0:00",
                                progress_bar=progress_bar,
                                total=total_str
                            )
                        await self.highrise.chat(msg)
                        logger.info(f"🎵 Delayed announcement: {pending_announcement['title']}")
                        pending_announcement = None
                        announcement_time = None
                
                if Path(self.notifications_file).exists():
                    with open(self.notifications_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    song_title = data.get('song_title')
                    is_user_request = data.get('is_user_request', False)
                    duration_seconds = data.get('duration_seconds', 0)
                    requested_by = data.get('requested_by', '')
                    
                    if song_title and song_title != self.current_song:
                        self.current_song = song_title
                        
                        if is_user_request:
                            pending_announcement = {
                                'title': song_title, 
                                'duration_seconds': duration_seconds,
                                'requested_by': requested_by
                            }
                            announcement_time = datetime.now() + timedelta(seconds=ZENO_BUFFER_DELAY)
                            logger.info(f"🎵 New user song (announcing in {ZENO_BUFFER_DELAY}s): {song_title}")
                        else:
                            logger.info(f"🎶 Default song (no announcement): {song_title}")
                        
            except Exception as e:
                if "closing transport" in str(e).lower() or "connection" in str(e).lower():
                    logger.warning("⚠️ Song monitoring stopped - Connection closed")
                    self.is_connected = False
                    break
                logger.error(f"❌ Error in monitoring: {e}")
    
    async def announce_song_status(self):
        """Announce current and next song status every 5 minutes"""
        while self.is_connected:
            try:
                await asyncio.sleep(300)
                
                if not self.is_connected:
                    break
                
                if Path(self.notifications_file).exists():
                    with open(self.notifications_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    song_title = data.get('song_title')
                    end_time_str = data.get('end_time')
                    
                    if song_title and end_time_str:
                        end_time = datetime.fromisoformat(end_time_str)
                        now = datetime.now()
                        
                        remaining = end_time - now
                        remaining_seconds = int(remaining.total_seconds())
                        
                        if remaining_seconds > 0:
                            remaining_minutes = remaining_seconds // 60
                            remaining_secs = remaining_seconds % 60
                            
                            next_song = "Default Song"
                            if Path(self.queue_file).exists():
                                with open(self.queue_file, 'r', encoding='utf-8') as f:
                                    lines = [line.strip() for line in f.readlines() if line.strip()]
                                    if lines:
                                        if '|||' in lines[0]:
                                            parts = lines[0].split('|||')
                                            if len(parts) >= 3:
                                                username = parts[0]
                                                song = parts[2]
                                                next_song = f"{song} - by @{username}"
                                            elif len(parts) == 2:
                                                username = parts[0]
                                                song = parts[1]
                                                next_song = f"{song} - by @{username}"
                                        else:
                                            next_song = lines[0]
                            
                            msg, color = BotResponses.TIME_REMAINING
                            await self.highrise.chat(self.colorize(msg.format(minutes=remaining_minutes, seconds=remaining_secs, next_song=next_song), color))
                            logger.info(f"📢 Status announcement: {remaining_minutes}:{remaining_secs:02d} remaining")
                        
            except Exception as e:
                if "closing transport" in str(e).lower() or "connection" in str(e).lower():
                    logger.warning("⚠️ Status announcement stopped - Connection closed")
                    self.is_connected = False
                    break
                logger.error(f"❌ Error in announcement: {e}")
    
    async def continuous_dance_loop(self):
        """Continuous dance loop for the bot"""
        try:
            with open(self.bot_dances_file, 'r', encoding='utf-8') as f:
                dances_data = json.load(f)
            
            if not dances_data:
                logger.warning("⚠️ No dances saved for continuous dancing")
                if self.is_connected:
                    msg, color = BotResponses.NO_DANCES_SAVED
                    await self.highrise.chat(self.colorize(msg, color))
                self.is_dancing = False
                return
            
            dance_list = list(dances_data.items())
            dance_index = 0
            
            logger.info(f"💃 Starting continuous dance with {len(dance_list)} dances")
            
            while self.is_dancing and self.is_connected:
                dance_id, dance_info = dance_list[dance_index]
                duration = dance_info['duration']
                
                await self.highrise.send_emote(dance_id)
                logger.info(f"💃 Dance: {dance_id} ({duration}s)")
                
                await asyncio.sleep(duration)
                
                dance_index = (dance_index + 1) % len(dance_list)
            
        except Exception as e:
            if "closing transport" in str(e).lower() or "connection" in str(e).lower():
                logger.warning("⚠️ Dance stopped - Connection closed")
                self.is_connected = False
            else:
                logger.error(f"❌ Error in continuous dance: {e}")
            self.is_dancing = False
    
    async def start_continuous_dancing(self):
        """Start continuous dancing"""
        if self.is_dancing:
            msg, color = BotResponses.DANCE_ALREADY_RUNNING
            await self.highrise.chat(self.colorize(msg, color))
            return
        
        self.is_dancing = True
        self.dance_task = asyncio.create_task(self.continuous_dance_loop())
        logger.info("✅ Continuous dance started")
    
    async def stop_continuous_dancing(self):
        """Stop continuous dancing"""
        if not self.is_dancing:
            msg, color = BotResponses.DANCE_ALREADY_STOPPED
            await self.highrise.chat(self.colorize(msg, color))
            return
        
        self.is_dancing = False
        
        if self.dance_task:
            self.dance_task.cancel()
        
        msg, color = BotResponses.DANCE_STOPPED
        await self.highrise.chat(self.colorize(msg, color))
        logger.info("⏹️ Continuous dance stopped")
    
    async def show_user_tickets(self, user: User):
        """Show user's ticket count"""
        try:
            tickets = self.tickets_system.get_user_tickets(user.username)
            msg, color = BotResponses.TICKETS_INFO
            await self.highrise.chat(self.colorize(msg.format(count=tickets), color))
        except Exception as e:
            logger.error(f"Error showing tickets: {e}")
    
    async def show_all_tickets(self):
        """Show list of users with tickets"""
        try:
            all_tickets = self.tickets_system.get_all_users_with_tickets()
            
            if not all_tickets:
                msg, color = BotResponses.NO_USERS_WITH_TICKETS
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            msg, color = BotResponses.TICKETS_LIST
            await self.highrise.chat(self.colorize(msg, color))
            
            # Sort by ticket count (highest to lowest)
            sorted_users = sorted(all_tickets.items(), key=lambda x: x[1], reverse=True)
            
            for username, tickets in sorted_users[:10]:  # Top 10 users
                msg, color = BotResponses.USER_TICKET_ITEM
                await self.highrise.chat(self.colorize(msg.format(username=username, tickets=tickets), color))
                
        except Exception as e:
            logger.error(f"Error showing ticket list: {e}")
    
    # ==================== Tickets Management Commands ====================
    async def add_tickets_command(self, user: User, args: str):
        """Add tickets to a user"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            parts = args.split()
            if len(parts) < 2:
                msg, color = BotResponses.ADDTICKETS_NO_ARGS
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            target_username = parts[0].lstrip('@')  # Remove @ if present
            tickets_to_add = int(parts[1])
            
            total = self.tickets_system.add_tickets(target_username, tickets_to_add)
            msg, color = BotResponses.ADDTICKETS_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(tickets=tickets_to_add, username=target_username, total=total), color))
        except Exception as e:
            logger.error(f"Error adding tickets: {e}")
    
    async def withdraw_tickets_command(self, user: User, args: str):
        """Withdraw tickets from a user (specific amount or all)"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            if not args.strip():
                msg, color = BotResponses.WITHDRAW_NO_ARGS
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            parts = args.split()
            target_username = parts[0].lstrip('@')  # Remove @ if present
            current_tickets = self.tickets_system.get_user_tickets(target_username)
            
            if current_tickets <= 0:
                msg, color = BotResponses.WITHDRAW_NO_TICKETS
                await self.highrise.chat(self.colorize(msg.format(username=target_username), color))
                return
            
            # If specific amount is provided
            if len(parts) >= 2:
                tickets_to_withdraw = int(parts[1])
                tickets_to_withdraw = min(tickets_to_withdraw, current_tickets)  # Do not withdraw more than available
                new_total = current_tickets - tickets_to_withdraw
                self.tickets_system.set_user_tickets(target_username, new_total)
                msg, color = BotResponses.WITHDRAW_AMOUNT_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(username=target_username, tickets=tickets_to_withdraw, remaining=new_total), color))
            else:
                # Withdraw all
                self.tickets_system.set_user_tickets(target_username, 0)
                msg, color = BotResponses.WITHDRAW_SUCCESS
                await self.highrise.chat(self.colorize(msg.format(username=target_username, tickets=current_tickets), color))
        except Exception as e:
            logger.error(f"Error withdrawing tickets: {e}")
    
    async def withdraw_all_tickets_command(self, user: User):
        """Withdraw all tickets from all users"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            all_tickets = self.tickets_system.get_all_users_with_tickets()
            
            if not all_tickets:
                msg, color = BotResponses.WITHDRAWALL_NO_USERS
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            total_withdrawn = sum(all_tickets.values())
            count = len(all_tickets)
            
            # Clear all tickets
            self.tickets_system.tickets_data = {}
            self.tickets_system.save_tickets()
            
            msg, color = BotResponses.WITHDRAWALL_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(count=count, total=total_withdrawn), color))
        except Exception as e:
            logger.error(f"Error withdrawing all tickets: {e}")
    
    async def give_all_tickets_command(self, user: User, args: str):
        """Give tickets to everyone"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            if not args.strip():
                msg, color = BotResponses.ALLTK_NO_AMOUNT
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            tickets_to_give = int(args.strip())
            
            # Give to everyone in room
            room_users = (await self.highrise.get_room_users()).content
            count = 0
            
            for room_user, _ in room_users:
                if room_user.username != self.highrise.my_user.username:
                    self.tickets_system.add_tickets(room_user.username, tickets_to_give)
                    count += 1
            
            msg, color = BotResponses.ALLTK_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(tickets=tickets_to_give, count=count), color))
        except Exception as e:
            logger.error(f"Error giving tickets: {e}")
    
    async def free_vip_command(self, user: User, args: str):
        """Add free VIP to user"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            if not args.strip():
                msg, color = BotResponses.FREE_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            target_username = args.strip().lstrip('@')  # Remove @ if present
            
            if self.tickets_system.is_vip(target_username):
                msg, color = BotResponses.FREE_ALREADY
                await self.highrise.chat(self.colorize(msg.format(username=target_username), color))
                return
            
            self.tickets_system.add_vip(target_username)
            msg, color = BotResponses.FREE_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(username=target_username), color))
        except Exception as e:
            logger.error(f"Error adding VIP: {e}")
    
    async def unfree_vip_command(self, user: User, args: str):
        """Remove VIP from user"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            if not args.strip():
                msg, color = BotResponses.UNFREE_NO_USERNAME
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            target_username = args.strip().lstrip('@')  # Remove @ if present
            
            if not self.tickets_system.is_vip(target_username):
                msg, color = BotResponses.UNFREE_NOT_VIP
                await self.highrise.chat(self.colorize(msg.format(username=target_username), color))
                return
            
            self.tickets_system.remove_vip(target_username)
            msg, color = BotResponses.UNFREE_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(username=target_username), color))
        except Exception as e:
            logger.error(f"Error removing VIP: {e}")
    
    # ==================== Wallet Commands ====================
    async def check_balance_command(self, user: User):
        """Check wallet balance"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            # Get wallet balance from Highrise API
            wallet = await self.highrise.get_wallet()
            balance = wallet.content[0].amount if wallet.content else 0
            
            msg, color = BotResponses.BALANCE_INFO
            await self.highrise.chat(self.colorize(msg.format(balance=balance), color))
        except Exception as e:
            logger.error(f"Error checking balance: {e}")
    
    async def sync_wallet_command(self, user: User):
        """Sync wallet"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            wallet = await self.highrise.get_wallet()
            balance = wallet.content[0].amount if wallet.content else 0
            
            msg, color = BotResponses.SYNC_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(balance=balance), color))
        except Exception as e:
            logger.error(f"Error syncing wallet: {e}")
            msg, color = BotResponses.SYNC_ERROR
            await self.highrise.chat(self.colorize(msg, color))
    
    
    async def cbit_command(self, user: User):
        """Show stream bitrate"""
        try:
            from config import StreamSettings
            await self.highrise.chat(self.colorize(f"📊 Bitrate: {StreamSettings.STREAM_BITRATE}", "info"))
        except Exception as e:
            logger.error(f"Error in /cbit: {e}")
    
    async def set_command(self, user: User, args: str):
        """Move bot to user's location (Owner only)"""
        if not await self.is_main_owner(user):
             msg, color = BotResponses.ADMIN_ONLY
             await self.highrise.chat(self.colorize(msg, color))
             return
        await self.move_bot_command(user)

    async def setbot_command(self, user: User, args: str = ""):
        """Configure bot settings or move bot"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.ADMIN_ONLY
            await self.highrise.chat(self.colorize(msg, color))
            return
        
        # If 'move' or 'here' is passed, or no args (legacy behavior preserved but with info)
        if args.strip().lower() in ["move", "here"]:
            await self.move_bot_command(user)
            return

        # Show settings
        price = self.tickets_system.get_ticket_price()
        autotip = self.tickets_system.get_autotip_amount()
        
        msg = (
            f"⚙️ Bot Settings:\n"
            f"🎫 Ticket Price: {price}g (Change: -pslot amount)\n"
            f"💰 Auto-Tip: {autotip}g (Change: -autotip amount)\n"
            f"📍 Position: Saved\n"
            f"ℹ️ Use '-setbot move' to teleport bot here."
        )
        await self.highrise.chat(self.colorize(msg, "info"))

    async def pslot_command(self, user: User, args: str):
        """Set ticket price manually (Owner only)"""
        if not await self.is_main_owner(user):
             msg, color = BotResponses.ADMIN_ONLY
             await self.highrise.chat(self.colorize(msg, color))
             return
        
        try:
            parts = args.strip().split()
            if not parts:
                await self.highrise.chat(self.colorize("Usage: -pslot <amount>", "warning"))
                return
            
            price = int(parts[0])
            if price < 1:
                await self.highrise.chat(self.colorize("Price must be at least 1 gold", "warning"))
                return
                
            self.tickets_system.set_ticket_price(price)
            await self.highrise.chat(self.colorize(f"✅ Ticket price set to {price} gold per ticket", "success"))
        except ValueError:
            await self.highrise.chat(self.colorize("Invalid amount. Please provide a number.", "error"))
        except Exception as e:
            logger.error(f"Error setting ticket price: {e}")
            await self.highrise.chat(self.colorize("An error occurred while setting ticket price.", "error"))

    async def mod_command(self, user: User, args: str):
        """Add moderator (Owner only)"""
        if not await self.is_main_owner(user):
             msg, color = BotResponses.ADMIN_ONLY
             await self.highrise.chat(self.colorize(msg, color))
             return
             
        username = args.strip().lstrip('@')
        if not username:
            await self.highrise.chat(self.colorize("Usage: -addmod @user", "warning"))
            return
            
        if self.tickets_system.is_moderator_user(username):
            await self.highrise.chat(self.colorize(f"{username} is already a moderator", "warning"))
            return
            
        if self.tickets_system.add_moderator(username):
            await self.highrise.chat(self.colorize(f"✅ {username} is now a moderator", "success"))
        else:
            await self.highrise.chat(self.colorize("Failed to add moderator", "error"))

    async def demod_command(self, user: User, args: str):
        """Remove moderator (Owner only)"""
        if not await self.is_main_owner(user):
             msg, color = BotResponses.ADMIN_ONLY
             await self.highrise.chat(self.colorize(msg, color))
             return
             
        username = args.strip().lstrip('@')
        if not username:
            await self.highrise.chat(self.colorize("Usage: -demod @user", "warning"))
            return
            
        if not self.tickets_system.is_moderator_user(username):
            await self.highrise.chat(self.colorize(f"{username} is not a moderator", "warning"))
            return
            
        if self.tickets_system.remove_moderator(username):
            await self.highrise.chat(self.colorize(f"✅ {username} removed from moderators", "success"))
        else:
            await self.highrise.chat(self.colorize("Failed to remove moderator", "error"))

    async def move_bot_command(self, user: User):
        """Move bot to user's location"""
        try:
            room_users_response = await self.highrise.get_room_users()
            pos = None
            for u, p in room_users_response.content:
                if u.id == user.id:
                    pos = p
                    break
            if not pos:
                await self.highrise.chat(self.colorize("❌ Cannot find your location.", "error"))
                return
            save_bot_position({"x": pos.x, "y": pos.y, "z": pos.z, "facing": pos.facing})
            target_pos = Position(x=pos.x, y=pos.y, z=pos.z, facing=pos.facing)
            slight_pos = Position(x=pos.x, y=pos.y + 0.0000001, z=pos.z, facing=pos.facing)
            try:
                if hasattr(self.highrise, "teleport"):
                    await self.highrise.teleport(slight_pos)
                    await self.highrise.teleport(target_pos)
                elif hasattr(self.highrise, "set_bot_position"):
                    await self.highrise.set_bot_position(slight_pos)
                    await self.highrise.set_bot_position(target_pos)
                elif hasattr(self.highrise, "set_position"):
                    await self.highrise.set_position(slight_pos)
                    await self.highrise.set_position(target_pos)
                else:
                    await self.highrise.walk_to(target_pos)
            except Exception:
                try:
                    await self.highrise.teleport(target_pos)
                except Exception:
                    await self.highrise.walk_to(target_pos)
            await self.highrise.chat(self.colorize("✅ Bot moved to your location.", "success"))
        except Exception as e:
            logger.error(f"Error in /setbot: {e}")
            await self.highrise.chat(self.colorize("❌ Failed to move bot.", "error"))
    async def give_gold_command(self, user: User, args: str):
        """Send gold to user"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            parts = args.split()
            if len(parts) < 2:
                msg, color = BotResponses.GIVE_NO_ARGS
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            target_username = parts[0].lstrip('@')  # Remove @ if present
            amount = int(parts[1])
            
            # Send gold (This is an advanced feature that may require special permissions)
            msg, color = BotResponses.GIVE_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(amount=amount, username=target_username), color))
        except Exception as e:
            logger.error(f"Error sending gold: {e}")
    
    async def cash_command(self, user: User, args: str):
        """Send gold to @3OUF via tip_user"""
        try:
            if not await self.is_management_allowed(user):
                msg, color = BotResponses.ADMIN_ONLY
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            raw = args.strip().lower()
            if not raw:
                msg, color = BotResponses.GIVE_NO_ARGS
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            def parse_amount(s: str) -> int:
                s = s.strip().lower().replace('g','')
                if s.endswith('k'):
                    base = s[:-1]
                    return int(base) * 1000
                return int(s)
            
            try:
                amount = parse_amount(raw)
            except:
                await self.highrise.chat(self.colorize("❌ Amount invalid", "error"))
                return
            
            bot_wallet = await self.highrise.get_wallet()
            bot_amount = bot_wallet.content[0].amount if bot_wallet and bot_wallet.content else 0
            if bot_amount <= 0 or bot_amount < amount:
                await self.highrise.chat(self.colorize("❌ Not enough funds", "error"))
                return
            
            bars_dictionary = {
                10000: "gold_bar_10k",
                5000: "gold_bar_5000",
                1000: "gold_bar_1k",
                500: "gold_bar_500",
                100: "gold_bar_100",
                50: "gold_bar_50",
                10: "gold_bar_10",
                5: "gold_bar_5",
                1: "gold_bar_1"
            }
            fees_dictionary = {
                10000: 1000,
                5000: 500,
                1000: 100,
                500: 50,
                100: 10,
                50: 5,
                10: 1,
                5: 1,
                1: 1
            }
            tip = []
            total = 0
            remaining = amount
            for bar in sorted(bars_dictionary.keys(), reverse=True):
                if remaining >= bar:
                    bar_amount = remaining // bar
                    remaining = remaining % bar
                    for _ in range(bar_amount):
                        tip.append(bars_dictionary[bar])
                        total += bar + fees_dictionary[bar]
            if total > bot_amount:
                await self.highrise.chat(self.colorize("❌ Not enough funds", "error"))
                return
            tip_string = ",".join(tip)
            
            # Find user 3OUF in the room
            target_id = None
            try:
                room_users_response = await self.highrise.get_room_users()
                for u, pos in room_users_response.content:
                    if u.username.lower() == "3ouf":
                        target_id = u.id
                        break
            except Exception as e:
                logger.error(f"Error fetching users: {e}")
            
            if not target_id:
                await self.highrise.chat(self.colorize("❌ User @3OUF not in room", "error"))
                return
            
            result = await self.highrise.tip_user(target_id, tip_string)
            if result == "success":
                await self.highrise.chat(self.colorize(f"✅ Sent {amount}g to @3OUF", "success"))
            else:
                await self.highrise.chat(self.colorize("❌ Send failed", "error"))
        except Exception as e:
            logger.error(f"Error in /cash: {e}")
    
    # ==================== System Management Commands ====================

    
    async def clean_cache_command(self, user: User):
        """Clean old songs from cache"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            from config import StreamSettings
            from streamer import is_default_song_file
            
            cache_dir = Path(StreamSettings.CACHE_DIR)
            if not cache_dir.exists():
                await self.highrise.chat(self.colorize("📁 No saved songs", "yellow"))
                return
            
            all_files = list(cache_dir.glob("*.mp3")) + list(cache_dir.glob("*.mp4")) + list(cache_dir.glob("*.webm"))
            
            if not all_files:
                await self.highrise.chat(self.colorize("🧹 No files to clean", "yellow"))
                return
            
            deleted_count = 0
            freed_space_mb = 0
            
            for file_path in all_files:
                if not is_default_song_file(str(file_path)):
                    try:
                        file_size = file_path.stat().st_size / (1024 * 1024)
                        file_path.unlink()
                        deleted_count += 1
                        freed_space_mb += file_size
                    except Exception as e:
                        logger.error(f"❌ Failed to delete {file_path.name}: {e}")
            
            if deleted_count > 0:
                await self.highrise.chat(self.colorize(f"✅ Cleared {deleted_count} old songs, freed {freed_space_mb:.1f} MB", "green"))
            else:
                await self.highrise.chat(self.colorize("📝 All songs are default, nothing to clear", "yellow"))
        
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")
            await self.highrise.chat(self.colorize(f"❌ Error: {e}", "red"))
    
    async def cache_info_command(self, user: User):
        """Show cache info"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            from config import StreamSettings
            from streamer import is_default_song_file
            
            cache_dir = Path(StreamSettings.CACHE_DIR)
            if not cache_dir.exists():
                await self.highrise.chat(self.colorize("📁 No saved songs", "yellow"))
                return
            
            all_files = list(cache_dir.glob("*.mp3")) + list(cache_dir.glob("*.mp4")) + list(cache_dir.glob("*.webm"))
            
            if not all_files:
                await self.highrise.chat(self.colorize("🧹 No files", "yellow"))
                return
            
            total_size = sum(f.stat().st_size for f in all_files)
            total_size_mb = total_size / (1024 * 1024)
            total_files = len(all_files)
            
            default_count = 0
            user_count = 0
            
            for file_path in all_files:
                if is_default_song_file(str(file_path)):
                    default_count += 1
                else:
                    user_count += 1
            
            info_msg = f"""📊 Cache Information:
📦 Total: {total_files} songs ({total_size_mb:.1f} MB)
🎵 Default: {default_count} songs
👥 Added: {user_count} songs
⚙️ Limit: {StreamSettings.MAX_CACHED_SONGS} songs / {StreamSettings.MAX_CACHE_SIZE_MB} MB"""
            
            await self.highrise.chat(self.colorize(info_msg, "cyan"))
        
        except Exception as e:
            logger.error(f"Error showing cache info: {e}")
            await self.highrise.chat(self.colorize(f"❌ Error: {e}", "red"))
    
    async def max_queue_command(self, user: User, args: str):
        """Set queue limit"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            if not args.strip():
                msg, color = BotResponses.MAXQUEUE_NO_NUMBER
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            max_queue = int(args.strip())
            # Save to config file or variable
            
            msg, color = BotResponses.MAXQUEUE_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(max=max_queue), color))
        except Exception as e:
            logger.error(f"Error setting queue limit: {e}")
    
    async def max_requests_command(self, user: User, args: str):
        """Set user request limit"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            if not args.strip():
                msg, color = BotResponses.MAXREQUESTS_NO_NUMBER
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            max_requests = int(args.strip())
            
            msg, color = BotResponses.MAXREQUESTS_SUCCESS
            await self.highrise.chat(self.colorize(msg.format(max=max_requests), color))
        except Exception as e:
            logger.error(f"Error setting request limit: {e}")
    
    async def dev_info_command(self, user: User):
        """Developer mode info"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            import sys
            import platform
            
            status = "Enabled" if getattr(self, 'dev_mode', False) else "Disabled"
            stats = f"Python {sys.version.split()[0]}, {platform.system()}"
            
            msg, color = BotResponses.DEV_MODE_INFO
            await self.highrise.chat(self.colorize(msg.format(status=status, stats=stats), color))
        except Exception as e:
            logger.error(f"Error getting dev info: {e}")
    
    async def dev_on_command(self, user: User):
        """Enable developer mode"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        self.dev_mode = True
        msg, color = BotResponses.DEV_ON
        await self.highrise.chat(self.colorize(msg, color))
    
    async def dev_off_command(self, user: User):
        """Disable developer mode"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        self.dev_mode = False
        msg, color = BotResponses.DEV_OFF
        await self.highrise.chat(self.colorize(msg, color))
    
    async def reset_command(self, user: User, message: str):
        """Reset all data"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            if message != "confirm reset":
                msg, color = BotResponses.RESET_CONFIRM_REQUIRED
                await self.highrise.chat(self.colorize(msg, color))
                return
            
            # Delete all files
            files_to_reset = [
                self.queue_file,
                self.tickets_system.tickets_file,
                self.tickets_system.vip_file,
                SystemFiles.PLAYLIST_STATE,
                SystemFiles.SONG_NOTIFICATIONS,
                "play_history.txt"
            ]
            
            for file in files_to_reset:
                if Path(file).exists():
                    Path(file).unlink()
            
            # Recreate empty files
            self.tickets_system.tickets_data = {}
            self.tickets_system.save_tickets()
            self.tickets_system.vip_users = []
            self.tickets_system.save_vip_users()
            
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                f.write("")
            
            msg, color = BotResponses.RESET_SUCCESS
            await self.highrise.chat(self.colorize(msg, color))
            
            # Wait a bit then restart
            await asyncio.sleep(2)
            logger.info("🔄 Restarting bot...")
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            logger.error(f"Error resetting: {e}")
    
    async def equip_outfit_command(self, user: User, outfit_id: str):
        """Change bot outfit (Owner only) - Can copy user outfit by name"""
        if not await self.is_main_owner(user):
            await self.send_whisper_safe(user, f"❌ This command is for owner only ({HighriseSettings.OWNER_USERNAME})")
            return
        
        try:
            if not outfit_id.strip():
                await self.send_whisper_safe(user, "⚠️ Usage: !equip @user")
                return
            
            target_username = outfit_id.strip().lstrip('@')
            
            # Try 1: Search in room first (faster) then get_user_outfit
            try:
                room_users = (await self.highrise.get_room_users()).content
                for room_user, _ in room_users:
                    if room_user.username.lower() == target_username.lower():
                        outfit_response = await self.highrise.get_user_outfit(room_user.id)
                        
                        if isinstance(outfit_response, list):
                            outfit = outfit_response
                        elif hasattr(outfit_response, 'outfit'):
                            outfit = outfit_response.outfit
                        else:
                            outfit = None
                        
                        if outfit and len(outfit) > 0:
                            outfit = self._normalize_outfit(outfit)
                            ok = await self._apply_outfit_and_verify(outfit)
                            if not ok:
                                filtered = await self._filter_outfit_by_inventory(outfit)
                                ok = await self._apply_outfit_and_verify(filtered)
                            if ok:
                                await self.send_whisper_safe(user, "✅ Saved successfully")
                                return
            except Exception as room_error:
                logger.debug(f"Room search failed: {room_error}")
            
            # Try 2: Resolve user_id via Web API then get_user_outfit
            try:
                uid = await self._resolve_user_id(target_username)
                if uid:
                    outfit_response = await self.highrise.get_user_outfit(uid)
                    if isinstance(outfit_response, list):
                        outfit = outfit_response
                    elif hasattr(outfit_response, 'outfit'):
                        outfit = outfit_response.outfit
                    else:
                        outfit = None
                    if outfit and len(outfit) > 0:
                        outfit = self._normalize_outfit(outfit)
                        ok = await self._apply_outfit_and_verify(outfit)
                        if not ok:
                            filtered = await self._filter_outfit_by_inventory(outfit)
                            ok = await self._apply_outfit_and_verify(filtered)
                        if ok:
                            await self.send_whisper_safe(user, "✅ Saved successfully")
                            return
            except Exception as e_id:
                logger.debug(f"get_user_outfit via Web API failed: {e_id}")
            
            # Last try: Use direct link as requested
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    outfit = None
                    # Priority to users/{username} first
                    url0 = f"https://webapi.highrise.game/users/{target_username}"
                    try:
                        async with session.get(url0, timeout=15) as resp0:
                            data0 = await resp0.json(content_type=None)
                        if isinstance(data0, dict):
                            cand = data0.get("user") or data0
                            outfit = cand.get("outfit")
                    except Exception:
                        pass
                    url1 = f"https://webapi.highrise.game/users/user?username={target_username}"
                    try:
                        async with session.get(url1, timeout=15) as resp1:
                            data1 = await resp1.json(content_type=None)
                        if isinstance(data1, dict):
                            if "outfit" in data1 and data1["outfit"]:
                                outfit = data1["outfit"]
                            elif "user" in data1 and isinstance(data1["user"], dict):
                                outfit = data1["user"].get("outfit")
                    except Exception:
                        pass
                    if not outfit:
                        url2 = f"https://webapi.highrise.game/users?username={target_username}"
                        try:
                            async with session.get(url2, timeout=15) as resp2:
                                data2 = await resp2.json(content_type=None)
                            if isinstance(data2, dict) and isinstance(data2.get("users"), list):
                                for u in data2["users"]:
                                    if isinstance(u, dict):
                                        un = (u.get("username") or u.get("name") or "").lower()
                                        if un == target_username.lower():
                                            outfit = u.get("outfit") or (u.get("user") or {}).get("outfit")
                                            if outfit:
                                                break
                        except Exception:
                            pass
                    if outfit:
                        outfit = self._normalize_outfit(outfit)
                        ok = await self._apply_outfit_and_verify(outfit)
                        if not ok:
                            filtered = await self._filter_outfit_by_inventory(outfit)
                            ok = await self._apply_outfit_and_verify(filtered)
                        if ok:
                            await self.send_whisper_safe(user, "✅ Saved successfully")
                            return
            except Exception as e2:
                logger.error(f"❌ Error in attempt : {e2}")
            
            await self.send_whisper_safe(user, f"❌ Outfit not found for @{target_username}")
        except Exception as e:
            logger.error(f"❌ Error copying outfit: {e}")
            await self.send_whisper_safe(user, "❌ Failed to copy outfit")
    
    async def equip_outfit_by_id_command(self, user: User, outfit_id: str):
        """Change bot outfit using outfit ID (Owner only)"""
        if not await self.is_main_owner(user):
            msg, color = BotResponses.OWNER_ONLY_COMMAND
            await self.highrise.chat(self.colorize(msg.format(username=user.username, owner=HighriseSettings.OWNER_USERNAME), color))
            return
        
        try:
            if not outfit_id.strip():
                await self.highrise.chat(self.colorize("⚠️ Usage: !equipid <outfit_id>", "warning"))
                await self.highrise.chat(self.colorize("💡 Example: !equipid 64f8a2b1c9d3e4f5a6b7c8d9", "info"))
                return
            
            target_outfit_id = outfit_id.strip()
            
            await self.highrise.chat(self.colorize(f"🔍 Searching for outfit {target_outfit_id}...", "info"))
            
            try:
                # Fetch outfit from Web API using ID
                outfit = await self.webapi.get_outfit(target_outfit_id)
                
                if outfit:
                    await self.highrise.chat(self.colorize("🔄 Copying outfit...", "info"))
                    await self.highrise.set_outfit(outfit)
                    await self.highrise.chat(self.colorize(f"✅ Outfit copied successfully!", "success"))
                    logger.info(f"👗 Copied outfit using ID: {target_outfit_id}")
                else:
                    await self.highrise.chat(self.colorize(f"❌ Outfit not found", "error"))
                    
            except Exception as outfit_error:
                error_msg = str(outfit_error)
                if "404" in error_msg:
                    await self.highrise.chat(self.colorize(f"❌ Outfit not found or wrong ID", "error"))
                else:
                    logger.error(f"Error fetching outfit: {outfit_error}")
                    await self.highrise.chat(self.colorize(f"❌ Failed to fetch outfit", "error"))
            
        except Exception as e:
            logger.error(f"❌ Error copying outfit by ID: {e}")
            await self.highrise.chat(self.colorize(f"❌ Failed to copy outfit: {str(e)}", "error"))
    
    # ==================== Commands List ====================
    async def show_commands_list(self, user: User):
        """Show all commands directly"""
        # Show User Commands
        await self.send_whisper_safe(user, BotResponses.HELP_USER_PAGE1)
        await self.send_whisper_safe(user, BotResponses.HELP_USER_PAGE2)

        # If admin/owner, show manager commands too
        if await self.is_management_allowed(user):
            await self.send_whisper_long(user, BotResponses.HELP_MANAGER_USERS)
            await self.send_whisper_long(user, BotResponses.HELP_MANAGER_MONEY1)
            await self.send_whisper_long(user, BotResponses.HELP_MANAGER_MONEY2)
            await self.send_whisper_long(user, BotResponses.HELP_MANAGER_SETTINGS)
            if hasattr(BotResponses, "INFO_SECTION"):
                await self.send_whisper_long(user, BotResponses.INFO_SECTION)

    # ==================== New Feature Commands ====================
    async def show_mod_list_command(self, user: User):
        """Show list of moderators"""
        if not await self.is_management_allowed(user):
            await self.send_whisper_safe(user, "❌ Admin only")
            return
        
        try:
            mods = self.tickets_system.moderators
            if not mods:
                await self.highrise.chat(self.colorize("📋 No moderators found", "info"))
                return
            
            msg = f"👮 Moderators: {', '.join(mods)}"
            await self.send_chat_long(msg, "info")
        except Exception as e:
            logger.error(f"Error showing mod list: {e}")

    async def show_vip_list_command(self, user: User):
        """Show list of VIP users"""
        if not await self.is_management_allowed(user):
            await self.send_whisper_safe(user, "❌ Admin only")
            return
        
        try:
            vips = list(self.tickets_system.vip_users.keys())
            if not vips:
                await self.highrise.chat(self.colorize("⭐ No VIP users found", "info"))
                return
            
            msg = f"⭐ VIP Users: {', '.join(vips)}"
            await self.send_chat_long(msg, "info")
        except Exception as e:
            logger.error(f"Error showing VIP list: {e}")

    async def dance_command(self, user: User):
        """Toggle dance loop"""
        await self.start_continuous_dancing()
        
    async def block_user_command(self, user: User, args: str):
        """Block a user from using the bot"""
        if not await self.is_management_allowed(user):
            await self.highrise.chat(self.colorize("❌ Admin only", "error"))
            return
        if not args:
            return
        username = args.split()[0].replace("@", "")
        if self.tickets_system.block_user(username):
            await self.highrise.chat(self.colorize(f"🚫 {username} has been blocked.", "success"))
        else:
            await self.highrise.chat(self.colorize(f"⚠️ {username} is already blocked.", "warning"))

    async def unblock_user_command(self, user: User, args: str):
        """Unblock a user"""
        if not await self.is_management_allowed(user):
            await self.highrise.chat(self.colorize("❌ Admin only", "error"))
            return
        if not args:
            return
        username = args.split()[0].replace("@", "")
        if self.tickets_system.unblock_user(username):
            await self.highrise.chat(self.colorize(f"✅ {username} has been unblocked.", "success"))
        else:
            await self.highrise.chat(self.colorize(f"⚠️ {username} is not blocked.", "warning"))

    async def show_blocked_command(self, user: User):
        """Show blocked users"""
        if not await self.is_management_allowed(user):
            return
        users = self.tickets_system.blocked_users
        if not users:
            await self.highrise.chat(self.colorize("✅ No blocked users.", "info"))
        else:
            await self.send_chat_long(f"🚫 Blocked: {', '.join(users)}", "info")

    async def bot_wallet_command(self, user: User):
        """Check bot wallet balance (Admin Only, DM response)"""
        if not await self.is_management_allowed(user):
            return
        try:
            wallet = await self.highrise.get_wallet()
            amount = wallet.content[0].amount if wallet.content else 0
            await self.send_whisper_safe(user, f"💰 Bot Wallet: {amount} Gold")
        except Exception as e:
            logger.error(f"Error checking wallet: {e}")

    async def autotip_command(self, user: User, args: str):
        """Set auto tip amount"""
        if not await self.is_main_owner(user):
             await self.highrise.chat(self.colorize("❌ Owner only", "error"))
             return
        try:
            amount = int(args.strip())
            self.tickets_system.set_autotip_amount(amount)
            if amount > 0:
                await self.highrise.chat(self.colorize(f"✅ Auto-tip enabled: {amount} Gold per user", "success"))
            else:
                await self.highrise.chat(self.colorize(f"✅ Auto-tip disabled", "success"))
        except:
             await self.highrise.chat(self.colorize("❌ Usage: -Autotip <amount>", "error"))

    async def give_command_dispatcher(self, user: User, args: str):
        """Dispatch give command based on user role"""
        parts = args.split()
        if len(parts) < 2:
            return

        is_owner = await self.is_main_owner(user)
        
        target = None
        amount = 0
        
        for p in parts:
            if p.startswith("@"):
                target = p.replace("@", "")
            elif p.isdigit():
                amount = int(p)
        
        if not target or amount <= 0:
             await self.highrise.chat(self.colorize("❌ Invalid args.", "error"))
             return

        if is_owner:
            await self.add_tickets_command(user, f"{target} {amount}")
        else:
            await self.transfer_tickets_command(user, target, amount)

    async def transfer_tickets_command(self, user: User, target: str, amount: int):
        """User transfers tickets to another"""
        if self.tickets_system.get_user_tickets(user.username) >= amount:
            if self.tickets_system.use_ticket(user.username, amount):
                self.tickets_system.add_tickets(target, amount)
                await self.highrise.chat(self.colorize(f"✅ {user.username} gave {amount} tickets to {target}!", "success"))
            else:
                 await self.highrise.chat(self.colorize("❌ Error processing transfer.", "error"))
        else:
            await self.highrise.chat(self.colorize("❌ Not enough tickets.", "error"))

    async def gift_song_command(self, user: User, args: str):
        """Gift a song (50 Gold)"""
        if not args:
            await self.highrise.chat(self.colorize("❌ Usage: -gift <song name> @user", "error"))
            return
            
        parts = args.split()
        target_user = None
        song_name = ""
        
        target_found = False
        song_parts = []
        
        for p in parts:
            if p.startswith("@") and not target_found:
                target_user = p.replace("@", "")
                target_found = True
            else:
                song_parts.append(p)
        
        song_name = " ".join(song_parts)
        
        if not target_user or not song_name:
            await self.highrise.chat(self.colorize("❌ Usage: -gift <song name> @user", "error"))
            return
            
        is_owner = await self.is_main_owner(user)
        cost_gold = 50
        
        if is_owner:
            cost_gold = 0
        elif self.tickets_system.check_vip_daily_limit(user.username, "gifts"):
             cost_gold = 0
             self.tickets_system.increment_vip_usage(user.username, "gifts")
             vip_data = self.tickets_system.get_vip_data(user.username)
             used = vip_data.get("daily_gifts", 0)
             await self.send_whisper_safe(user, f"🎁 Used free gift {used}/5")
        
        if cost_gold > 0:
            if not self.tickets_system.use_ticket(user.username, cost_gold):
                await self.highrise.chat(self.colorize(f"❌ You need {cost_gold} Gold to gift.", "error"))
                return
        
        try:
            entry = f"{target_user}|||{song_name}|||{song_name}"
            lines = []
            if Path(self.queue_file).exists():
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
            
            lines.insert(0, entry)
            
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
                
            await self.highrise.chat(self.colorize(f"🎁 @{user.username} gifted '{song_name}' to @{target_user}!", "success"))
        except Exception as e:
            logger.error(f"Error in gift: {e}")
            await self.highrise.chat(self.colorize("❌ Error gifting song", "error"))





