# Highrise Music Bot with Live Streaming

## Overview

A sophisticated music bot for the Highrise virtual world platform that integrates with Zeno.fm radio streaming. The bot allows users to request songs through chat commands, which are then played on a live radio station. Users interact with the bot in Arabic, request songs from YouTube, and listen to them via an external Zeno.fm stream.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### December 3, 2025 - Connection State Management & Hosting Fixes
- **Connection State Management System**: Comprehensive fix for "Cannot write to closing transport" errors
  - Added `is_connected` flag to track bot connection state
  - All background tasks now check connection state before executing operations
  - Tasks gracefully stop when connection is lost (no more transport errors)
  - Detection of "closing transport" errors automatically sets connection flag
  - Modified tasks: vip_reminder_task, audio_help_reminder_task, periodic_staff_check, monitor_current_song, announce_song_status, continuous_dance_loop
  - send_with_delay helper now checks connection before and after sleep
- **Fixed yt-dlp Not Found Error**: Modified streamer.py to use `python -m yt_dlp` instead of `yt-dlp` command directly
  - Resolves "No such file or directory: 'yt-dlp'" error on hosting platforms
  - Uses sys.executable to ensure correct Python interpreter is used
  - Maintains full subprocess functionality for proper skip/cancel handling
- **Fixed before_start SDK Compatibility**: Made tg parameter optional in MusicBot.before_start()
  - Resolves "missing 1 required positional argument: 'tg'" error
  - Works with both old and new versions of Highrise SDK
  - Falls back to asyncio.create_task when TaskGroup not available

### November 22, 2025 - Smart YouTube Rate Limiting & Comprehensive Setup System
- **Smart Rate Limiting System**: Prevents YouTube blocking with intelligent request throttling
  - Random delays between downloads (5-15 seconds)
  - Maximum 20 downloads per hour limit
  - Automatic 5-minute wait when HTTP 429 error detected
  - Download history tracking to prevent rate limit violations
- **Comprehensive Setup System** (Enhanced `main.py`)
  - Automatic environment checks and validation
  - Required files verification
  - Python dependencies checking
  - Automatic directory and data file creation
  - System tools verification (FFmpeg, yt-dlp)
  - Clear startup messages with pass/fail status
- **New Startup Files**:
  - `startup.sh` - Shell script for quick launch on any hosting
  - `SETUP_GUIDE.md` - Complete installation and setup guide for bot hosting
- **Improved Error Handling**:
  - Better detection of YouTube blocking (HTTP 429 errors)
  - Automatic pause and retry mechanism
  - Detailed logging of rate limit events

### November 20, 2025 - Automatic Cache Cleaning System
- **Automatic Cache Management**: Added intelligent auto-cleaning system for song cache
  - Automatic cleanup after each successful song download
  - Configurable limits: max 100 songs or 1GB storage (80% threshold triggers cleanup)
  - Protects default playlist songs from deletion
  - Deletes oldest user-requested songs first when limits are exceeded
- **Manual Owner Commands**: New cache management commands for bot owner
  - `!cleancache` - Manually clean all user-added songs (keeps defaults)
  - `!cacheinfo` - View detailed cache statistics (total/default/user songs, size, limits)
- **Configuration Settings** (`config.py`):
  - `AUTO_CLEAN_ENABLED = True` - Enable/disable automatic cleaning
  - `MAX_CACHE_SIZE_MB = 1024` - Maximum cache size in megabytes
  - `MAX_CACHED_SONGS = 100` - Maximum number of cached songs
- **Shared Helper Functions**: Centralized default song detection to ensure consistency across all cache operations

### November 20, 2025 - Outfit Copying & Bot Position Management
- **Fixed !equip Command**: Enhanced outfit copying with two-tier search system
  - First searches users in the room (faster)
  - Falls back to Web API search for any Highrise user (even outside room)
  - Better error handling for 404 errors and "user not found" scenarios
- **Added !equipid Command**: Copy outfits using outfit ID as an alternative method
  - Usage: `!equipid <outfit_id>`
  - Example: `!equipid 64f8a2b1c9d3e4f5a6b7c8d9`
