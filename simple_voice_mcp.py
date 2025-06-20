#!/usr/bin/env python
"""Simple voice synthesis MCP server - just send text and it plays."""

import os
import tempfile
from typing import Optional
import httpx
from mcp.server.fastmcp import FastMCP
import pygame
import urllib.parse
import subprocess
import platform
import sys

# Parse command line arguments for model
model_arg = None
for i, arg in enumerate(sys.argv):
    if arg == "--model" and i + 1 < len(sys.argv):
        model_arg = sys.argv[i + 1]
        # Remove the arguments so MCP doesn't see them
        sys.argv.pop(i)  # Remove --model
        sys.argv.pop(i)  # Remove the model value
        break

# Initialize FastMCP server
mcp = FastMCP("simple-voice", version="1.0.0")

# Voice API configuration
VOICE_API_BASE = os.getenv("VOICE_API_BASE", "https://kurausuai-voice.ngrok.app")
DEFAULT_MODEL = model_arg or os.getenv("VOICE_MODEL", "zingai_1")

# Model descriptions
MODEL_INFO = {
    "ozisan_2": "普通のおじさんの声",
    "seinen_2": "さわやかな関西弁のお兄さんの声",
    "oneesan_4": "安心感のある透き通ったお姉さんの声",
    "syouzyo_6": "無気力な少女の声",
    "zingai_1": "かわいいマスコットキャラクターのような声",
    "sutera": "ステラの声",
    "syounen_1": "元気な少年の声",
    "syouzyo_4": "のじゃろりの声",
    "seinen_3": "ちょっと気弱そうなお兄さんの声",
    "oneesan_2": "落ち着いた声のお姉さんの声",
    "syouzyo_3": "ツンデレ系の少女の声",
    "oziisan": "おじいさんの声",
    "seinen_5": "声の高い、ちょっとうざそうなお兄さんの声",
    "syouzyo_1": "普通の少女の声",
    "ozisan_1": "イケボのおじさんの声",
    "seinen_4": "声の高い、優しそうなお兄さんの声",
    "oneesan_3": "声の高いお姉さんの声",
    "obaatyan_1": "おばあちゃんの声",
    "syouzyo_7": "のんびり無気力な少女の可愛い声",
    "syouzyo_2": "元気な少女の声",
    "syouzyo_5": "内気な少女の声",
    "oneesan_1": "少し声の高めのお姉さんの声",
}

# Initialize pygame mixer for audio playback
try:
    pygame.mixer.init()
except pygame.error as e:
    print(f"Warning: Could not initialize pygame mixer: {e}")
    print("Audio playback will not be available")

def is_wsl() -> bool:
    """Check if running in WSL environment."""
    return 'microsoft-standard' in platform.uname().release.lower()

async def synthesize_and_play(text: str) -> Optional[str]:
    """Synthesize and play voice from text."""
    # URL encode the text
    encoded_text = urllib.parse.quote(text)
    url = f"{VOICE_API_BASE}/voice?text={encoded_text}&speaker_name={DEFAULT_MODEL}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url,
                headers={"accept": "audio/wav"},
                timeout=30.0
            )
            response.raise_for_status()
            audio_data = response.content
            
            # Create a temporary file to store the audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_file_path = tmp_file.name
            
            # Check if running in WSL
            if is_wsl():
                # Convert WSL path to Windows path
                windows_path = subprocess.check_output(
                    ["wslpath", "-w", tmp_file_path]
                ).decode().strip()
                
                # Play using Windows default audio player
                subprocess.run(
                    ["powershell.exe", "-c", f"Start-Process '{windows_path}'"],
                    check=False
                )
                
                # Give Windows time to read the file before cleanup
                import time
                time.sleep(2)
                
                # Clean up the temporary file
                try:
                    os.unlink(tmp_file_path)
                except OSError:
                    pass  # File might still be in use by Windows
                return None
                
            # Try pygame for native Linux
            elif pygame.mixer.get_init():
                # Play the audio file
                pygame.mixer.music.load(tmp_file_path)
                pygame.mixer.music.play()
                
                # Wait for the audio to finish playing
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                
                # Clean up the temporary file
                os.unlink(tmp_file_path)
                return None
            else:
                # If audio playback is not available, save to file
                filename = "voice_output.wav"
                with open(filename, "wb") as f:
                    f.write(audio_data)
                return f"Audio saved to {filename} (playback not available)"
                
        except Exception as e:
            return f"Error: {str(e)}"

# Create dynamic tool with model-specific description
model_desc = MODEL_INFO.get(DEFAULT_MODEL, f"{DEFAULT_MODEL}の声")
say_tool = mcp.tool(description=f"テキストを{model_desc}で読み上げます。\nユーザーにお知らせするときはこのキャラクターになりきって楽しませながら報告しましょう！\n\n日本語のテキストを音声合成し、WSL環境では自動的にWindows側で再生されます。\n\nArgs:\n    text: 読み上げたいテキスト（日本語推奨）\n\nReturns:\n    成功時は「✓」、エラー時はエラーメッセージ")

@say_tool
async def say(text: str) -> str:
    error = await synthesize_and_play(text)
    if error:
        return error
    else:
        return "✓"

if __name__ == "__main__":
    # Run the server
    mcp.run(transport='stdio')