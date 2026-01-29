#!/usr/bin/env python3
"""
Continuous Playlist Manager System
Maintains uninterrupted streaming and plays requests immediately
"""


import os
import time
import json
import logging
import threading
from pathlib import Path
import random
import re
from typing import List, Optional, Dict
from datetime import datetime

# Import settings from config.py
from config import SystemFiles, StreamSettings, DEFAULT_SONGS, LogSettings

logging.basicConfig(
    level=getattr(logging, LogSettings.LOG_LEVEL, logging.WARNING),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('continuous_playlist')

class ContinuousPlaylistManager:
    """Continuous Playlist Manager"""

    def __init__(self):
        # System files from config
        self.QUEUE_FILE = SystemFiles.QUEUE
        self.DEFAULT_PLAYLIST_FILE = SystemFiles.DEFAULT_PLAYLIST
        self.CURRENT_STATE_FILE = SystemFiles.PLAYLIST_STATE
        self.HISTORY_FILE = SystemFiles.HISTORY
        self.FAILED_REQUESTS_FILE = SystemFiles.FAILED_REQUESTS

        # System state
        self.current_song = None
        self.is_playing_user_request = False
        self.default_playlist = []
        self.current_default_index = 0
        self.last_played_time = None
        self.disable_default_playlist = False

        # Settings from config
        self.min_song_duration = StreamSettings.MIN_SONG_DURATION
        self.shuffle_default_playlist = True
        self.max_retry_attempts = StreamSettings.MAX_RETRY_ATTEMPTS

        # Track failed attempts
        self.failed_requests = {}  # {song: attempts_count}

        # Load saved data
        self.load_default_playlist()
        self.load_state()

        logger.info("🎵 Continuous Playlist Manager started")

    def load_default_playlist(self):
        """Load default playlist"""
        try:
            if Path(self.DEFAULT_PLAYLIST_FILE).exists():
                with open(self.DEFAULT_PLAYLIST_FILE, 'r', encoding='utf-8') as f:
                    self.default_playlist = [
                        line.strip() for line in f.readlines() 
                        if line.strip() and not line.strip().startswith('#')
                    ]
                if self.default_playlist:
                    logger.info(f"✅ Loaded {len(self.default_playlist)} default songs")
                else:
                    logger.warning("⚠️ Playlist empty, using default list")
                    self.create_default_playlist()
            else:
                # Create basic default playlist
                self.create_default_playlist()
        except Exception as e:
            logger.error(f"❌ Error loading default playlist: {e}")
            self.create_default_playlist()

    def create_default_playlist(self):
        """Create default playlist"""
        default_songs = DEFAULT_SONGS

        try:
            with open(self.DEFAULT_PLAYLIST_FILE, 'w', encoding='utf-8') as f:
                for song in default_songs:
                    f.write(f"{song}\n")
            self.default_playlist = default_songs
            logger.info(f"✅ Created default playlist with {len(default_songs)} songs")
        except Exception as e:
            logger.error(f"❌ Error creating default playlist: {e}")

    def load_state(self):
        """Load saved playback state"""
        try:
            if Path(self.CURRENT_STATE_FILE).exists():
                with open(self.CURRENT_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.current_default_index = state.get('current_default_index', 0)
                    self.current_song = state.get('current_song')
                    self.is_playing_user_request = state.get('is_playing_user_request', False)
                    self.disable_default_playlist = state.get('disable_default_playlist', False)

                # Ensure index is valid
                if self.current_default_index >= len(self.default_playlist):
                    self.current_default_index = 0

                # Correct old default song name after update
                try:
                    if (self.current_song 
                        and not self.is_playing_user_request 
                        and self.default_playlist):
                        if self.current_song.strip() not in self.default_playlist:
                            logger.info("🔄 Old default song detected in state, replacing with new list")
                            self.current_default_index = 0
                            self.current_song = self.default_playlist[0]
                            self.save_state()
                except Exception:
                    pass

                logger.info("✅ Saved playback state loaded")
        except Exception as e:
            logger.error(f"❌ Error loading state: {e}")

    def save_state(self):
        """Save current playback state"""
        try:
            state = {
                'current_default_index': self.current_default_index,
                'current_song': self.current_song,
                'is_playing_user_request': self.is_playing_user_request,
                'disable_default_playlist': self.disable_default_playlist,
                'last_saved': datetime.now().isoformat()
            }

            with open(self.CURRENT_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"❌ Error saving state: {e}")

    def get_next_song(self) -> Optional[str]:
        """Get next song to play"""
        # First: Check user requests (highest priority)
        user_request = self.peek_user_request()
        if user_request:
            self.current_song = user_request
            self.is_playing_user_request = True
            self.save_state()
            logger.info(f"🎵 User request (immediate priority): {user_request}")
            return user_request
        
        # Update default playlist disable state based on queue
        try:
            has_queue = False
            if Path(self.QUEUE_FILE).exists():
                with open(self.QUEUE_FILE, 'r', encoding='utf-8') as f:
                    has_queue = any(line.strip() for line in f.readlines())
            # Disable default if requests pending
            self.disable_default_playlist = bool(has_queue)
            self.save_state()
        except Exception as e:
            logger.debug(f"Could not update default disable state automatically: {e}")

        # Second: Play from default playlist only if no requests
        if self.default_playlist and not self.disable_default_playlist:
            if self.current_default_index >= len(self.default_playlist):
                self.current_default_index = 0

            song = self.default_playlist[self.current_default_index]
            self.current_song = song
            self.is_playing_user_request = False
            self.save_state()
            logger.info(f"🎶 Default song: {song}")
            return song

        logger.warning("⚠️ No songs available")
        return None

    def mark_song_started_successfully(self, song: str):
        """Record song start success and remove request if user's"""
        if self.is_playing_user_request and song == self.current_song:
            # Remove request from failed list if successful
            if song in self.failed_requests:
                del self.failed_requests[song]
                logger.info(f"🔄 Removed {song} from failed requests list")

            # Remove request from queue after successful start
            if self.consume_user_request():
                logger.info(f"✅ User request started successfully: {song}")
                # Advance to next default song after success
                self.advance_default_index()
            else:
                logger.warning(f"⚠️ Could not remove request from queue: {song}")
        else:
            logger.info(f"✅ Default song started: {song}")
            # Advance to next default song after success
            self.advance_default_index()

    def peek_user_request(self) -> Optional[str]:
        """Peek user request without removing from queue.txt"""
        try:
            if not Path(self.QUEUE_FILE).exists():
                return None
            with open(self.QUEUE_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) > 100:
                trimmed = lines[:100]
                with open(self.QUEUE_FILE, 'w', encoding='utf-8') as wf:
                    wf.writelines(trimmed)

            if not lines:
                return None

            # Peek first request without deleting
            next_request = lines[0].strip()
            if not next_request:
                return None
            
            # Split parts (username, streamer query, title)
            parts = next_request.split('|||')
            if len(parts) == 3: # New format: username|||query_for_streamer|||title_for_display
                _, query_for_streamer, _ = parts
                return query_for_streamer
            elif len(parts) == 2: # Old format: username|||song_query
                _, song_query = parts
                return song_query
            return next_request # fallback for invalid lines
            
        except Exception as e:
            logger.error(f"❌ Error peeking user requests: {e}")
            return None
    
    def get_current_requester(self) -> Optional[str]:
        """Get username who requested current song"""
        try:
            if not Path(self.QUEUE_FILE).exists():
                return None

            with open(self.QUEUE_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if not lines:
                return None

            # Peek first request without deleting
            next_request = lines[0].strip()
            if not next_request:
                return None
            
            # Split parts (username, streamer query, title)
            parts = next_request.split('|||')
            if len(parts) >= 2: # username|||query_for_streamer|||title_for_display or username|||song_query
                username = parts[0]
                return username
            return None

        except Exception as e:
            logger.error(f"❌ Error getting requester name: {e}")
            return None

    def consume_user_request(self) -> bool:
        """Remove first request from queue.txt after success"""
        try:
            if not Path(self.QUEUE_FILE).exists():
                return False

            with open(self.QUEUE_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if not lines:
                return False

            # Delete first request only
            remaining_lines = lines[1:]

            with open(self.QUEUE_FILE, 'w', encoding='utf-8') as f:
                f.writelines(remaining_lines)

            logger.info("✅ Request removed after successful start")
            return True

        except Exception as e:
            logger.error(f"❌ Error removing request: {e}")
            return False

    def get_user_request(self) -> Optional[str]:
        """Read user request from queue.txt - use peek instead"""
        return self.peek_user_request()

    def add_to_history(self, song: str):
        """Add song to playback history"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - {song}\n")
        except Exception as e:
            logger.error(f"❌ Error adding to history: {e}")

    def mark_song_finished(self, song: str):
        """Record song finished successfully"""
        logger.info(f"✅ Song finished: {song}")

        # Check queue and clean if empty
        try:
            if Path(self.QUEUE_FILE).exists():
                with open(self.QUEUE_FILE, 'r', encoding='utf-8') as f:
                    queue = [line.strip() for line in f.readlines() if line.strip()]

                # If list empty, clear file
                if not queue:
                    with open(self.QUEUE_FILE, 'w', encoding='utf-8') as f:
                        f.write("")
                    logger.info("🧹 Queue cleared (empty)")
        except Exception as e:
            logger.error(f"❌ Error cleaning queue: {e}")

        self.save_state()

    def get_queue_status(self) -> Dict[str, any]:
        """Get queue status"""
        try:
            # Count user requests
            user_requests_count = 0
            if Path(self.QUEUE_FILE).exists():
                with open(self.QUEUE_FILE, 'r', encoding='utf-8') as f:
                    user_requests_count = len([line for line in f.readlines() if line.strip()])

            return {
                'current_song': self.current_song,
                'is_user_request': self.is_playing_user_request,
                'user_requests_pending': user_requests_count,
                'default_playlist_size': len(self.default_playlist),
                'current_default_position': self.current_default_index,
                'next_default_song': self.default_playlist[self.current_default_index] if self.default_playlist else None
            }

        except Exception as e:
            logger.error(f"❌ Error getting queue status: {e}")
            return {}

    def mark_request_failed(self, song: str):
        """Record request failure and increment attempts"""
        if song in self.failed_requests:
            self.failed_requests[song] += 1
        else:
            self.failed_requests[song] = 1

        attempts = self.failed_requests[song]
        logger.info(f"❌ Request failed {song} - Attempt {attempts}/{self.max_retry_attempts}")

        try:
            Path(self.FAILED_REQUESTS_FILE).touch()
            with open(self.FAILED_REQUESTS_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{song}\n")
        except Exception as e:
            logger.error(f"❌ Error saving failed requests: {e}")

        if attempts >= self.max_retry_attempts:
            logger.warning(f"⚠️ Max attempts reached for: {song}")
            
            # Remove failed request from queue after max attempts
            if self.is_playing_user_request:
                self.remove_failed_request(song)
                logger.info(f"🗑️ Failed request permanently removed: {song}")
            
            # Remove from failed attempts list
            if song in self.failed_requests:
                del self.failed_requests[song]

    def remove_failed_request(self, song: str):
        """Remove failed request from queue permanently"""
        try:
            if not Path(self.QUEUE_FILE).exists():
                return False
            
            with open(self.QUEUE_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find request and delete
            new_lines = []
            removed = False
            for line in lines:
                line_content = line.strip()
                if not line_content:
                    continue
                
                # Extract streamer query for comparison
                parts = line_content.split('|||')
                if len(parts) == 3:
                    _, query_for_streamer, _ = parts
                elif len(parts) == 2:
                    _, query_for_streamer = parts
                else:
                    query_for_streamer = line_content # fallback
                
                # If this is the failed song, don't add it
                if query_for_streamer == song and not removed:
                    removed = True
                    continue
                
                new_lines.append(line)
            
            # Write updated list
            with open(self.QUEUE_FILE, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            return removed
            
        except Exception as e:
            logger.error(f"❌ Error removing failed request: {e}")
            return False

    def move_failed_request_to_end(self):
        """Move failed request to end of queue"""
        try:
            failed_request = self.peek_user_request()
            if failed_request and self.consume_user_request():
                # Add request to end of list
                with open(self.QUEUE_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"{failed_request}\n")
                logger.info(f"🔄 Failed request moved to end of queue: {failed_request}")

                # Remove from failure list to give it another chance later
                if failed_request in self.failed_requests:
                    del self.failed_requests[failed_request]

        except Exception as e:
            logger.error(f"❌ Error moving failed request: {e}")

    def advance_default_index(self):
        """Advance to next default song"""
        if self.default_playlist:
            self.current_default_index = (self.current_default_index + 1) % len(self.default_playlist)
    
    def peek_next_default_song(self) -> Optional[str]:
        """Peek next default song without changing index"""
        if not self.default_playlist:
            return None
        next_index = (self.current_default_index + 1) % len(self.default_playlist)
        return self.default_playlist[next_index]

    def add_song_to_default_playlist(self, song: str):
        """Add song to default playlist"""
        try:
            if song not in self.default_playlist:
                self.default_playlist.append(song)

                # Save to file
                with open(self.DEFAULT_PLAYLIST_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"{song}\n")

                logger.info(f"✅ Song added to default playlist: {song}")
                return True
            else:
                logger.info(f"⚠️ Song already exists: {song}")
                return False

        except Exception as e:
            logger.error(f"❌ Error adding song: {e}")
            return False

    def ensure_queue_file(self):
        """Ensure queue file exists"""
        if not Path(self.QUEUE_FILE).exists():
            Path(self.QUEUE_FILE).touch()


def test_playlist_manager():
    """Test playlist manager"""
    manager = ContinuousPlaylistManager()

    print("🧪 Testing Playlist Manager")
    print("="*50)

    # Add test request
    with open("queue.txt", "w", encoding="utf-8") as f:
        f.write("Fayrouz - Habbaytak Bessayf\n")

    # Test get next song
    for i in range(5):
        song = manager.get_next_song()
        print(f"🎵 Song {i+1}: {song}")
        if song:
            manager.mark_song_finished(song)
        print(f"📊 Status: {manager.get_queue_status()}")
        print("-" * 30)


if __name__ == "__main__":
    test_playlist_manager()
