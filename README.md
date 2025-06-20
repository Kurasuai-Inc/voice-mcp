# Simple Voice MCP Server

テキストを送信するだけで音声再生するシンプルなMCPサーバーです。

## 使い方

1つのツール `say` だけを提供します：
- `say("こんにちは")` → 設定されたキャラクターの声で再生

## セットアップ

### 基本設定

MCPクライアントの設定に追加:

```json
{
  "mcpServers": {
    "simple-voice": {
      "command": "uv",
      "args": ["--directory", "/path/to/voice-mcp", "run", "simple_voice_mcp.py"]
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
      "args": ["--directory", "/path/to/voice-mcp", "run", "simple_voice_mcp.py", "--model", "syouzyo_4"]
    }
  }
}
```

### 利用可能な音声モデル

- **男性音声**: 
  - `ozisan_1`: イケボのおじさんの声
  - `ozisan_2`: 普通のおじさんの声
  - `seinen_2`: さわやかな関西弁のお兄さんの声
  - `seinen_3`: ちょっと気弱そうなお兄さんの声
  - `seinen_4`: 声の高い、優しそうなお兄さんの声
  - `seinen_5`: 声の高い、ちょっとうざそうなお兄さんの声
  - `oziisan`: おじいさんの声

- **女性音声**: 
  - `oneesan_1`: 少し声の高めのお姉さんの声
  - `oneesan_2`: 落ち着いた声のお姉さんの声
  - `oneesan_3`: 声の高いお姉さんの声
  - `oneesan_4`: 安心感のある透き通ったお姉さんの声
  - `obaatyan_1`: おばあちゃんの声

- **少女音声**: 
  - `syouzyo_1`: 普通の少女の声
  - `syouzyo_2`: 元気な少女の声
  - `syouzyo_3`: ツンデレ系の少女の声
  - `syouzyo_4`: のじゃろりの声
  - `syouzyo_5`: 内気な少女の声
  - `syouzyo_6`: 無気力な少女の声
  - `syouzyo_7`: のんびり無気力な少女の可愛い声

- **その他**: 
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

## 特徴

- 最小限のインターフェース（sayコマンドのみ）
- キャラクターになりきって楽しく報告
- WSL環境では自動的にWindows側で音声を再生
- 成功時は「✓」を返すだけのシンプルな応答

## インストール

```bash
# 依存関係のインストール
uv sync
```

## WSL環境での音声再生

**🎉 WSL環境では自動的にWindows側で音声が再生されます！**

追加の設定は不要です。WSL環境を自動検出して、PowerShell経由でWindows側の音声プレーヤーを起動します。

### 動作の仕組み
1. WSL環境を自動検出（`microsoft-standard`をカーネル名で判別）
2. 音声ファイルのWSLパスをWindowsパスに変換（`wslpath -w`使用）
3. PowerShell経由でWindows側のデフォルト音声プレーヤーを起動
4. 一時ファイルは自動的にクリーンアップ

### トラブルシューティング
- 音声が再生されない場合は、Windows側に`.wav`ファイルに関連付けられたプレーヤーがあることを確認してください
- セキュリティソフトがPowerShellの実行をブロックしていないか確認してください