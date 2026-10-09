import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, ImageClip, vfx,
    concatenate_audioclips, CompositeAudioClip
)
from config.settings import OUTPUT_DIR

os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"

# Cari path font di Windows, fallback ke Arial Bold lalu Arial biasa
IMPACT_FONT_PATH = r"C:\Windows\Fonts\impact.ttf"
BOLD_FONT_PATH = r"C:\Windows\Fonts\arialbd.ttf"
DEFAULT_FONT_PATH = (
    IMPACT_FONT_PATH if os.path.exists(IMPACT_FONT_PATH)
    else BOLD_FONT_PATH if os.path.exists(BOLD_FONT_PATH)
    else r"C:\Windows\Fonts\arial.ttf"
)

VIDEO_W, VIDEO_H = 1080, 1920
TRANSITION_DURATION = 0.6


# ============================================================
# 1. COLOR GRADING & LOOK SINEMATIK
# ============================================================

def apply_color_grade(image_clip, contrast=1.12, saturation=1.15, temperature=6):
    def filter_frame(get_frame, t):
        frame = get_frame(t).astype(np.float32)
        frame = (frame - 127.5) * contrast + 127.5

        gray = frame.mean(axis=2, keepdims=True)
        frame = gray + (frame - gray) * saturation

        frame[:, :, 0] += temperature       # naikkan channel merah
        frame[:, :, 2] -= temperature * 0.5  # turunkan channel biru sedikit

        return np.clip(frame, 0, 255).astype(np.uint8)
    return image_clip.transform(filter_frame)


def apply_vignette(image_clip, strength=0.45):
    w, h = image_clip.size
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    max_dist = np.sqrt(cx ** 2 + cy ** 2)
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_dist
    mask = np.clip(1 - strength * (dist ** 2), 0, 1)[:, :, None]

    def filter_frame(get_frame, t):
        frame = get_frame(t).astype(np.float32)
        return np.clip(frame * mask, 0, 255).astype(np.uint8)
    return image_clip.transform(filter_frame)


def apply_dark_overlay(image_clip, opacity=0.35):
    def filter_frame(get_frame, t):
        frame = get_frame(t).astype(float)
        return (frame * (1.0 - opacity)).astype(np.uint8)
    return image_clip.transform(filter_frame)


# ============================================================
# 2. MOTION GRAPHIC: KEN BURNS DENGAN VARIASI ARAH
# ============================================================

def make_ken_burns(clip, duration, zoom_range=(1.0, 1.18), direction=None):
    import cv2
    w, h = clip.size
    directions = ["in-center", "in-topleft", "in-bottomright", "out-center", "pan-left", "pan-right"]
    direction = direction or random.choice(directions)

    z_start, z_end = zoom_range
    if direction.startswith("out"):
        z_start, z_end = z_end, z_start

    def effect(get_frame, t):
        progress = min(1.0, t / max(duration, 0.001))
        scale = z_start + (z_end - z_start) * progress

        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(get_frame(t), (new_w, new_h))

        max_off_x, max_off_y = new_w - w, new_h - h

        if direction in ("in-center", "out-center"):
            off_x, off_y = max_off_x // 2, max_off_y // 2
        elif direction == "in-topleft":
            off_x, off_y = int(max_off_x * 0.15), int(max_off_y * 0.15)
        elif direction == "in-bottomright":
            off_x, off_y = int(max_off_x * 0.85), int(max_off_y * 0.85)
        elif direction == "pan-left":
            off_x, off_y = int(max_off_x * (1 - progress)), max_off_y // 2
        else:  # pan-right
            off_x, off_y = int(max_off_x * progress), max_off_y // 2

        off_x = max(0, min(off_x, max_off_x))
        off_y = max(0, min(off_y, max_off_y))
        return resized[off_y:off_y + h, off_x:off_x + w]
    return clip.transform(effect)


# ============================================================
# 3. SUBTITLE & BRANDING ASSETS
# ============================================================

