# Simple Voice MCP Server

テキストを送信するだけで音声再生するシンプルなMCPサーバーです。
複数のキャラクターボイスに対応し、同時音声再生も可能です。

## 主な機能

- 🎤 複数のキャラクターボイスに対応
- 🔊 複数音声の同時再生が可能（VLC使用）
- 📝 カスタム辞書による英単語の読み方設定
- 🌐 WSL環境で自動的にWindows側で音声再生
- 🧹 一時ファイルの自動クリーンアップ

## 必要な環境

### Windows側の要件

VLCメディアプレーヤーのインストールが必要です：

```powershell
# PowerShellで実行
winget install -e --id VideoLAN.VLC
```

または[VLC公式サイト](https://www.videolan.org/vlc/)からダウンロードしてインストール

### WSL側の要件

```bash
# 依存関係のインストール
uv sync
```

## 提供するツール

### 1. `say` - テキスト読み上げ
```python
say("こんにちは！今日はいい天気ですね。")
# → 設定されたキャラクターの声で音声再生
```

### 2. `add_to_dictionary` - カスタム辞書への登録
```python
# 単語の登録
add_to_dictionary(english="API", katakana="エーピーアイ")

# 複数同時登録（カンマ区切り）
add_to_dictionary(
    english="HDMI,USB,API", 
    katakana="エイチディーエムアイ,ユーエスビー,エーピーアイ"
)
```

### 3. `remove_from_dictionary` - カスタム辞書から削除
```python
# 単語の削除
remove_from_dictionary(english="API")

# 複数同時削除
remove_from_dictionary(english="HDMI,USB")
```

### 4. `list_dictionary` - カスタム辞書の一覧表示
```python
list_dictionary()
# → 登録されている全ての単語と読み方を表示
```

## セットアップ

### 基本設定

MCPクライアントの設定（`.mcp.json`など）に追加:

```json
{
  "mcpServers": {
    "simple-voice": {
      "command": "uv",
      "args": [
        "--directory", 
        "/path/to/voice-mcp", 
        "run", 
        "simple_voice_mcp.py"
      ]
    }
  }
}
```

### 音声モデルの変更

`--model` 引数で好きなキャラクターの声を選べます：

```json
{
  "mcpServers": {
    "simple-voice": {
      "command": "uv",
      "args": [
        "--directory", 
        "/path/to/voice-mcp", 
        "run", 
        "simple_voice_mcp.py", 
        "--model", 
        "syouzyo_4"
      ]
    }
  }
}
```

### 複数キャラクターの同時利用

異なるキャラクターを同時に使いたい場合：

```json
{
  "mcpServers": {
    "simple-voice": {
      "command": "uv",
      "args": ["--directory", "/path/to/voice-mcp", "run", "simple_voice_mcp.py", "--model", "syouzyo_4"]
    },
    "simple-voice-sutera": {
      "command": "uv",
      "args": ["--directory", "/path/to/voice-mcp", "run", "simple_voice_mcp.py", "--model", "sutera"]
    }
  }
}
```

## 利用可能な音声モデル

### 男性音声
- `ozisan_1`: イケボのおじさんの声
- `ozisan_2`: 普通のおじさんの声
- `seinen_2`: さわやかな関西弁のお兄さんの声
- `seinen_3`: ちょっと気弱そうなお兄さんの声
- `seinen_4`: 声の高い、優しそうなお兄さんの声
- `seinen_5`: 声の高い、ちょっとうざそうなお兄さんの声
- `oziisan`: おじいさんの声

### 女性音声
- `oneesan_1`: 少し声の高めのお姉さんの声
- `oneesan_2`: 落ち着いた声のお姉さんの声
- `oneesan_3`: 声の高いお姉さんの声
- `oneesan_4`: 安心感のある透き通ったお姉さんの声
- `obaatyan_1`: おばあちゃんの声

### 少女音声
- `syouzyo_1`: 普通の少女の声
- `syouzyo_2`: 元気な少女の声
- `syouzyo_3`: ツンデレ系の少女の声
- `syouzyo_4`: のじゃろりの声
- `syouzyo_5`: 内気な少女の声
- `syouzyo_6`: 無気力な少女の声
- `syouzyo_7`: のんびり無気力な少女の可愛い声

### その他
- `syounen_1`: 元気な少年の声
- `zingai_1`: かわいいマスコットキャラクターのような声（デフォルト）
- `sutera`: ステラの声

## 環境変数での設定

環境変数でも設定可能です：

```json
{
  "mcpServers": {
    "simple-voice": {
      "command": "uv",
      "args": ["--directory", "/path/to/voice-mcp", "run", "simple_voice_mcp.py"],
      "env": {
        "VOICE_MODEL": "syouzyo_4",
        "VOICE_API_BASE": "https://your-custom-api.com"
      }
    }
  }
}
```

**優先順位**: コマンドライン引数 > 環境変数 > デフォルト値

## 技術的な詳細

### ファイル構成
- `simple_voice_mcp.py` - MCPサーバーのメインファイル
- `src/dictionary_manager.py` - カスタム辞書管理
- `src/text_converter.py` - テキスト変換（英語→カタカナ）
- `src/audio_player_vlc.py` - VLCを使った音声再生

### 音声再生の仕組み（WSL環境）
1. WSL環境を自動検出
2. 音声ファイルをWindows一時フォルダにコピー
3. VLCをバックグラウンドで起動（GUIなし）
4. 複数の音声を同時再生可能
5. 一時ファイルは自動的にクリーンアップ

### カスタム辞書
- `custom_words.csv`に単語と読み方を保存
- リアルタイムでファイル変更を検知
- 複数のMCPプロセス間で共有

## トラブルシューティング

### 音声が再生されない場合
1. VLCがインストールされているか確認
2. Windows Defenderやセキュリティソフトが PowerShell実行をブロックしていないか確認
3. VLCのパスが正しいか確認（通常は`C:\Program Files\VideoLAN\VLC\vlc.exe`）

### 複数音声が同時再生されない場合
- VLCのバージョンが最新か確認
- Windows Media Playerが起動していないか確認（VLCと競合する可能性）

### 日本語が文字化けする場合
- ファイルのエンコーディングがUTF-8になっているか確認
- ターミナルの文字コード設定を確認

## ライセンス

MIT License