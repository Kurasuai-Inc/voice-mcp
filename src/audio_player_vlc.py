"""Simple audio playback module for WSL - uses VLC for multiple simultaneous playback"""

import os
import tempfile
import subprocess
import platform
from typing import Optional, Dict
import httpx
import urllib.parse
import asyncio
import time
import glob
import threading
from queue import Queue

def is_wsl() -> bool:
    """Check if running in WSL environment."""
    return 'microsoft-standard' in platform.uname().release.lower()


# VLC executable path
VLC_PATH = r"C:\Program Files\VideoLAN\VLC\vlc.exe"

# Audio queues and worker threads per model
audio_queues: Dict[str, Queue] = {}
worker_threads: Dict[str, threading.Thread] = {}

def audio_worker(model: str):
    """Worker thread that processes audio files sequentially for a specific model."""
    queue = audio_queues[model]
    while True:
        try:
            win_path = queue.get()
            if win_path is None:  # Shutdown signal
                break
                
            # Play audio file using VLC
            ps_command = f'''
            & "{VLC_PATH}" --intf dummy --dummy-quiet --play-and-exit "{win_path}"
            '''
            
            # Wait for playback to complete
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
            
            queue.task_done()
        except Exception:
            queue.task_done()

def ensure_worker_running(model: str):
    """Ensure the audio worker thread is running for a specific model."""
    if model not in audio_queues:
        audio_queues[model] = Queue()
    
    if model not in worker_threads or not worker_threads[model].is_alive():
        worker_threads[model] = threading.Thread(target=audio_worker, args=(model,), daemon=True)
        worker_threads[model].start()


def cleanup_old_temp_files() -> None:
    """Clean up old temporary audio files from both WSL and Windows temp directories."""
    # Clean WSL temp files
    temp_dir = tempfile.gettempdir()
    audio_files = glob.glob(os.path.join(temp_dir, "tmp*.wav"))
    
    if len(audio_files) > 10:
        # Sort by modification time and remove oldest files
        audio_files.sort(key=os.path.getmtime)
        files_to_remove = audio_files[:-10]  # Keep only the 10 newest
        
        for file_path in files_to_remove:
            try:
                os.remove(file_path)
            except OSError:
                pass  # Ignore if file is already gone or in use
    
    # Clean Windows temp files
    if is_wsl():
        ps_script = '''
        $temp = [System.IO.Path]::GetTempPath()
        $files = Get-ChildItem -Path $temp -Filter "voice_*.wav" | Sort-Object LastWriteTime
        if ($files.Count -gt 10) {
            $toRemove = $files[0..($files.Count - 11)]
            $toRemove | ForEach-Object { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }
        }
        '''
        subprocess.run(
            ["powershell.exe", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )


async def synthesize_and_play(text: str, voice_api_base: str, model: str) -> Optional[str]:
    """Synthesize and play voice from text using VLC in WSL.
    
    Args:
        text: Text to synthesize
        voice_api_base: Base URL for voice API
        model: Voice model to use
        
    Returns:
        Error message if failed, None if successful
    """
    # URL encode the text
    encoded_text = urllib.parse.quote(text)
    url = f"{voice_api_base}/voice?text={encoded_text}&speaker_name={model}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers={"accept": "audio/wav"},
                timeout=30.0
            )
            response.raise_for_status()
            audio_data = response.content
            
            # Clean up old temp files before creating new one
            cleanup_old_temp_files()
            
            # Create a temporary file to store the audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_file_path = tmp_file.name
            
            # Check if running in WSL
            if is_wsl():
                try:
                    # Get Windows temp directory
                    ps_command = "[System.IO.Path]::GetTempPath()"
                    result = subprocess.run(
                        ["powershell.exe", "-Command", ps_command],
                        capture_output=True,
                        text=True
                    )
                    win_temp = result.stdout.strip()
                    
                    # Create unique filename for this model
                    import uuid
                    win_filename = f"voice_{model}_{uuid.uuid4().hex[:8]}.wav"
                    win_path = os.path.join(win_temp, win_filename).replace('/', '\\')
                    
                    # Convert WSL path to Windows path
                    wsl_path = subprocess.check_output(
                        ["wslpath", "-w", tmp_file_path]
                    ).decode().strip()
                    
                    # Copy file to Windows temp
                    copy_command = f'Copy-Item "{wsl_path}" "{win_path}" -Force'
                    subprocess.run(
                        ["powershell.exe", "-Command", copy_command],
                        check=True
                    )
                    
                    # Ensure worker thread is running for this model
                    ensure_worker_running(model)
                    
                    # Add audio file to model-specific queue for sequential playback
                    audio_queues[model].put(win_path)
                    
                    # Clean up WSL temp file
                    try:
                        os.remove(tmp_file_path)
                    except:
                        pass
                        
                    return None
                except Exception as e:
                    return f"VLC playback error: {str(e)}"
            else:
                return "Audio playback not implemented for non-WSL environments"
                
        except Exception as e:
            return f"Error: {str(e)}"