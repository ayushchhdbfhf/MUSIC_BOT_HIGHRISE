#!/usr/bin/env python3
"""
Live streaming service to Zeno.fm
"""

import os
import subprocess
import time
import json
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from continuous_playlist_manager import ContinuousPlaylistManager
from config import SystemFiles, StreamSettings, LogSettings
from highrise_music_bot import BotResponses
import hashlib
import random
import re
import sys
import tempfile
import gc


def clean_search_query(query: str) -> str:
    """Clean search query from emojis and problematic symbols"""
    # If it's a URL, return as is (trimmed)
    if query.strip().startswith(('http://', 'https://')):
        return query.strip()

    # Remove emojis (Unicode ranges for emojis)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001f926-\U0001f937"  # other emojis
        "\U00010000-\U0010ffff"  # additional emoji ranges
        "\u2600-\u26FF"          # misc symbols
        "\u2700-\u27BF"          # dingbats
        "\u231A-\u231B"          # watch/hourglass
        "\u23E9-\u23F3"          # media control
        "\u23F8-\u23FA"          # media control
        "\u25AA-\u25AB"          # squares
        "\u25B6"                 # play button
        "\u25C0"                 # reverse button
        "\u25FB-\u25FE"          # squares
        "\u2614-\u2615"          # umbrella/hot beverage
        "\u2648-\u2653"          # zodiac
        "\u267F"                 # wheelchair
        "\u2693"                 # anchor
        "\u26A1"                 # lightning
        "\u26AA-\u26AB"          # circles
        "\u26BD-\u26BE"          # balls
        "\u26C4-\u26C5"          # weather
        "\u26CE"                 # ophiuchus
        "\u26D4"                 # no entry
        "\u26EA"                 # church
        "\u26F2-\u26F3"          # fountain/golf
        "\u26F5"                 # sailboat
        "\u26FA"                 # tent
        "\u26FD"                 # fuel pump
        "\u2702"                 # scissors
        "\u2705"                 # check mark
        "\u2708-\u270D"          # airplane to writing hand
        "\u270F"                 # pencil
        "\u2712"                 # black nib
        "\u2714"                 # check mark
        "\u2716"                 # x mark
        "\u271D"                 # latin cross
        "\u2721"                 # star of david
        "\u2728"                 # sparkles
        "\u2733-\u2734"          # eight spoked asterisk
        "\u2744"                 # snowflake
        "\u2747"                 # sparkle
        "\u274C"                 # cross mark
        "\u274E"                 # cross mark
        "\u2753-\U00002755"      # question marks
        "\U00002757"             # exclamation mark
        "\U00002763-\U00002764"  # heart marks
        "\U00002795-\U00002797"  # math symbols
        "\U000027A1"             # arrow
        "\U000027B0"             # curly loop
        "\U000027BF"             # double curly loop
        "\U00002934-\U00002935"  # arrows
        "\U00002B05-\U00002B07"  # arrows
        "\U00002B1B-\U00002B1C"  # squares
        "\U00002B50"             # star
        "\U00002B55"             # circle
        "\U00003030"             # wavy dash
        "\U0000303D"             # part alternation mark
        "\U00003297"             # circled ideograph congratulation
        "\U00003299"             # circled ideograph secret
        "]+", flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub('', query)
    
    # Remove hashtags
    cleaned = re.sub(r'#\S+', '', cleaned)
    
    # Remove excess special characters
    cleaned = re.sub(r'[^\w\s\-]', ' ', cleaned)
    
    # Clean extra spaces
    cleaned = ' '.join(cleaned.split())
    
    return cleaned.strip()


logging.basicConfig(
    level=getattr(LogSettings.LOG_LEVEL, LogSettings.LOG_LEVEL, logging.WARNING),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('streamer')

def get_cache_filename_for_query(query: str) -> str:
    """Generate unique filename based on query"""
    query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in query)
    safe_name = safe_name[:50].strip()
    return f"{StreamSettings.CACHE_DIR}/{safe_name}_{query_hash}.mp3"

def is_default_song_file(file_path: str) -> bool:
    """Check if song is from default songs"""
    from config import DEFAULT_SONGS
    
    file_name = Path(file_path).name
    
    for default_song in DEFAULT_SONGS:
        expected_cache_file = get_cache_filename_for_query(default_song)
        if Path(expected_cache_file).name == file_name:
            return True
    
    return False