- **Added Bot Position Commands**: Save and restore bot position with persistence
  - `add` - Save current bot position (owner only)
  - `go` - Walk to saved position using walk_to (owner only)
  - Position saved in `bot_position.json` and persists across disconnections
- **Default Playlist Expansion**: Expanded from 5 to 40 Mahraganat (Egyptian festival music) songs
  - Fixed "No songs available" issue by populating `default_playlist.txt`
  - Bot now continuously plays from extensive music library

### November 19, 2025 - Command System Improvements
- **Added Direct Message Support**: Bot now responds to private messages with the full commands list automatically
- **Enhanced !withdraw Command**: Now supports withdrawing specific amounts (!withdraw @user 10) or all tickets (!withdraw @user)
- **@ Symbol Support**: All commands that accept usernames now work with or without the @ symbol
- **Updated Commands List**: Improved clarity and added usage examples for all owner commands
- **Fixed Commands**:
  - !addtickets @user <number> - Add tickets to a user
  - !withdraw @user [number] - Withdraw specific amount or all tickets
  - !free @user - Grant free VIP
  - !unfree @user - Remove VIP
  - !give @user <amount> - Send gold
  - !commands / !help - Show commands list (also works in DM)
  - All owner management commands now strip @ from usernames automatically

## System Architecture

### Core Components

**1. Comprehensive Startup System**
- **Main Orchestrator** (`main.py`): Enhanced orchestrator that handles environment setup, validation, and service launch
  - Automatic system checks (files, dependencies, tools)
  - Environment variable validation
  - Automatic directory and file creation
  - Clear startup status reporting
- **Highrise Bot Service** (`highrise_music_bot.py`): Handles user interactions, command processing, and chat communication within the Highrise virtual world
- **Streaming Service** (`streamer.py`): Manages audio streaming to Zeno.fm, downloads songs, handles playlist playback, and implements smart rate limiting

**Rationale**: Separating the chat bot from the streaming service allows independent operation and easier debugging. The enhanced main.py ensures all prerequisites are met before launch, making deployment seamless on any hosting platform.

**2. File-Based Inter-Process Communication**
- Uses text files (`queue.txt`, `playlist_state.json`, `song_notifications.json`) as the communication layer between bot and streamer
- Queue system where bot writes requests and streamer consumes them
- State files track current playback, playlist position, and notifications

**Rationale**: Simple, reliable communication that persists across restarts. No complex message queuing systems needed for this use case.

**3. Playlist Management System**
- **Continuous Playlist Manager** (`continuous_playlist_manager.py`): Manages seamless transitions between default playlist and user requests
- Default playlist fallback when queue is empty
- Tracks playlist state and history in JSON files
- Maintains playback continuity without gaps

**4. Ticket/VIP System**
- **Tickets System** (`tickets_system.py`): Controls song request permissions through a ticket-based economy
- Users earn tickets by tipping the bot (10 gold = 5 tickets)
- VIP users stored separately in `vip_users.json`
- Ticket balances persisted in `tickets_data.json`

**Rationale**: Prevents spam and abuse while incentivizing engagement. VIP system allows privilege escalation for trusted users.

**5. Bot Dancing System**
- Continuous dance animation loop using Highrise emote system
- Dance patterns defined in `bot_dances.json` with precise duration timings
- Asynchronous dance task runs parallel to message handling

**6. Staff Management**
- Auto-detection of moderators, designers, and room owners
- Cached in `staff_cache.json` for persistent recognition
- Manual moderator list override available in configuration

**7. Search and Selection Flow**
- YouTube search via yt-dlp integration
- Results stored temporarily per user in memory
- Pagination support (+ command for more results)
- User selects by number, bot adds to queue

**8. Updates Management System** (Added: October 2025)
- **Web Interface** (`updates.html`): Modern web UI for file management
- **Flask API** (`updates_manager.py`): Backend for file upload/download operations
- **Features**:
  - Upload and replace files with automatic backup
  - Search for similar files automatically
  - Download core files as ZIP (excludes config.py and cache)
  - Download all project files as ZIP
  - Backup system saves replaced files with timestamps

