"""
PDF to Video Generator v3 - 1文ずつ字幕表示版
=============================================
各文の音声再生中にその字幕だけを表示
"""

import os
import sys
import re
import subprocess
import tempfile
import shutil
from dataclasses import dataclass, field

import fitz  # PyMuPDF
import requests
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# 設定
# ============================================================

VOICEVOX_URL = "http://127.0.0.1:50021"
SPEAKER_ID = 3
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FONT_SIZE = 36
SUBTITLE_Y = VIDEO_HEIGHT - 80  # 字幕Y位置


@dataclass
class Sentence:
    text: str
    audio_path: str = ""
    duration: float = 0.0


@dataclass
class PageContent:
    page_num: int
    image_path: str
    resized_path: str = ""
    text: str = ""
    sentences: list[Sentence] = field(default_factory=list)


# ============================================================
# ユーティリティ
# ============================================================

def get_font(size: int):
    """日本語フォントを取得"""
    font_paths = [
        "C:/Windows/Fonts/meiryo.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    return ImageFont.load_default()


def check_voicevox():
    try:
        r = requests.get(f"{VOICEVOX_URL}/version", timeout=5)
        return r.status_code == 200
    except:
        return False


def generate_audio(text: str, output_path: str, speaker_id: int) -> float:
    """音声生成、長さを返す"""
    params = {"text": text, "speaker": speaker_id}
    r = requests.post(f"{VOICEVOX_URL}/audio_query", params=params)
    query = r.json()
    
    r = requests.post(
        f"{VOICEVOX_URL}/synthesis",
        params={"speaker": speaker_id},
        json=query
    )
    
    with open(output_path, "wb") as f:
        f.write(r.content)
    
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", output_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


# ============================================================
# PDF処理
# ============================================================

def extract_pdf_pages(pdf_path: str, output_dir: str) -> list[PageContent]:
    pages = []
    doc = fitz.open(pdf_path)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        image_path = os.path.join(output_dir, f"page_{page_num:03d}.png")
        pix.save(image_path)
        text = page.get_text().strip()
        
        pages.append(PageContent(
            page_num=page_num,
            image_path=image_path,
            text=text
        ))
        print(f"  Page {page_num + 1}/{len(doc)}")
    
    doc.close()
    return pages


def resize_image(image_path: str, output_path: str):
    """動画サイズにリサイズ"""
    img = Image.open(image_path)
    img_ratio = img.width / img.height
    video_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    
    if img_ratio > video_ratio:
        new_width = VIDEO_WIDTH
        new_height = int(VIDEO_WIDTH / img_ratio)
    else:
        new_height = VIDEO_HEIGHT
        new_width = int(VIDEO_HEIGHT * img_ratio)
    
    img = img.resize((new_width, new_height), Image.LANCZOS)
    background = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    offset = ((VIDEO_WIDTH - new_width) // 2, (VIDEO_HEIGHT - new_height) // 2)
    background.paste(img, offset)
    background.save(output_path)
    return output_path


# ============================================================
# スクリプト生成
# ============================================================

def split_into_phrases(text: str, max_chars: int = 25) -> list[str]:
    """テキストを短いフレーズに分割（1行表示用）"""
    # まず句読点で分割
    parts = re.split(r'([。、！？])', text)
    
    phrases = []
    current = ""
    
    for i, part in enumerate(parts):
        if not part:
            continue
        
        # 句読点の場合は前のテキストに追加
        if part in '。、！？':
            current += part
            if len(current) >= max_chars or part in '。！？':
                if current.strip():
                    phrases.append(current.strip())
                current = ""
        else:
            # 通常のテキスト
            if len(current) + len(part) > max_chars and current:
                if current.strip():
                    phrases.append(current.strip())
                current = part
            else:
                current += part
    
    if current.strip():
        phrases.append(current.strip())
    
    # 空のフレーズを除去、長すぎるものは分割
    result = []
    for phrase in phrases:
        if len(phrase) > max_chars * 2:
            # 強制的に分割
            for j in range(0, len(phrase), max_chars):
                chunk = phrase[j:j+max_chars]
                if chunk.strip():
                    result.append(chunk.strip())
        elif phrase.strip():
            result.append(phrase.strip())
    
    return result


def generate_scripts(pages: list[PageContent]) -> list[PageContent]:
    for i, page in enumerate(pages):
        if page.text:
            text = page.text[:400] if len(page.text) > 400 else page.text
            script = f"このページでは、{text}について説明します。"
        else:
            script = f"こちらは{page.page_num + 1}ページ目になります。"
        
        # 短いフレーズに分割
        phrases = split_into_phrases(script, max_chars=30)
        page.sentences = [Sentence(text=p) for p in phrases if p]
        print(f"  Page {i + 1}: {len(page.sentences)} phrases")
    
    return pages


# ============================================================
# 字幕付き画像生成
# ============================================================

def create_image_with_subtitle(base_image_path: str, subtitle_text: str, output_path: str):
    """画像に字幕を焼き込み（1行のみ、中央下に表示）"""
    img = Image.open(base_image_path).copy()
    draw = ImageDraw.Draw(img)
    font = get_font(FONT_SIZE)
    
    # テキストサイズ計算
    bbox = draw.textbbox((0, 0), subtitle_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 中央下に配置
    x = (VIDEO_WIDTH - text_width) // 2
    y = SUBTITLE_Y - text_height // 2
    
    # 背景（半透明黒）
    padding = 12
    bg_box = [x - padding, y - padding, x + text_width + padding, y + text_height + padding]
    
    # 半透明背景を描画
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(bg_box, fill=(0, 0, 0, 180))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    
    # テキスト描画
    draw = ImageDraw.Draw(img)
    # アウトライン
    for dx, dy in [(-2, -2), (-2, 2), (2, -2), (2, 2), (-2, 0), (2, 0), (0, -2), (0, 2)]:
        draw.text((x + dx, y + dy), subtitle_text, font=font, fill=(0, 0, 0))
    # メインテキスト
    draw.text((x, y), subtitle_text, font=font, fill=(255, 255, 255))
    
    img.save(output_path)
    return output_path


# ============================================================
# 動画生成
# ============================================================

def create_video(pages: list[PageContent], output_path: str, temp_dir: str):
    """各文ごとにクリップを作成して結合"""
    
    # 1. 画像リサイズ
    print("  Resizing images...")
    for page in pages:
        resized = os.path.join(temp_dir, f"resized_{page.page_num:03d}.png")
        resize_image(page.image_path, resized)
        page.resized_path = resized
    
    # 2. 各文ごとにクリップ作成
    print("  Creating clips per sentence...")
    all_clips = []
    clip_idx = 0
    
    for page in pages:
        for j, sentence in enumerate(page.sentences):
            # 字幕付き画像を作成
            subtitle_img = os.path.join(temp_dir, f"subtitle_{clip_idx:04d}.png")
            create_image_with_subtitle(page.resized_path, sentence.text, subtitle_img)
            
            # 音声生成
            audio_path = os.path.join(temp_dir, f"audio_{clip_idx:04d}.wav")
            duration = generate_audio(sentence.text, audio_path, SPEAKER_ID)
            sentence.audio_path = audio_path
            sentence.duration = duration
            
            # 動画クリップ作成
            clip_path = os.path.join(temp_dir, f"clip_{clip_idx:04d}.mp4")
            subprocess.run([
                "ffmpeg", "-y",
                "-loop", "1", "-i", subtitle_img,
                "-i", audio_path,
                "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p", "-shortest",
                clip_path
            ], capture_output=True)
            
            all_clips.append(clip_path)
            clip_idx += 1
            print(f"    Clip {clip_idx}: {sentence.text[:30]}... ({duration:.1f}s)")
    
    # 3. 全クリップ結合
    print("  Concatenating all clips...")
    concat_file = os.path.join(temp_dir, "concat.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for clip in all_clips:
            f.write(f"file '{clip}'\n")
    
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path
    ], capture_output=True)
    
    print(f"  Done: {output_path}")


# ============================================================
# メイン
# ============================================================

def main():
    if len(sys.argv) < 3:
        print("Usage: python pdf_to_video_v3.py <input.pdf> <output.mp4>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2]
    
    global SPEAKER_ID
    if "--speaker" in sys.argv:
        idx = sys.argv.index("--speaker")
        SPEAKER_ID = int(sys.argv[idx + 1])
    
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found")
        sys.exit(1)
    
    print("[1/4] Checking VOICEVOX...")
    if not check_voicevox():
        print("Error: VOICEVOX not running")
        sys.exit(1)
    print("  OK")
    
    temp_dir = tempfile.mkdtemp(prefix="pdf_to_video_")
    print(f"  Temp: {temp_dir}")
    
    try:
        print(f"\n[2/4] Extracting PDF...")
        pages = extract_pdf_pages(pdf_path, temp_dir)
        
        print("\n[3/4] Generating scripts...")
        pages = generate_scripts(pages)
        
        print("\n[4/4] Creating video...")
        create_video(pages, output_path, temp_dir)
        
        # 合計時間計算
        total = sum(s.duration for p in pages for s in p.sentences)
        
        print("\n" + "=" * 50)
        print("Complete!")
        print(f"Output: {output_path}")
        print(f"Duration: {total:.1f}s")
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