class ZenoStreamer:
    """Service to stream to Zeno.fm"""

    def __init__(self):
        self.playlist_manager = ContinuousPlaylistManager()
        self.zeno_password = StreamSettings.ZENO_PASSWORD
        self.stream_url = f"icecast://{StreamSettings.ZENO_USERNAME}:{self.zeno_password}@{StreamSettings.ZENO_SERVER}:{StreamSettings.ZENO_PORT}/{StreamSettings.ZENO_MOUNT_POINT}"
        self.notifications_file = SystemFiles.SONG_NOTIFICATIONS
        self.skip_signal_file = "skip_signal.txt"
        self.current_process = None
        self.ffmpeg_bin = "ffmpeg"
        self.ffprobe_bin = "ffprobe"
        self.last_cache_cleanup = time.time()
        try:
            test_ffmpeg = subprocess.run([self.ffmpeg_bin, "-version"], capture_output=True)
            if test_ffmpeg.returncode != 0:
                raise Exception("ffmpeg not found")
        except Exception:
            try:
                from imageio_ffmpeg import get_ffmpeg_exe, get_ffprobe_exe
                self.ffmpeg_bin = get_ffmpeg_exe()
                try:
                    self.ffprobe_bin = get_ffprobe_exe()
                except Exception:
                    self.ffprobe_bin = self.ffmpeg_bin
                logger.info(f"🎬 Using ffmpeg from: {self.ffmpeg_bin}")
            except Exception as e:
                logger.warning(f"⚠️ Could not find ffmpeg/ffprobe: {e}")
        
        # Download tracking system to avoid bans
        self.download_history = []
        self.max_downloads_per_hour = 20
        self.rate_limit_cooldown = 0
        self.last_429_error = None
        
        # Pre-download system for next song
        self.next_song_cache = None  # {"song": "...", "file": "..."}
        self.predownload_thread = None

        # Create cache directory
        if not getattr(StreamSettings, "NO_CACHE", False):
            Path(StreamSettings.CACHE_DIR).mkdir(exist_ok=True)
            logger.info(f"📁 Cache directory ready: {StreamSettings.CACHE_DIR}")
        
        if StreamSettings.AUTO_CLEAN_ENABLED and not getattr(StreamSettings, "NO_CACHE", False):
            self.clean_old_cache()

    def get_cache_filename(self, query: str) -> str:
        if getattr(StreamSettings, "NO_CACHE", False):
            query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in query)[:50].strip()
            tmpdir = tempfile.gettempdir()
            return str(Path(tmpdir) / f"hr_tmp_{safe_name}_{query_hash}.mp3")
        return get_cache_filename_for_query(query)
    
    def check_rate_limit(self):
        """Check rate limit and wait if necessary"""
        now = datetime.now()
        
        # If recent 429 error, wait longer
        if self.last_429_error:
            time_since_error = (now - self.last_429_error).total_seconds()
            if time_since_error < 300:  # 5 minutes
                wait_time = 300 - time_since_error
                logger.warning(f"⏸️ Waiting {wait_time:.0f}s due to previous 429 error")
                time.sleep(wait_time)
                self.last_429_error = None
                now = datetime.now()  # Update time after waiting
        
        # Clean old downloads (older than 1 hour)
        one_hour_ago = now - timedelta(hours=1)
        self.download_history = [dt for dt in self.download_history if dt > one_hour_ago]
        
        # Check download count in last hour
        if len(self.download_history) >= self.max_downloads_per_hour:
            oldest = min(self.download_history)
            wait_seconds = (oldest + timedelta(hours=1) - now).total_seconds()
            if wait_seconds > 0:
                logger.warning(f"⚠️ Max limit reached ({self.max_downloads_per_hour} downloads/hour)")
                logger.info(f"⏳ Waiting {wait_seconds:.0f} seconds...")
                time.sleep(wait_seconds)
                now = datetime.now()  # Update time after waiting
                # Clean again after waiting
                one_hour_ago = now - timedelta(hours=1)
                self.download_history = [dt for dt in self.download_history if dt > one_hour_ago]
        
        self.download_history.append(datetime.now())
        delay_seconds = random.uniform(1, 3)
        logger.info(f"⏱️ Random slight delay before download: {delay_seconds:.1f}s")
        time.sleep(delay_seconds)
    
    def clean_old_cache(self):
        if getattr(StreamSettings, "NO_CACHE", False):
            return
        try:
            cache_dir = Path(StreamSettings.CACHE_DIR)
            if not cache_dir.exists():
                return
            
            # Delete partial and temp files first
            for pattern in ["*.temp*", "*.part*", "*.ytdl*", "*.mp3.part*", "*.mp4.part*", "*.webm.part*"]:
                for tmpf in cache_dir.glob(pattern):
                    try:
                        tmpf.unlink()
                    except:
                        pass
            
            all_files = list(cache_dir.glob("*.mp3")) + list(cache_dir.glob("*.mp4")) + list(cache_dir.glob("*.webm"))
            
            if not all_files:
                logger.info("🧹 No files to clean")
                return
            
            total_size = sum(f.stat().st_size for f in all_files)
            total_size_mb = total_size / (1024 * 1024)
            total_files = len(all_files)
            
            logger.info(f"📊 Cache check: {total_files} songs, {total_size_mb:.1f} MB")
            
            files_to_delete = []
            
            if total_size_mb > StreamSettings.MAX_CACHE_SIZE_MB or total_files > StreamSettings.MAX_CACHED_SONGS:
                logger.info(f"⚠️ Max limit exceeded: {total_files}/{StreamSettings.MAX_CACHED_SONGS} songs, {total_size_mb:.1f}/{StreamSettings.MAX_CACHE_SIZE_MB} MB")
                
                default_files = []
                user_files = []
                
                for file_path in all_files:
                    if is_default_song_file(str(file_path)):
                        default_files.append(file_path)
                    else:
                        user_files.append(file_path)
                
                logger.info(f"📝 Default songs: {len(default_files)}, User songs: {len(user_files)}")
                
                user_files.sort(key=lambda f: f.stat().st_mtime)
                default_files.sort(key=lambda f: f.stat().st_mtime)
                
                current_size_mb = total_size_mb
                current_count = total_files
                
                # First: delete user songs if we want to reduce memory
                if not getattr(StreamSettings, "KEEP_USER_CACHE", False):
                    for old_file in user_files:
                        file_size_mb = old_file.stat().st_size / (1024 * 1024)
                        files_to_delete.append(old_file)
                        current_size_mb -= file_size_mb
                        current_count -= 1
                else:
                    max_user_keep = max(5, int(StreamSettings.MAX_CACHED_SONGS * 0.2))
                    for old_file in user_files[:-max_user_keep]:
                        file_size_mb = old_file.stat().st_size / (1024 * 1024)
                        files_to_delete.append(old_file)
                        current_size_mb -= file_size_mb
                        current_count -= 1
                
                # Second: if still over limit, delete oldest default
                if current_size_mb > StreamSettings.MAX_CACHE_SIZE_MB or current_count > StreamSettings.MAX_CACHED_SONGS:
                    max_default_keep = max(20, int(StreamSettings.MAX_CACHED_SONGS * 0.8))
                    for old_file in default_files[:-max_default_keep]:
                        if current_size_mb <= StreamSettings.MAX_CACHE_SIZE_MB * 0.9 and current_count <= StreamSettings.MAX_CACHED_SONGS * 0.9:
                            break
                        file_size_mb = old_file.stat().st_size / (1024 * 1024)
                        files_to_delete.append(old_file)
                        current_size_mb -= file_size_mb
                        current_count -= 1
            
            if files_to_delete:
                deleted_count = 0
                freed_space_mb = 0
                
                for file_to_delete in files_to_delete:
                    try:
                        file_size = file_to_delete.stat().st_size / (1024 * 1024)
                        file_to_delete.unlink()
                        deleted_count += 1
                        freed_space_mb += file_size
                        logger.info(f"🗑️ Deleted: {file_to_delete.name} ({file_size:.1f} MB)")
                    except Exception as e:
                        logger.error(f"❌ Failed to delete {file_to_delete.name}: {e}")
                
                logger.info(f"✅ Cleaned {deleted_count} old songs, freed {freed_space_mb:.1f} MB")
            else:
                logger.info("✅ Space is good, no cleaning needed")
        
        except Exception as e:
            logger.error(f"❌ Auto-clean error: {e}")

    def download_song(self, query: str) -> Optional[str]:
        """Download song from YouTube or use cached version"""
        try:
            original_query = query
            cleaned_query = clean_search_query(query)
            
            if not cleaned_query or len(cleaned_query) < 3:
                logger.warning(f"⚠️ Search query too short after cleaning: '{original_query}' -> '{cleaned_query}'")
                search_query = original_query
            else:
                search_query = cleaned_query
                if original_query != cleaned_query:
                    logger.info(f"🧹 Search query cleaned: '{original_query}' -> '{cleaned_query}'")
            
            msg, _ = BotResponses.STREAM_SEARCHING
            logger.info(msg.format(query=search_query))

            cache_file = self.get_cache_filename(query)

            if Path(cache_file).exists() and not getattr(StreamSettings, "NO_CACHE", False):
                file_size = Path(cache_file).stat().st_size
                # Check if file is complete (larger than 100KB and readable)
                if file_size > 100000:  # At least 100KB
                    # Verify file via ffprobe
                    try:
                        verify_cmd = [
                            self.ffprobe_bin, "-v", "error",
                            "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1",
                            cache_file
                        ]
                        verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=10)
                        if verify_result.returncode == 0 and verify_result.stdout.strip():
                            duration = float(verify_result.stdout.strip())
                            if duration > 10:  # More than 10 seconds
                                logger.info(f"✅ Using cached complete version: {cache_file} ({duration:.0f}s)")
                                return cache_file
                            else:
                                logger.warning(f"⚠️ File too short ({duration:.0f}s), deleting: {cache_file}")
                                Path(cache_file).unlink()
                        else:
                            logger.warning(f"⚠️ Corrupt file, deleting: {cache_file}")
                            Path(cache_file).unlink()
                    except Exception as verify_error:
                        logger.warning(f"⚠️ File verification failed: {verify_error}")
                        Path(cache_file).unlink()
                else:
                    logger.warning(f"⚠️ File too small ({file_size} bytes), deleting: {cache_file}")
                    Path(cache_file).unlink()

            self.check_rate_limit()
            
            base_name = cache_file.replace('.mp3', '')
            temp_file = f"{base_name}.temp"  # yt-dlp will make it .temp.mp3
            temp_file_with_ext = f"{temp_file}.mp3"  # Actual output file
            output_file = cache_file

            # Basic yt-dlp arguments
            cmd_base = [
                sys.executable, "-m", "yt_dlp",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--no-check-certificates",
                "--extractor-retries", "3",
                "--retries", "2",
                "--socket-timeout", "20",
                "--concurrent-fragments", "1",
                "--max-filesize", "20M",
                "--match-filter", "!is_live",
                "-o", temp_file,
            ]

            # Add cookies if available
            if Path("cookies.txt").exists() and Path("cookies.txt").stat().st_size > 100:
                logger.info("🍪 Found cookies.txt, using for authentication")
                cmd_base.extend(["--cookies", "cookies.txt"])

            # Download strategies (try different identities)
            download_strategies = [
                {"name": "Default", "args": []}
            ]
            
            for strategy in download_strategies:
                logger.info(f"🔄 Attempting download with strategy: {strategy['name']}")
                is_url = search_query.strip().startswith(('http://', 'https://'))
                final_query = search_query if is_url else f"ytsearch1:{search_query}"
                cmd = cmd_base + strategy["args"] + [final_query]
                
                try:
                    download_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    # Use communicate with timeout (45s)
                    stdout, stderr = download_process.communicate(timeout=45)
                    stdout = stdout.decode('utf-8', errors='replace')
                    stderr = stderr.decode('utf-8', errors='replace')

                except subprocess.TimeoutExpired:
                    logger.error(f"❌ Download timeout (45s) with strategy: {strategy['name']}")
                    download_process.kill()
                    # Clean output after killing process
                    download_process.communicate()
                    continue # Try next strategy

                if download_process.returncode == 0 and Path(temp_file_with_ext).exists():
                    file_size = Path(temp_file_with_ext).stat().st_size
                    if file_size < 50000:  # 50KB
                        logger.warning(f"⚠️ Downloaded file too small ({file_size} bytes) with strategy {strategy['name']}")
                        Path(temp_file_with_ext).unlink()
                        continue  # Try next strategy

                    # Success!
                    logger.info(f"✅ Download success with strategy: {strategy['name']}")
                    import shutil
                    shutil.move(temp_file_with_ext, output_file)
                    
                    msg, _ = BotResponses.STREAM_DOWNLOADING
                    logger.info(msg.format(title=output_file))
                    
                    if StreamSettings.AUTO_CLEAN_ENABLED:
                        self.clean_old_cache()
                    return output_file
                else:
                    # Failed, log error and try next strategy
                    full_log = f"Stderr: {stderr}\nStdout: {stdout}"
                    if "Sign in to confirm" in full_log:
                        logger.warning(f"⚠️ Login required with {strategy['name']}. IP might be monitored.")
                    if ("HTTP Error 429" in full_log) or ("Too Many Requests" in full_log) or (" 429 " in full_log):
                        logger.warning("⚠️ 429 Detected (Too Many Requests), waiting automatically to avoid ban")
                        self.last_429_error = datetime.now()
                        self.check_rate_limit()
                    
                    logger.warning(f"⚠️ Download failed with {strategy['name']}: {full_log[:500]}...")
                    if Path(temp_file_with_ext).exists():
                        Path(temp_file_with_ext).unlink()

            # If all strategies failed
            logger.error("❌ All download attempts failed")
            msg, _ = BotResponses.STREAM_DOWNLOAD_ERROR
            logger.error(msg.format(error="All strategies failed"))
            return None

        except Exception as e:
            logger.error(f"❌ Download error: {e}")
            return None

    def stream_song(self, audio_file: str, song_title: str, is_user_request: bool = False, requested_by: str = "") -> bool:
        """Stream song to Zeno.fm with proper start from beginning"""
        try:
            msg, _ = BotResponses.STREAM_PLAYING
            logger.info(msg.format(title=song_title))

            # Get song duration
            duration_cmd = [
                self.ffprobe_bin,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_file
            ]

            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
            try:
                duration_seconds = int(float(duration_result.stdout.strip()))
            except:
                duration_seconds = 180  # 3 minutes default

            # Save song information with user request flag and requester
            self.save_song_notification(song_title, duration_seconds, is_user_request, requested_by)

            # Stream song from beginning with correct options
            stream_cmd = [
                self.ffmpeg_bin,
                "-nostdin",
                "-nostats",
                "-hide_banner",
                "-loglevel", "error",
                "-fflags", "+genpts+discardcorrupt",
                "-re",
                "-thread_queue_size", "512",
                "-i", audio_file,
                "-vn",
                "-acodec", "libmp3lame",
                "-b:a", StreamSettings.STREAM_BITRATE,
                "-ar", "32000",
                "-ac", "1",
                "-write_xing", "0",
                "-flush_packets", "1",
                "-bufsize", "128k",
                "-max_interleave_delta", "0",
                "-max_delay", "50000",
                "-f", "mp3",
                "-content_type", "audio/mpeg",
                self.stream_url
            ]

            logger.info("🔌 Starting stream to Zeno.fm from beginning...")
            self.current_process = subprocess.Popen(stream_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            
            # Short wait to ensure stream start
            time.sleep(0.3)
            
            # Check if stream started successfully
            if self.current_process.poll() is not None:
                _, stderr = self.current_process.communicate()
                error_msg = stderr.decode('utf-8', errors='ignore') if stderr else 'Unknown error'
                logger.error(f"❌ Stream start failed: {error_msg[-300:]}")
                fallback_cmd = stream_cmd[:]
                try:
                    idx = fallback_cmd.index(StreamSettings.STREAM_BITRATE)
                    fallback_cmd[idx] = "96k"
                except Exception:
                    pass
                try:
                    self.current_process = subprocess.Popen(fallback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    time.sleep(0.3)
                    if self.current_process.poll() is not None:
                        _, stderr2 = self.current_process.communicate()
                        error_msg2 = stderr2.decode('utf-8', errors='ignore') if stderr2 else 'Unknown error'
                        logger.error(f"❌ Failed to start after 2nd attempt: {error_msg2[-300:]}")
                        return False
                except Exception as e:
                    logger.error(f"❌ Failed to run 2nd attempt: {e}")
                    return False
            
            logger.info("✅ Stream connected, song started from beginning!")

            # Monitor skip signal and user requests during streaming
            while self.current_process.poll() is None:
                # Check for skip signal
                if Path(self.skip_signal_file).exists():
                    msg, _ = BotResponses.STREAM_SKIP_SIGNAL
                    logger.info(msg)
                    # Kill process immediately
                    self.current_process.kill()
                    try:
                        self.current_process.wait(timeout=2)
                    except:
                        pass
                    Path(self.skip_signal_file).unlink()
                    logger.info("✅ Stream stopped immediately (Skipped)")
                    # Delete song on skip
                    self._delete_after_play(audio_file)
                    # Return True because skip is a successful operation (not a failure)
                    return True


                # Check for skip_default_only signal (only affects default songs)
                if Path("skip_default_only.txt").exists():
                    if not self.playlist_manager.is_playing_user_request:
                        logger.info("⏭️ Skipping default song (special signal)")
                        self.current_process.kill()
                        try:
                            self.current_process.wait(timeout=2)
                        except:
                            pass
                        Path("skip_default_only.txt").unlink()
                        logger.info("✅ Default song stopped")
                        # Delete song on skip
                        self._delete_after_play(audio_file)
                        # Return True because skip is a successful operation
                        return True
                    else:
                        # Delete signal if current song is user request
                        Path("skip_default_only.txt").unlink()
                        logger.info("🔒 Skip signal ignored - current song is user request")

                time.sleep(0.3)

            if self.current_process.returncode == 0:
                msg, _ = BotResponses.STREAM_ENDED
                logger.info(msg.format(title=song_title))
                
                # Drain any remaining data from stdout/stderr
                try:
                    self.current_process.stdout.read()
                    self.current_process.stderr.read()
                except:
                    pass
                
                # Close pipes cleanly
                try:
                    self.current_process.stdout.close()
                    self.current_process.stderr.close()
                except:
                    pass
                
                # Ensure process finished completely
                self.current_process = None
                
                # Delete song after playback
                self._delete_after_play(audio_file)
                return True
            else:
                # Get error details from stderr
                try:
                    _, stderr = self.current_process.communicate(timeout=2)
                    error_msg = stderr.decode('utf-8', errors='ignore') if stderr else 'Unknown error'
                except:
                    error_msg = 'Unknown error (timeout)'
                    
                ret = self.current_process.returncode
                err_tail = error_msg[-500:]
                if ret in (-10054, 4294957242) or ("Error number -10054" in err_tail) or ("Error writing trailer" in err_tail):
                    msg, _ = BotResponses.STREAM_ENDED
                    logger.warning(f"⚠️ Icecast connection closed during finish (ret={ret}). Treating as normal end.")
                    logger.info(msg.format(title=song_title))
                    try:
                        self.current_process.stdout.read()
                        self.current_process.stderr.read()
                    except:
                        pass
                    try:
                        self.current_process.stdout.close()
                        self.current_process.stderr.close()
                    except:
                        pass
                    self.current_process = None
                    self._delete_after_play(audio_file)
                    return True
                else:
                    logger.error(f"❌ Streaming failed with return code {ret}")
                    logger.error(f"❌ FFmpeg error: {err_tail}")
                    self.current_process = None
                    self._delete_after_play(audio_file)
                    return False

        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            if self.current_process:
                try:
                    self.current_process.kill()
                    self.current_process.wait(timeout=1)
                except:
                    pass
            # Delete song on error
            self._delete_after_play(audio_file)
            return False
    
    def _delete_after_play(self, audio_file: str):
        """Delete song after playback"""
        try:
            # Modified to keep all songs in cache and not delete them
            if audio_file and Path(audio_file).exists():
                if not is_default_song_file(audio_file):
                    logger.info(f"✅ Keeping user song in cache: {Path(audio_file).name}")
                else:
                    logger.info(f"✅ Keeping default song in cache: {Path(audio_file).name}")
        except Exception as e:
            logger.error(f"❌ Error in _delete_after_play: {e}")
    
    def predownload_next_song(self, song_name: str):
        """Pre-download next song in background"""
        try:
            logger.info(f"⏳ Pre-downloading next song: {song_name}")
            audio_file = self.download_song(song_name)
            if audio_file and audio_file != "SKIPPED":
                self.next_song_cache = {"song": song_name, "file": audio_file}
                logger.info(f"✅ Pre-downloaded: {song_name}")
            else:
                self.next_song_cache = None
        except Exception as e:
            logger.warning(f"⚠️ Pre-download failed: {e}")
            self.next_song_cache = None

    def save_song_notification(self, song_title: str, duration_seconds: int, is_user_request: bool = False, requested_by: str = ""):
        """Save current song information"""
        try:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            duration_formatted = f"{minutes}:{seconds:02d}"

            start_time = datetime.now()
            end_time = start_time + timedelta(seconds=duration_seconds)

            notification = {
                "song_title": song_title,
                "duration_formatted": duration_formatted,
                "duration_seconds": duration_seconds,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "timestamp": start_time.isoformat(),
                "is_user_request": is_user_request,
                "requested_by": requested_by
            }

            with open(self.notifications_file, 'w', encoding='utf-8') as f:
                json.dump(notification, f, ensure_ascii=False, indent=2)

            logger.info(f"📝 Song information saved: {song_title} (user_request={is_user_request}, requested_by={requested_by})")

        except Exception as e:
            logger.error(f"❌ Error saving information: {e}")

    def start_predownload(self):
        """Start pre-downloading next song in background"""
        try:
            if not getattr(StreamSettings, "PREDOWNLOAD_ENABLED", True):
                return
            # Check if there is a pending user request
            user_request = self.playlist_manager.peek_user_request()
            if user_request:
                # Do not pre-download if there is a user request
                return
            
            # Get next song without consuming it
            next_default = self.playlist_manager.peek_next_default_song()
            if next_default and (not self.next_song_cache or self.next_song_cache.get("song") != next_default):
                self.predownload_thread = threading.Thread(
                    target=self.predownload_next_song, 
                    args=(next_default,),
                    daemon=True
                )
                self.predownload_thread.start()
        except Exception as e:
            logger.warning(f"⚠️ Error starting pre-download: {e}")

    def run(self):
        """Run continuous streaming service with seamless transitions"""
        logger.info("🎵 Starting live streaming service")

        while True:
            try:
                # Periodic cache cleanup
                try:
                    if time.time() - self.last_cache_cleanup > getattr(StreamSettings, "CACHE_CLEAN_INTERVAL_SEC", 300):
                        self.clean_old_cache()
                        self.last_cache_cleanup = time.time()
                except Exception:
                    pass
                # Check for skip signal before starting
                if Path(self.skip_signal_file).exists():
                    msg, _ = BotResponses.STREAM_SKIP_SIGNAL
                    logger.info(msg)
                    Path(self.skip_signal_file).unlink()
                    # Cancel pre-download on skip
                    self.next_song_cache = None

                # Check if there's a user request first (highest priority)
                user_request = self.playlist_manager.peek_user_request()
                if user_request:
                    # Cancel pre-download because user request has priority
                    self.next_song_cache = None

                # Get next song
                next_song = self.playlist_manager.get_next_song()

                if not next_song:
                    logger.warning("⚠️ No songs to play")
                    time.sleep(10)
                    continue

                # Use pre-downloaded song if available
                audio_file = None
                if self.next_song_cache and self.next_song_cache.get("song") == next_song:
                    audio_file = self.next_song_cache.get("file")
                    if audio_file and Path(audio_file).exists():
                        logger.info(f"⚡ Using pre-downloaded song: {next_song}")
                        self.next_song_cache = None
                    else:
                        audio_file = None
                        self.next_song_cache = None
                
                # If not pre-downloaded, download now
                if not audio_file:
                    audio_file = self.download_song(next_song)

                # If skipped during download
                if audio_file == "SKIPPED":
                    logger.info("⏭️ Song skipped during download by user")
                    Path(self.skip_signal_file).unlink(missing_ok=True)

                    # Remove request from queue if it was a user request
                    if self.playlist_manager.is_playing_user_request:
                        self.playlist_manager.consume_user_request()
                        self.playlist_manager.is_playing_user_request = False
                    
                    continue

                if not audio_file:
                    self.playlist_manager.mark_request_failed(next_song)
                    
                    # If it was a user request, move it to end or delete it
                    if self.playlist_manager.is_playing_user_request:
                        self.playlist_manager.move_failed_request_to_end()
                    
                    continue

                # Start streaming
                is_request = self.playlist_manager.is_playing_user_request
                requester = self.playlist_manager.get_current_requester() if is_request else "Auto"
                
                # Start pre-downloading next song during current song playback
                self.start_predownload()
                
                success = self.stream_song(audio_file, next_song, is_request, requester)

                if success:
                    if is_request:
                        self.playlist_manager.consume_user_request()
                    self.playlist_manager.mark_song_finished(next_song)
                else:
                    self.playlist_manager.mark_request_failed(next_song)

            except Exception as e:
                logger.error(f"❌ Service error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    streamer = ZenoStreamer()
    streamer.run()