**Rationale**: Provides easy way to update bot files without direct file system access. Automatic backups prevent data loss.

### Technology Stack

**Backend Framework**
- **Highrise Bot SDK**: Official SDK for Highrise platform integration
- **Python AsyncIO**: Asynchronous event handling for bot responsiveness
- **yt-dlp**: YouTube downloading and metadata extraction
- **FFmpeg**: Audio transcoding and streaming

**Data Storage**
- **JSON Files**: Configuration, state persistence, user data (tickets, VIP, staff cache)
- **Text Files**: Queue management, playlists, history logging
- **In-Memory Storage**: Temporary search results, user session data

**Streaming Pipeline**
- Downloads audio from YouTube using yt-dlp
- Converts to MP3 format via FFmpeg
- Streams to Icecast server (Zeno.fm) using FFmpeg output pipe
- Cache system stores downloaded songs to avoid re-downloading

### Configuration Management

**Centralized Config** (`config.py`)
- Dataclass-based configuration for type safety
- Environment variable integration for secrets (bot tokens, passwords)
- Separate setting groups: System Files, Stream Settings, Log Settings, Highrise Settings
- Configurable logging levels for production vs development

### Message Response System

**Centralized Responses** (`responses.py`)
- All bot messages defined in a single class
- Supports message categorization (music, error, info, success)
- Easy localization - currently Arabic
- Consistent user experience across all interactions

### Error Handling & Resilience

- **Smart Rate Limiting**: Prevents YouTube HTTP 429 blocks with automatic throttling
  - Random delays between downloads (5-15 seconds each)
  - Maximum 20 downloads per hour limit
  - Automatic 5-minute pause when blocked
  - Download history tracking
- Retry mechanism for failed song downloads (MAX_RETRY_ATTEMPTS)
- Failed requests tracked in `failed_requests.txt`
- Minimum song duration validation
- Timeout handling for search operations
- Graceful fallback to default playlist
- **System Validation**: Comprehensive checks on startup for smooth deployment

### Pros of Current Architecture

- **Simplicity**: File-based communication is easy to debug and monitor
- **Persistence**: All state survives restarts automatically
- **Modularity**: Each component has single responsibility
- **Scalability**: Can easily add more bots reading from same queue
- **Language Support**: Arabic-first design with easy localization path

### Cons and Trade-offs

- **File I/O Overhead**: Frequent file reads/writes for queue management
- **No Real-time Sync**: Small delay between services due to file polling
- **Single Point of Failure**: File corruption could break communication
- **Limited Concurrency**: File locking not implemented, potential race conditions

## External Dependencies

### Third-Party Services

**Zeno.fm Streaming**
- Radio streaming platform
- Icecast protocol for audio input
- Stream URL: `stream.zeno.fm` (configured per deployment)
- Authentication via username/password in environment variables

**YouTube (via yt-dlp)**
- Primary audio source for song requests
- No API key required (uses public interface)
- Format selection prioritizes audio quality
- Metadata extraction for titles and durations

### APIs and Integrations

**Highrise Platform**
- Bot SDK for virtual world interaction
- WebSocket-based communication
- Room management and user presence
- Emote/animation system integration

### External Libraries

**Core Dependencies** (from `requirements.txt`)
- `aiohttp==3.12.13`: Async HTTP client for API calls
- `highrise-bot-sdk==24.1.0`: Official Highrise integration
- `requests==2.32.5`: Synchronous HTTP for simple operations
- `yt-dlp==2025.9.26`: YouTube download and extraction

**System Requirements**
- FFmpeg: Audio processing and streaming (not in requirements.txt, system-level)
- Python 3.8+: Async/await syntax and dataclass support

### Database/Storage

**No Traditional Database**
- All data stored in JSON/text files
- No SQL or NoSQL database required
- Simple key-value storage pattern
- Suitable for single-instance deployment

**File-Based Storage**
- `tickets_data.json`: User ticket balances
- `vip_users.json`: VIP user list
- `staff_cache.json`: Detected staff members
- `queue.txt`: Song request queue
- `play_history.txt`: Playback log
- `playlist_state.json`: Current playback state
- `song_notifications.json`: Now playing information