def group_words_into_phrases(word_subtitles, max_words=3):
    """
    Mengelompokkan word-level timestamps menjadi frasa pendek (3 kata)
    agar alur subtitle lebih mudah dibaca.
    """
    if not word_subtitles:
        return []

    phrases = []
    current_words = []

    for item in word_subtitles:
        current_words.append(item)
        if len(current_words) >= max_words:
            words_str = [w.get("text", w.get("word", "")) if isinstance(w, dict) else str(w) for w in current_words]
            phrase_text = " ".join(words_str)
            start_time = current_words[0]["start"] if isinstance(current_words[0], dict) else current_words[0][1]
            end_time = current_words[-1]["end"] if isinstance(current_words[-1], dict) else current_words[-1][2]

            phrases.append({
                "word": phrase_text,
                "start": start_time,
                "end": end_time,
                "highlight": False
            })
            current_words = []

    if current_words:
        words_str = [w.get("text", w.get("word", "")) if isinstance(w, dict) else str(w) for w in current_words]
        phrase_text = " ".join(words_str)
        start_time = current_words[0]["start"] if isinstance(current_words[0], dict) else current_words[0][1]
        end_time = current_words[-1]["end"] if isinstance(current_words[-1], dict) else current_words[-1][2]

        phrases.append({
            "word": phrase_text,
            "start": start_time,
            "end": end_time,
            "highlight": False
        })

    return phrases


def _render_word_image(text, font_path, font_size, color, stroke_color, stroke_width, highlight=False):
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = font.getbbox(text, stroke_width=stroke_width)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    padding_x, padding_y = 35, 15
    canvas_w = int(text_w + (stroke_width * 2) + (padding_x * 2))
    canvas_h = int(text_h + (stroke_width * 2) + (padding_y * 2))

    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    box_fill = (255, 59, 59, 195) if highlight else (0, 0, 0, 160)
    draw.rounded_rectangle(
        [(stroke_width, stroke_width), (canvas_w - stroke_width, canvas_h - stroke_width)],
        radius=18, fill=box_fill
    )

    draw.text(
        (canvas_w / 2, canvas_h / 2), text, font=font,
        fill=color, stroke_width=stroke_width, stroke_fill=stroke_color, anchor="mm"
    )
    return np.array(img)


def create_subtitle_clip(text, font_path, font_size=75, color='#FFE600', stroke_color='black',
                          stroke_width=6, start_time=0, duration=1.0, pos=('center', 1300),
                          highlight=False, pop_in=True):
    import cv2
    img_np = _render_word_image(text, font_path, font_size, color, stroke_color, stroke_width, highlight)
    base_frame = img_np
    h, w = base_frame.shape[:2]
    pop_duration = 0.12 if pop_in else 0

    def scale_pop(get_frame, t):
        frame = base_frame
        if pop_duration and t < pop_duration:
            scale = 0.6 + 0.4 * (t / pop_duration)
        else:
            scale = 1.0

        new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        canvas = np.zeros((h, w, 4), dtype=np.uint8)
        off_x, off_y = (w - new_w) // 2, (h - new_h) // 2
        canvas[off_y:off_y + new_h, off_x:off_x + new_w] = resized
        return canvas

    clip = (ImageClip(base_frame)
            .with_duration(duration)
            .transform(scale_pop))

    return clip.with_position(pos).with_start(start_time).with_duration(duration)


def create_watermark(logo_path, duration, target_width=140, opacity=0.85):
    """Membuat watermark logo di pojok kanan atas dari file PNG/JPG."""
    if not os.path.exists(logo_path):
        return None
    
    img = Image.open(logo_path).convert("RGBA")
    aspect = img.height / img.width
    new_h = int(target_width * aspect)
    img = img.resize((target_width, new_h), Image.LANCZOS)
    
    r, g, b, alpha = img.split()
    alpha = alpha.point(lambda p: int(p * opacity))
    img.putalpha(alpha)
    
    base_frame = np.array(img)
    clip = ImageClip(base_frame).with_duration(duration)
    
    x_pos = VIDEO_W - target_width - 40
    y_pos = 50
    return clip.with_position((x_pos, y_pos))


# ============================================================
# 4. ELEMEN INFOGRAFIS & CARD
# ============================================================

def create_progress_bar(total_duration, width=VIDEO_W, height=14):
    def make_frame(t):
        img = Image.new("RGB", (width, height), (40, 40, 40))
        draw = ImageDraw.Draw(img)
        progress = min(1.0, t / total_duration)
        draw.rectangle([0, 0, int(width * progress), height], fill=(255, 200, 0))
        return np.array(img)

    return (ImageClip(np.zeros((height, width, 3), dtype=np.uint8))
            .with_duration(total_duration)
            .transform(lambda gf, t: make_frame(t))
            .with_position(("center", VIDEO_H - height - 8)))


