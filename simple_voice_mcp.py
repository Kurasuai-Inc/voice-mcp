#!/usr/bin/env python
"""Simple voice synthesis MCP server - just send text and it plays."""

import os
import sys
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# Import our modules
from src.dictionary_manager import DictionaryManager
from src.text_converter import TextConverter
from src.audio_player_vlc import synthesize_and_play  # Use VLC for multiple simultaneous playback

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

# Initialize managers
dict_path = os.path.join(os.path.dirname(__file__), 'custom_words.csv')
dict_manager = DictionaryManager(dict_path)
text_converter = TextConverter(dict_manager)

# Create dynamic tool with model-specific description
model_desc = MODEL_INFO.get(DEFAULT_MODEL, f"{DEFAULT_MODEL}の声")
say_tool = mcp.tool(
    description=f"テキストを{model_desc}で読み上げます。\n"
    f"ユーザーにお知らせするときはこのキャラクターになりきって楽しませながら報告しましょう！\n\n"
    f"日本語のテキストを音声合成し、WSL環境では自動的にWindows側で再生されます。\n"
    f"英単語が含まれている場合は自動的にカタカナに変換されます。\n\n"
    f"Args:\n    text: 読み上げたいテキスト（日本語・英語混在可能）\n\n"
    f"Returns:\n    成功時は\"✓\"、エラー時はエラーメッセージ"
)

@say_tool
async def say(text: str) -> str:
    """Say the given text using voice synthesis."""
    try:
        print(f"[DEBUG] Say called with: {text}")
        
        # Convert text to katakana
        converted_text, unconverted_words = text_converter.convert_to_katakana(text)
        print(f"[DEBUG] Converted text: {converted_text}")
        
        # Synthesize and play
        error = await synthesize_and_play(converted_text, VOICE_API_BASE, DEFAULT_MODEL)
        print(f"[DEBUG] Synthesis result: {error}")
        
        if error:
            return f"Error: {error}"
        else:
            if unconverted_words:
                return f"✓ (未変換の英単語: {', '.join(unconverted_words)})"
            else:
                return "✓"
    except Exception as e:
        print(f"[ERROR] Exception in say: {e}")
        import traceback
        traceback.print_exc()
        return f"Exception: {str(e)}"


@mcp.tool(description="カスタム辞書に新しい英単語とカタカナ読みのペアを登録します。HDMIやAPIなどの略語や、.pyのような拡張子も登録できます。複数登録する場合はカンマ区切りで指定できます。")
def add_to_dictionary(
    english: str = Field(description="英単語、略語、または拡張子。複数の場合はカンマ区切り（例: hdmi,api,csv,.py,.csv または 1つ,2つ,3つ）"),
    katakana: str = Field(description="カタカナ読み。複数の場合はカンマ区切り（例: エイチディーエムアイ,エーピーアイ,シーエスブイ,ドットパイ,ドットシーエスブイ または ひとつ,ふたつ,みっつ）")
) -> str:
    """
    カスタム辞書に新しいエントリを追加します。
    
    単一登録:
        add_to_dictionary("api", "エーピーアイ")
    
    複数登録:
        add_to_dictionary("1つ,2つ,3つ", "ひとつ,ふたつ,みっつ")
    
    ファイル名を正しく読み上げるために、以下のような登録を推奨します：
    - 拡張子単体: ".py" → "ドットパイ", ".csv" → "ドットシーエスブイ"
    - 略語: "csv" → "シーエスブイ", "api" → "エーピーアイ"
    - 数字付き: "2つ" → "ふたつ", "3個" → "さんこ"
    
    Args:
        english: 英単語、略語、または拡張子（小文字で保存されます）
        katakana: カタカナでの読み方
        
    Returns:
        成功時は登録完了メッセージ、エラー時はエラーメッセージ
    """
    # カンマで分割（前後の空白を削除）
    english_list = [e.strip() for e in english.split(',')]
    katakana_list = [k.strip() for k in katakana.split(',')]
    
    # 個数が一致しない場合はエラー
    if len(english_list) != len(katakana_list):
        return f"エラー: 英単語の数({len(english_list)})とカタカナの数({len(katakana_list)})が一致しません"
    
    # 単一の場合
    if len(english_list) == 1:
        success, message = dict_manager.add_entry(english_list[0], katakana_list[0])
        return message
    
    # 複数の場合
    results = []
    success_count = 0
    for eng, kana in zip(english_list, katakana_list):
        success, message = dict_manager.add_entry(eng, kana)
        if success:
            success_count += 1
            results.append(f"✓ {eng} → {kana}")
        else:
            results.append(f"✗ {eng}: {message}")
    
    summary = f"\n登録完了: {success_count}/{len(english_list)}件成功"
    return "\n".join(results) + "\n" + summary


@mcp.tool(description="カスタム辞書から指定した英単語のエントリを削除します。複数削除する場合はカンマ区切りで指定できます。")
def remove_from_dictionary(
    english: str = Field(description="削除する英単語。複数の場合はカンマ区切り（例: hdmi,api,.py または test,1つ,2つ）")
) -> str:
    """
    カスタム辞書から指定したエントリを削除します。
    
    単一削除:
        remove_from_dictionary("api")
    
    複数削除:
        remove_from_dictionary("test,1つ,2つ")
    
    Args:
        english: 削除する英単語
        
    Returns:
        成功時は削除完了メッセージ、エラー時はエラーメッセージ
    """
    # カンマで分割（前後の空白を削除）
    english_list = [e.strip() for e in english.split(',')]
    
    # 単一の場合
    if len(english_list) == 1:
        success, message = dict_manager.remove_entry(english_list[0])
        return message
    
    # 複数の場合
    results = []
    success_count = 0
    for eng in english_list:
        success, message = dict_manager.remove_entry(eng)
        if success:
            success_count += 1
            results.append(f"✓ {eng} を削除")
        else:
            results.append(f"✗ {eng}: {message}")
    
    summary = f"\n削除完了: {success_count}/{len(english_list)}件成功"
    return "\n".join(results) + "\n" + summary


@mcp.tool(description="カスタム辞書に登録されているすべての英単語と読み方を表示します。")
def list_dictionary() -> str:
    """
    カスタム辞書の全エントリを一覧表示します。
    
    Returns:
        辞書エントリの一覧、または空の場合はその旨のメッセージ
    """
    return dict_manager.list_entries()


if __name__ == "__main__":
    # Run the server
    mcp.run(transport='stdio')