#!/usr/bin/env python
"""Simple voice synthesis MCP server - just send text and it plays."""

import os
import tempfile
from typing import Optional, Dict, List, Tuple
import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import Field
import pygame
import urllib.parse
import subprocess
import platform
import sys
import re
import csv
try:
    import alkana
except ImportError:
    alkana = None

# Global variables for custom dictionary
custom_dict = {}
custom_dict_path = os.path.join(os.path.dirname(__file__), 'custom_words.csv')
custom_dict_mtime = 0  # Track file modification time

def load_custom_dictionary():
    """Load custom dictionary from CSV file."""
    global custom_dict, custom_dict_mtime
    
    if os.path.exists(custom_dict_path):
        try:
            # Check if file has been modified
            current_mtime = os.path.getmtime(custom_dict_path)
            if current_mtime != custom_dict_mtime:
                custom_dict.clear()
                with open(custom_dict_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2:
                            custom_dict[row[0].lower()] = row[1]
                custom_dict_mtime = current_mtime
        except Exception as e:
            print(f"Warning: Could not load custom dictionary: {e}")

# Initial load
load_custom_dictionary()

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

def convert_english_to_katakana(text: str) -> Tuple[str, List[str]]:
    """Convert English words in text to Katakana using alkana.
    
    Returns:
        A tuple of (converted_text, unconverted_words)
    """
    # Reload dictionary to get latest changes
    load_custom_dictionary()
    
    if not alkana:
        return text, []
    
    # Split text into tokens: English words (with optional dots/extensions), Japanese characters, punctuation, whitespace
    # Updated pattern to capture things like ".py", "file.txt", etc.
    tokens = re.findall(r'[A-Za-z]+\.[A-Za-z]+|\.[A-Za-z]+|[A-Za-z]+|[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+|[^\w\s]|\s+', text)
    
    # Post-process to handle cases like "main.py" where ".py" is in dictionary
    processed_tokens = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        # Check if this is a compound like "main.py"
        if re.match(r'^[A-Za-z]+\.[A-Za-z]+$', token):
            # Split into parts
            parts = token.split('.')
            base_word = parts[0]
            extension = '.' + parts[1]
            
            # Check if the full compound is in dictionary
            if token.lower() in custom_dict:
                processed_tokens.append(token)
            # Check if just the extension is in dictionary
            elif extension.lower() in custom_dict:
                # Convert base word and extension separately
                processed_tokens.append(base_word)
                processed_tokens.append(extension)
            else:
                # Keep as is
                processed_tokens.append(token)
        else:
            processed_tokens.append(token)
        i += 1
    
    tokens = processed_tokens
    converted_tokens = []
    unconverted_words = []
    
    for token in tokens:
        # Check if token is English (contains only ASCII letters, possibly with dots)
        if re.match(r'^(\.)?[A-Za-z]+(\.[A-Za-z]+)?$', token):
            token_lower = token.lower()
            # First try custom dictionary
            if token_lower in custom_dict:
                converted_tokens.append(custom_dict[token_lower])
            # Then try alkana
            elif alkana:
                katakana = alkana.get_kana(token_lower)
                if katakana:
                    converted_tokens.append(katakana)
                else:
                    # If not found in any dictionary, keep original and track it
                    converted_tokens.append(token)
                    if token_lower not in unconverted_words:
                        unconverted_words.append(token_lower)
            else:
                # If alkana not available, keep original
                converted_tokens.append(token)
        else:
            # Keep non-English parts as is (Japanese, punctuation, whitespace)
            converted_tokens.append(token)
    
    return ''.join(converted_tokens), unconverted_words

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
say_tool = mcp.tool(description=f"テキストを{model_desc}で読み上げます。\nユーザーにお知らせするときはこのキャラクターになりきって楽しませながら報告しましょう！\n\n日本語のテキストを音声合成し、WSL環境では自動的にWindows側で再生されます。\n英単語が含まれている場合は自動的にカタカナに変換されます。\n\nArgs:\n    text: 読み上げたいテキスト（日本語・英語混在可能）\n\nReturns:\n    成功時は\"✓\"、エラー時はエラーメッセージ")

@say_tool
async def say(text: str) -> str:
    # Convert English words to Katakana before synthesis
    converted_text, unconverted_words = convert_english_to_katakana(text)
    error = await synthesize_and_play(converted_text)
    if error:
        return error
    else:
        if unconverted_words:
            return f"✓ (未変換の英単語: {', '.join(unconverted_words)})"
        else:
            return "✓"

@mcp.tool(description="カスタム辞書に新しい英単語とカタカナ読みのペアを登録します。HDMIやAPIなどの略語や、.pyのような拡張子も登録できます。")
def add_to_dictionary(
    english: str = Field(description="英単語、略語、または拡張子（例: hdmi, api, csv, .py, .csv）"),
    katakana: str = Field(description="カタカナ読み（例: エイチディーエムアイ, エーピーアイ, シーエスブイ, ドットパイ, ドットシーエスブイ）")
) -> str:
    """
    カスタム辞書に新しいエントリを追加します。
    
    ファイル名を正しく読み上げるために、以下のような登録を推奨します：
    - 拡張子単体: ".py" → "ドットパイ", ".csv" → "ドットシーエスブイ"
    - 略語: "csv" → "シーエスブイ", "api" → "エーピーアイ"
    
    例: "custom_words.csv"を正しく読むには：
    1. add_to_dictionary("csv", "シーエスブイ")
    2. add_to_dictionary(".csv", "ドットシーエスブイ")
    
    Args:
        english: 英単語、略語、または拡張子（小文字で保存されます）
        katakana: カタカナでの読み方
        
    Returns:
        成功時は登録完了メッセージ、エラー時はエラーメッセージ
    """
    try:
        # Validate inputs
        if not english or not katakana:
            return "エラー: 英単語とカタカナの両方を指定してください"
        
        # Convert to lowercase for consistency
        english_lower = english.lower()
        
        # Update in-memory dictionary
        custom_dict[english_lower] = katakana
        
        # Read existing entries
        existing_entries = []
        custom_dict_path = os.path.join(os.path.dirname(__file__), 'custom_words.csv')
        
        if os.path.exists(custom_dict_path):
            with open(custom_dict_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                existing_entries = list(reader)
        
        # Check if entry already exists and update it
        entry_updated = False
        for i, row in enumerate(existing_entries):
            if len(row) >= 2 and row[0].lower() == english_lower:
                existing_entries[i] = [english_lower, katakana]
                entry_updated = True
                break
        
        # Add new entry if not updating
        if not entry_updated:
            existing_entries.append([english_lower, katakana])
        
        # Sort entries for better readability
        existing_entries.sort(key=lambda x: x[0] if x else '')
        
        # Write back to file
        with open(custom_dict_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(existing_entries)
        
        if entry_updated:
            return f"✓ 辞書を更新しました: {english_lower} → {katakana}"
        else:
            return f"✓ 辞書に登録しました: {english_lower} → {katakana}"
            
    except Exception as e:
        return f"エラー: 辞書への登録に失敗しました - {str(e)}"


@mcp.tool(description="カスタム辞書から指定した英単語のエントリを削除します。")
def remove_from_dictionary(
    english: str = Field(description="削除する英単語（例: hdmi, api, .py）")
) -> str:
    """
    カスタム辞書から指定したエントリを削除します。
    
    Args:
        english: 削除する英単語
        
    Returns:
        成功時は削除完了メッセージ、エラー時はエラーメッセージ
    """
    try:
        english_lower = english.lower()
        
        # Remove from in-memory dictionary
        if english_lower in custom_dict:
            del custom_dict[english_lower]
        else:
            return f"エラー: '{english}' は辞書に登録されていません"
        
        # Read and update file
        custom_dict_path = os.path.join(os.path.dirname(__file__), 'custom_words.csv')
        existing_entries = []
        
        if os.path.exists(custom_dict_path):
            with open(custom_dict_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2 and row[0].lower() != english_lower:
                        existing_entries.append(row)
        
        # Write back to file
        with open(custom_dict_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(existing_entries)
        
        return f"✓ 辞書から削除しました: {english_lower}"
        
    except Exception as e:
        return f"エラー: 辞書からの削除に失敗しました - {str(e)}"


@mcp.tool(description="カスタム辞書に登録されているすべての英単語と読み方を表示します。")
def list_dictionary() -> str:
    """
    カスタム辞書の全エントリを一覧表示します。
    
    Returns:
        辞書エントリの一覧、または空の場合はその旨のメッセージ
    """
    try:
        if not custom_dict:
            return "辞書は空です"
        
        # Sort entries for display
        sorted_entries = sorted(custom_dict.items())
        
        # Format as a nice list
        result = "カスタム辞書の内容:\n\n"
        for english, katakana in sorted_entries:
            result += f"  {english} → {katakana}\n"
        
        result += f"\n合計: {len(sorted_entries)} エントリ"
        return result
        
    except Exception as e:
        return f"エラー: 辞書の読み込みに失敗しました - {str(e)}"


if __name__ == "__main__":
    # Run the server
    mcp.run(transport='stdio')