def create_lower_third(title, subtitle="", start_time=0, duration=3.0, font_path=DEFAULT_FONT_PATH, accent_color="#FFE600"):
    canvas_w, canvas_h = 900, 220
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype(font_path, 48)
        sub_font = ImageFont.truetype(font_path, 30)
    except Exception:
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()

    draw.rounded_rectangle([(0, 20), (canvas_w - 40, canvas_h - 20)], radius=12, fill=(0, 0, 0, 150))
    draw.rectangle([(0, 20), (10, canvas_h - 20)], fill=accent_color)
    draw.text((35, 55), title, font=title_font, fill="white")
    if subtitle:
        draw.text((35, 115), subtitle, font=sub_font, fill=accent_color)

    base_frame = np.array(img)
    slide_time = 0.4

    def slide_in(get_frame, t):
        frame = base_frame
        if t < slide_time:
            progress = t / slide_time
            shift = int((1 - progress) * canvas_w)
            canvas = np.zeros_like(frame)
            if shift < canvas_w:
                canvas[:, shift:] = frame[:, :canvas_w - shift]
            return canvas
        return frame

    clip = ImageClip(base_frame).with_duration(duration).transform(slide_in)
    return clip.with_position((40, VIDEO_H - 500)).with_start(start_time)


def create_title_card(text, duration=2.0, font_path=DEFAULT_FONT_PATH, font_size=110):
    img = Image.new("RGBA", (VIDEO_W, VIDEO_H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    words, lines, current = text.split(), [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] > VIDEO_W - 160 and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    total_h = len(lines) * (font_size + 20)
    y = (VIDEO_H - total_h) / 2
    for line in lines:
        draw.text((VIDEO_W / 2, y), line, font=font, fill="white",
                   stroke_width=4, stroke_fill="black", anchor="ma")
        y += font_size + 20

    base_frame = np.array(img)
    fade_time = 0.5

    def fade(get_frame, t):
        frame = base_frame.astype(np.float32)
        if t < fade_time:
            alpha = t / fade_time
        elif t > duration - fade_time:
            alpha = max(0.0, (duration - t) / fade_time)
        else:
            alpha = 1.0
        return (frame * alpha).astype(np.uint8)

    return ImageClip(base_frame).with_duration(duration).transform(fade)


def _cover_resize(path, target_w, target_h):
    img = Image.open(path).convert("RGB")
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(src_w * scale) + 1, int(src_h * scale) + 1
    img = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    return np.array(img)


# ============================================================
# HELPER PARSER SUBTITLE (SAFE DICT / TUPLE READ)
# ============================================================

def _parse_subtitle_item(item):
    """Mencegah TypeError/IndexError saat tipe data item berupa dict atau tuple/list."""
    word = ""
    start = 0.0
    end = 0.0
    highlight = False

    if isinstance(item, dict):
        word = str(item.get('word', item.get('text', ''))).strip().upper()
        start = float(item.get('start', 0.0))
        end = float(item.get('end', start + 0.3))
        highlight = bool(item.get('highlight', False))
    elif isinstance(item, (tuple, list)):
        if len(item) >= 3:
            if isinstance(item[0], str):
                word = str(item[0]).strip().upper()
                start = float(item[1])
                end = float(item[2])
            else:
                start = float(item[0])
                end = float(item[1])
                word = str(item[2]).strip().upper()
        elif len(item) == 2:
            if isinstance(item[0], str):
                word = str(item[0]).strip().upper()
                start = float(item[1])
                end = start + 0.3
            else:
                start = float(item[0])
                end = float(item[1])
                word = ""
        elif len(item) == 1:
            word = str(item[0]).strip().upper()
            start = 0.0
            end = 0.3

    return word, start, end, highlight


# ============================================================
# 5. RENDER FINAL
# ============================================================

def render_video(word_subtitles, audio_path, bg_paths, output_filename="final_shorts.mp4",
                  title_text=None, outro_text=None, logo_path=None, 
                  lower_thirds=None, add_progress_bar=True, bg_music_path=None):
    """
    Render video Shorts dengan Voiceover + AI BGM, Title Card, Watermark & Subtitle Pop-In.
    """
    print("🎬 Rendering High-Quality Professional Shorts Video...")

    # 1. Load Voiceover Utama
    voice_audio = AudioFileClip(audio_path)
    total_duration = voice_audio.duration
    audio_layers = [voice_audio]

    # 2. Mix dengan Backsound jika ada (Diperbaiki untuk MoviePy v2)
    if bg_music_path and os.path.exists(bg_music_path):
        try:
            bg_music = AudioFileClip(bg_music_path).with_volume_scaled(0.08) # Volume tipis 8%
            
            if bg_music.duration < total_duration:
                loops_needed = int(total_duration // bg_music.duration) + 1
                bg_music = concatenate_audioclips([bg_music] * loops_needed)
                
            bg_music = bg_music.subclipped(0, total_duration)
            audio_layers.append(bg_music)
            print(f"🎵 Backsound ditambahkan dari: {bg_music_path}")
        except Exception as e:
            print(f"⚠️ Gagal memuat BGM, lanjut tanpa BGM: {e}")

    # Gabungkan layer audio
    final_audio = CompositeAudioClip(audio_layers)

    # --- BACKGROUND COMPOSITING ---
    clips = []
    n = len(bg_paths) if bg_paths else 1

    overlap_total = (n - 1) * TRANSITION_DURATION if n > 1 else 0
    clip_duration = ((total_duration + overlap_total) / n) if bg_paths else total_duration

    for idx, path in enumerate(bg_paths):
        img_clip = (ImageClip(_cover_resize(path, VIDEO_W, VIDEO_H))
                    .with_duration(clip_duration))

        try:
            motion_clip = make_ken_burns(img_clip, clip_duration)
        except Exception:
            motion_clip = img_clip

        graded = apply_color_grade(motion_clip)
        vignetted = apply_vignette(graded)
        dark_clip = apply_dark_overlay(vignetted, opacity=0.30)

        if 0 < idx < len(bg_paths):
            dark_clip = dark_clip.with_effects([vfx.CrossFadeIn(TRANSITION_DURATION)])
        if idx < len(bg_paths) - 1:
            dark_clip = dark_clip.with_effects([vfx.CrossFadeOut(TRANSITION_DURATION)])

        clips.append(dark_clip)

    bg_composite = concatenate_videoclips(clips, method="compose", padding=-TRANSITION_DURATION)

    safe_end = min(total_duration, bg_composite.duration)
    bg_composite = bg_composite.subclipped(0, safe_end).with_audio(final_audio.subclipped(0, safe_end))

    layers = [bg_composite]

    # --- 1. TITLE CARD PEMBUKA ---
    if title_text:
        layers.append(create_title_card(title_text, duration=2.5).with_start(0))

    # --- 2. CLOSING / CTA ---
    if outro_text:
        outro_duration = 2.5
        outro_start = max(0, total_duration - outro_duration)
        layers.append(create_title_card(outro_text, duration=outro_duration).with_start(outro_start))

    # --- 3. LOGO WATERMARK ---
    if logo_path and os.path.exists(logo_path):
        logo_clip = create_watermark(logo_path, total_duration)
        if logo_clip:
            layers.append(logo_clip.with_start(0))
            print("🖼️ Watermark Logo berhasil dimuat.")

    # --- 4. LOWER THIRDS ---
    if lower_thirds:
        for lt in lower_thirds:
            layers.append(create_lower_third(
                lt.get("title", ""), lt.get("subtitle", ""),
                start_time=lt.get("start", 0), duration=lt.get("duration", 3.0)
            ))

    # --- 5. SUBTITLE PARSING ---
    parsed_subtitles = [_parse_subtitle_item(item) for item in word_subtitles]
    num_words = len(parsed_subtitles)

    for i, (word, start, end, is_highlight) in enumerate(parsed_subtitles):
        if not word:
            continue

        if i < num_words - 1:
            next_start = parsed_subtitles[i + 1][1]
            duration = max(0.1, next_start - start)
        else:
            duration = max(0.1, end - start)

        color = '#FFFFFF' if is_highlight else ('#FFE600' if i % 2 == 0 else '#FFFFFF')

        layers.append(create_subtitle_clip(
            text=word, font_path=DEFAULT_FONT_PATH, font_size=80,
            color=color, stroke_color='black', stroke_width=6,
            start_time=start, duration=duration,
            pos=('center', 1300), highlight=is_highlight
        ))

    # --- 6. PROGRESS BAR ---
    if add_progress_bar:
        layers.append(create_progress_bar(total_duration))

    # --- RENDER FINAL ---
    final = CompositeVideoClip(layers, size=(VIDEO_W, VIDEO_H))
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    final.write_videofile(
        output_path,
        fps=30,
        preset="medium",
        codec="libx264",
        audio_codec="aac",
        threads=4,
    )

    voice_audio.close()
    bg_composite.close()
    final.close()

    print(f"✨ SUCCESS! Video Motion Graphic siap di: {output_path}")
    return output_path