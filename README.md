# PDF to Video Generator 🎬

PDFプレゼンテーションから自動でナレーション付き動画を生成します。

## デモ

```
PDF (5ページ) → 音声合成 → 字幕付き動画 (3分)
```

## 特徴

- 📄 **PDF自動読み込み** - 各ページを画像として抽出
- 🎤 **日本語音声合成** - VOICEVOX による自然な読み上げ
- 📝 **字幕同期** - 音声に合わせて1行ずつ表示
- 🎨 **自動レイアウト** - 16:9動画に最適化

## 必要条件

- Python 3.10+
- [VOICEVOX Engine](https://voicevox.hiroshiba.jp/) (音声合成)
- [FFmpeg](https://ffmpeg.org/) (動画処理)

## インストール

```bash
git clone https://github.com/YOUR_USERNAME/pdf-to-video.git
cd pdf-to-video
pip install -r requirements.txt
```

## 使い方

### 1. VOICEVOXエンジンを起動

```bash
# Windows
voicevox_engine\run.exe

# Mac/Linux
./voicevox_engine/run
```

### 2. 動画生成

```bash
python pdf_to_video.py input.pdf output.mp4
```

### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--speaker <id>` | VOICEVOXスピーカーID | 3 (ずんだもん) |

### スピーカーID一覧

| ID | 名前 |
|----|------|
| 0 | 四国めたん (あまあま) |
| 2 | 四国めたん (ノーマル) |
| 3 | ずんだもん (ノーマル) |
| 8 | 春日部つむぎ |
| 13 | 青山龍星 (男性) |

## 出力仕様

- 解像度: 1920x1080 (16:9)
- 形式: MP4 (H.264 + AAC)
- 字幕: 画像に焼き込み

## 仕組み

```
PDF
 ↓ PyMuPDF
ページ画像 + テキスト抽出
 ↓
フレーズ分割 (約30文字ごと)
 ↓ VOICEVOX
各フレーズの音声生成
 ↓ Pillow
字幕付き画像生成
 ↓ FFmpeg
動画クリップ作成 → 結合
 ↓
完成動画 🎉
```

## ライセンス

MIT License

## 謝辞

- [VOICEVOX](https://voicevox.hiroshiba.jp/) - 無料の音声合成エンジン
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF処理ライブラリ
- [FFmpeg](https://ffmpeg.org/) - 動画処理ツール
