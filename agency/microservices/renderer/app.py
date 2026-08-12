"""
app.py

Microservicio Independiente de Renderizado de Video Faceless (MoneyPrinter).
Pipeline:
1. Síntesis de voz con edge-tts (.mp3 en español).
2. Búsqueda y descarga de 3-4 clips verticales HD desde Pexels API.
3. Edición, ajuste a 9:16, recorte y composición con MoviePy.
4. Subida a MinIO / S3.
5. Limpieza absoluta e inmediata de archivos temporales del disco (Zero Waste).
"""

import os
import re
import shutil
import tempfile
import logging
import asyncio
import requests
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
import edge_tts
from minio import Minio

# ── Monkeypatch: Pillow 10+ eliminó Image.ANTIALIAS; MoviePy 1.x lo usa internamente.
# Debe declararse ANTES de cualquier import lazy de moviepy.editor para que el
# parche sea visible cuando MoviePy llame a PIL.Image.ANTIALIAS por primera vez.
import PIL.Image as _pil_image
if not hasattr(_pil_image, "ANTIALIAS"):
    _pil_image.ANTIALIAS = getattr(_pil_image, "LANCZOS", _pil_image.BICUBIC)

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("video_renderer")

app = FastAPI(
    title="ViralSync Faceless Video Renderer Microservice",
    version="1.0.0",
    description="Motor de renderizado autónomo de video a costo cero con Edge-TTS, Pexels y MoviePy",
)

# Endpoint RAW (con esquema): se conserva para derivar `secure` del scheme
# (SH-03-2/3) ANTES de extraer host:puerto para el SDK (D-4).
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "viralsync-media")
# Host público browser-reachable para URLs presignadas (D-4, SH-01-3): vacío por
# default → se firma contra el endpoint del contenedor.
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", "")
MINIO_SECURE = os.getenv("MINIO_SECURE", "").lower() in ["true", "1", "yes"]
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "es-MX-JorgeNeural")


def _derive_secure() -> bool:
    """secure = True si el endpoint es https:// o MINIO_SECURE es truthy (SH-03-2/3)."""
    return MINIO_SECURE or "https://" in MINIO_ENDPOINT


def _host_port(endpoint: str) -> str:
    """Extrae host:puerto limpio de un endpoint (http[s]:// opcional)."""
    return endpoint.replace("http://", "").replace("https://", "").split("/")[0]


class RenderScene(BaseModel):
    model_config = ConfigDict(extra="ignore")

    block: str
    text: str = Field(..., min_length=1, description="Narración de la escena (no vacía)")
    tts_voice: Optional[str] = Field(default=None, description="Voz edge-tts de la escena (si falta, DEFAULT_VOICE)")
    visual_prompt: Optional[str] = Field(default=None, description="Prompt visual para derivar keywords de b-roll")
    image_url: Optional[str] = Field(default=None, description="URL de la imagen del producto")
    duration_s: Optional[float] = Field(default=None, gt=0, description="Duración explícita en segundos")


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., example="3 Errores al Escalar B2B")
    script_text: str = Field(..., example="El error principal no es la falta de herramientas, sino intentar abarcar todo sin foco.")
    keywords: List[str] = Field(default_factory=lambda: ["business", "technology", "office"])
    tenant_id: Optional[str] = Field(default="default_tenant")
    product_image_url: Optional[str] = Field(default=None, description="URL de la imagen del producto")
    scenes: Optional[List[RenderScene]] = None
    target_duration: Optional[float] = Field(default=30.0, description="Duración estricta del video: 15.0, 30.0, 45.0 o 60.0s")
    max_duration_seconds: Optional[float] = Field(default=30.0)


class RenderResponse(BaseModel):
    status: str
    video_url: str
    tenant_id: str
    duration_seconds: float


async def generate_speech_audio(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> str:
    """Genera un archivo de audio .mp3 usando Microsoft Edge TTS."""
    logger.info(f"Generando narración Edge-TTS con voz '{voice}'...")
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    logger.info(f"Audio generado exitosamente en {output_path}")
    return output_path


def audio_duration_seconds(audio_path: str) -> float:
    """Lee la duración natural de un clip de audio (TTS) con MoviePy."""
    from moviepy.editor import AudioFileClip

    clip = AudioFileClip(audio_path)
    try:
        return clip.duration
    finally:
        clip.close()


def _keywords_from_prompt(visual_prompt: Optional[str], fallback: List[str], context_text: str = "") -> List[str]:
    """Deriva keywords de búsqueda limpias y temáticas en inglés para Pexels API según el producto/servicio del formulario."""
    combined = f"{context_text} {visual_prompt or ''}".lower()

    mappings = [
        (["mic", "microfono", "k688", "fifine", "audio", "sonido", "podcast", "voz"], ["microphone", "podcast", "studio audio"]),
        (["camara", "video", "foto", "fotografia"], ["camera lens", "filmmaking", "photographer"]),
        (["software", "saas", "app", "codigo", "dev", "b2b", "ia", "tecnologia", "sistema", "plataforma"], ["coding laptop", "technology workspace", "digital software"]),
        (["gym", "fitness", "entrenamiento", "deporte", "ejercicio", "musculo"], ["fitness workout", "gym training", "athlete"]),
        (["moda", "ropa", "zapatillas", "outfit", "estilo", "calzado", "tienda"], ["fashion style", "clothing store", "outfit"]),
        (["comida", "restaurante", "cocina", "receta", "cafe", "gastronomia"], ["delicious food", "restaurant kitchen", "chef cooking"]),
        (["inmobiliaria", "casa", "departamento", "propiedad", "bienes raices"], ["modern house", "luxury apartment", "real estate"]),
        (["belleza", "skincare", "cosmeticos", "maquillaje", "piel", "estetica"], ["skincare beauty", "cosmetics model", "spa wellness"]),
        (["finanzas", "dinero", "inversion", "banco", "cripto", "negocio"], ["finance money", "business meeting", "investment stock"]),
        (["auto", "carro", "vehiculo", "moto", "mecanica"], ["modern car", "driving highway", "automotive"]),
        (["mascota", "perro", "gato", "veterinaria"], ["cute dog", "cat pet", "veterinary"]),
        (["viaje", "turismo", "hotel", "playa", "vacaciones"], ["travel destination", "beach vacation", "tourist resort"]),
    ]

    for triggers, target_kw in mappings:
        if any(tr in combined for tr in triggers):
            return target_kw

    clean_prompt = re.sub(r"https?://\S+", "", visual_prompt or "")
    clean_prompt = re.sub(r"X-Amz-\S+", "", clean_prompt)

    words = re.findall(r"[a-zA-Z]{3,}", clean_prompt)
    stop_words = {
        "vertical", "video", "high", "resolution", "cinematic", "style",
        "using", "reference", "product", "image", "from", "http", "localhost",
        "viralsync", "media", "products", "png", "jpg", "jpeg", "signedheaders",
        "signature", "credential", "algorithm", "expires", "mode", "ratio",
        "ultra", "detailed", "focus", "lighting", "shot", "hero", "with", "and"
    }
    meaningful = [w for w in words if w.lower() not in stop_words]
    return meaningful[:3] if meaningful else (fallback or ["business workspace", "technology"])


def _scene_duration_seconds(scene: RenderScene, audio_path: str) -> float:
    """Duración de una escena: `duration_s` explícito o largo natural del TTS (VSR-05)."""
    if scene.duration_s is not None:
        return scene.duration_s
    return audio_duration_seconds(audio_path)


def _scenes_total_duration(scene_durations: List[float], max_duration_seconds: Optional[float]) -> float:
    """Cap total: min(suma de escenas, max_duration_seconds o 45.0) (VSR-05, D3)."""
    cap = max_duration_seconds or 45.0
    return min(sum(scene_durations), cap)


def download_pexels_videos(keywords: List[str], temp_dir: str, per_page: int = 3) -> List[str]:
    """Descarga clips de video verticales en formato HD usando Pexels API con diversidad dinámica."""
    downloaded_files = []

    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY no configurada. Generando aviso para clips vacíos.")
        return downloaded_files

    import random
    import uuid

    headers = {"Authorization": PEXELS_API_KEY}
    query = "+".join(keywords) if keywords else "business+technology"
    random_page = random.randint(1, 4)
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page={per_page}&page={random_page}"

    try:
        response = requests.get(url, headers=headers, timeout=10.0)
        data = response.json() if response.status_code == 200 else {}
        videos = data.get("videos", [])

        if not videos:
            url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page={per_page}&page=1"
            response = requests.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                videos = response.json().get("videos", [])

        if videos:
            for idx, video in enumerate(videos[:per_page]):
                video_files = video.get("video_files", [])
                light_file = next((vf for vf in video_files if 720 <= vf.get("height", 0) <= 1080), None) or (video_files[0] if video_files else None)
                if light_file and light_file.get("link"):
                    video_url = light_file["link"]
                    short_uuid = uuid.uuid4().hex[:6]
                    file_path = os.path.join(temp_dir, f"pexels_clip_{short_uuid}_{idx}.mp4")
                    logger.info(f"Filtro Hardware (720p): Descargando clip Pexels {idx + 1} ({query}, pag {random_page})...")
                    with requests.get(video_url, stream=True, timeout=15.0) as r:
                        r.raise_for_status()
                        with open(file_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                    downloaded_files.append(file_path)
    except Exception as exc:
        logger.error(f"Error descargando clips de Pexels API ({exc})")

    return downloaded_files


def compose_video_moviepy(audio_path: str, video_paths: List[str], output_path: str) -> float:
    """Compone y renderiza el video vertical 9:16 combinando audios y clips con MoviePy."""
    from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips, ColorClip

    logger.info("Componiendo video final con MoviePy...")
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration if audio_clip.duration > 0 else 30.0
    TARGET_W, TARGET_H = 1080, 1920

    clip_objects = []
    if video_paths:
        duration_per_clip = audio_duration / len(video_paths)
        for path in video_paths:
            try:
                v_clip = VideoFileClip(path)
                clip_ratio = v_clip.w / v_clip.h
                target_ratio = TARGET_W / TARGET_H
                if clip_ratio > target_ratio:
                    sub_clip = v_clip.resize(height=TARGET_H)
                    x_center = sub_clip.w / 2
                    sub_clip = sub_clip.crop(x1=x_center - TARGET_W / 2, width=TARGET_W)
                else:
                    sub_clip = v_clip.resize(width=TARGET_W)
                    y_center = sub_clip.h / 2
                    sub_clip = sub_clip.crop(y1=max(0, y_center - TARGET_H / 2), height=TARGET_H)
                
                sub_clip = sub_clip.subclip(0, min(sub_clip.duration, duration_per_clip))

                def _make_overlay_frame(gf, t, dur=duration_per_clip):
                    try:
                        frame = gf(t)
                        base = Image.fromarray(frame)
                        if base.size != (TARGET_W, TARGET_H):
                            base = base.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
                        out_img = draw_overlay_on_image(base, "", None, t, dur)
                        return np.array(out_img)
                    except Exception as exc:
                        logger.warning(f"Error en _make_overlay_frame flat: {exc}")
                        return gf(t)

                sub_clip = sub_clip.fl(_make_overlay_frame)
                clip_objects.append(sub_clip)
            except Exception as exc:
                logger.warning(f"Error procesando clip {path}: {exc}")

    if not clip_objects:
        logger.info("Usando fondo dinámico de fallback para el renderizado...")
        fallback_clip = ColorClip(size=(1080, 1920), color=(15, 23, 42), duration=audio_duration)
        clip_objects.append(fallback_clip)

    final_video = concatenate_videoclips(clip_objects, method="chain")
    final_video = final_video.set_audio(audio_clip)
    final_video = final_video.set_duration(audio_duration)

    logger.info(f"Renderizando archivo final en {output_path} (Duración: {audio_duration:.2f}s)...")
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        threads=os.cpu_count() or 2,
        logger=None,
    )

    audio_clip.close()
    final_video.close()
    for c in clip_objects:
        try:
            c.close()
        except Exception:
            pass

    return audio_duration


import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def generate_scene_frame(
    width: int,
    height: int,
    text: str,
    product_img: Optional[Image.Image],
    t: float,
    duration: float,
) -> np.ndarray:
    """
    Genera un frame 9:16 vertical (1080x1920) dinámico de calidad profesional:
    1. Fondo: Gradiente índigo oscuro + ambient blur del producto.
    2. Producto: Tarjeta centrada con marco resplandeciente y zoom Ken Burns ligero.
    3. Subtítulos: Banner dinámico amarillo/blanco en negrita en el tercio inferior.
    """
    img = Image.new("RGB", (width, height), (15, 23, 42))
    draw = ImageDraw.Draw(img)

    for y in range(0, height, 4):
        r = int(15 + (30 - 15) * (y / height))
        g = int(23 + (27 - 23) * (y / height))
        b = int(42 + (75 - 42) * (y / height))
        draw.rectangle([(0, y), (width, y + 4)], fill=(r, g, b))

    if product_img:
        try:
            bg_copy = product_img.copy().convert("RGB")
            bg_scaled = bg_copy.resize((width, height), Image.Resampling.LANCZOS)
            bg_blurred = bg_scaled.filter(ImageFilter.GaussianBlur(radius=35))
            img = Image.blend(img, bg_blurred, alpha=0.35)
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    if product_img:
        try:
            card_w, card_h = 680, 680
            progress = min(max(t / max(duration, 0.1), 0.0), 1.0)
            zoom = 1.0 + 0.05 * progress
            cur_w = int(card_w * zoom)
            cur_h = int(card_h * zoom)

            p_resized = product_img.copy().convert("RGBA").resize((cur_w, cur_h), Image.Resampling.LANCZOS)

            pos_x = (width - cur_w) // 2
            pos_y = 420 + (card_h - cur_h) // 2

            card_bg = Image.new("RGBA", (cur_w + 24, cur_h + 24), (0, 0, 0, 0))
            card_draw = ImageDraw.Draw(card_bg)
            card_draw.rounded_rectangle(
                [(0, 0), (cur_w + 24, cur_h + 24)],
                radius=32,
                fill=(15, 23, 42, 230),
                outline=(129, 140, 248, 240),
                width=4,
            )
            img.paste(card_bg, (pos_x - 12, pos_y - 12), card_bg)
            img.paste(p_resized, (pos_x, pos_y), p_resized)
        except Exception as exc:
            logger.warning(f"Error renderizando tarjeta de producto: {exc}")

    if text:
        try:
            lines = textwrap.wrap(text, width=28)
            if lines:
                font_size = 46
                font_paths = [
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                ]
                font = None
                use_ttf = False
                for fp in font_paths:
                    if os.path.exists(fp):
                        try:
                            font = ImageFont.truetype(fp, font_size)
                            use_ttf = True
                            break
                        except Exception:
                            pass
                if not font:
                    font = ImageFont.load_default()

                line_height = 60
                badge_w = 940
                badge_h = len(lines) * line_height + 40
                badge_x = (width - badge_w) // 2
                badge_y = 1380 - (badge_h // 2)

                sub_badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
                sub_draw = ImageDraw.Draw(sub_badge)
                sub_draw.rounded_rectangle(
                    [(0, 0), (badge_w, badge_h)],
                    radius=24,
                    fill=(15, 23, 42, 225),
                    outline=(250, 204, 21, 220),
                    width=3,
                )
                img.paste(sub_badge, (badge_x, badge_y), sub_badge)

                draw_sub = ImageDraw.Draw(img)
                for idx, line in enumerate(lines):
                    ly = badge_y + 25 + idx * line_height
                    text_color = (250, 204, 21) if idx == 0 else (255, 255, 255)
                    
                    if use_ttf:
                        draw_sub.text(
                            (width // 2, ly),
                            line,
                            font=font,
                            fill=text_color,
                            anchor="mm",
                            stroke_width=3,
                            stroke_fill=(0, 0, 0),
                        )
                    else:
                        bbox = draw_sub.textbbox((0, 0), line, font=font)
                        tw = bbox[2] - bbox[0]
                        tx = (width - tw) // 2
                        draw_sub.text((tx, ly), line, font=font, fill=text_color)
        except Exception as exc:
            logger.warning(f"Error renderizando subtítulos: {exc}")

    return np.array(img)


def draw_overlay_on_image(
    base_img: Image.Image,
    text: str,
    prod_img: Optional[Image.Image] = None,
    t: float = 0.0,
    duration: float = 5.0
) -> Image.Image:
    """Superpone tarjeta de producto flotante y subtítulos estilo Karaoke dinámicos sobre la imagen base del video."""
    width, height = base_img.size
    img = base_img.convert("RGBA")

    # 1. Tarjeta flotante de producto (tercio superior: y=240..660)
    if prod_img:
        try:
            card_size = 400
            progress = min(max(t / max(duration, 0.1), 0.0), 1.0)
            zoom = 1.0 + 0.04 * np.sin(progress * np.pi)
            cur_w = int(card_size * zoom)
            cur_h = int(card_size * zoom)

            p_rgba = prod_img.copy().convert("RGBA").resize((cur_w, cur_h), Image.Resampling.LANCZOS)

            pos_x = (width - cur_w) // 2
            pos_y = 240 + (card_size - cur_h) // 2

            card_bg = Image.new("RGBA", (cur_w + 30, cur_h + 30), (0, 0, 0, 0))
            card_draw = ImageDraw.Draw(card_bg)
            card_draw.rounded_rectangle(
                [(0, 0), (cur_w + 30, cur_h + 30)],
                radius=28,
                fill=(15, 23, 42, 220),
                outline=(250, 204, 21, 240),
                width=4,
            )
            img.paste(card_bg, (pos_x - 15, pos_y - 15), card_bg)
            img.paste(p_rgba, (pos_x, pos_y), p_rgba)
        except Exception as exc:
            logger.warning(f"Error renderizando tarjeta de producto sobre video: {exc}")

    # 2. Subtítulo dinámico estilo Karaoke en el tercio inferior (y=1420)
    if text:
        try:
            clean_text = text.strip()
            words = clean_text.split()
            if words:
_CACHED_FONT = None

def _get_subtitle_font(font_size: int = 48):
    global _CACHED_FONT
    if _CACHED_FONT is not None:
        return _CACHED_FONT
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                _CACHED_FONT = ImageFont.truetype(fp, font_size)
                return _CACHED_FONT
            except Exception:
                pass
    _CACHED_FONT = ImageFont.load_default()
    return _CACHED_FONT


def draw_overlay_on_image(
    base_img: Image.Image,
    text: str,
    prod_img: Optional[Image.Image] = None,
    t: float = 0.0,
    duration: float = 5.0
) -> Image.Image:
    """Superpone tarjeta de producto flotante y subtítulos estilo Karaoke dinámicos sobre la imagen base del video."""
    width, height = base_img.size
    img = base_img.convert("RGBA")

    # 1. Tarjeta flotante de producto (tercio superior: y=240..660)
    if prod_img:
        try:
            card_size = 400
            progress = min(max(t / max(duration, 0.1), 0.0), 1.0)
            zoom = 1.0 + 0.04 * np.sin(progress * np.pi)
            cur_w = int(card_size * zoom)
            cur_h = int(card_size * zoom)

            p_rgba = prod_img.copy().convert("RGBA").resize((cur_w, cur_h), Image.Resampling.LANCZOS)

            pos_x = (width - cur_w) // 2
            pos_y = 240 + (card_size - cur_h) // 2

            card_bg = Image.new("RGBA", (cur_w + 30, cur_h + 30), (0, 0, 0, 0))
            card_draw = ImageDraw.Draw(card_bg)
            card_draw.rounded_rectangle(
                [(0, 0), (cur_w + 30, cur_h + 30)],
                radius=28,
                fill=(15, 23, 42, 220),
                outline=(250, 204, 21, 240),
                width=4,
            )
            img.paste(card_bg, (pos_x - 15, pos_y - 15), card_bg)
            img.paste(p_rgba, (pos_x, pos_y), p_rgba)
        except Exception as exc:
            logger.warning(f"Error renderizando tarjeta de producto sobre video: {exc}")

    # 2. Subtítulo dinámico estilo Karaoke en el tercio inferior (y=1420)
    if text:
        try:
            clean_text = text.strip()
            words = clean_text.split()
            if words:
                font = _get_subtitle_font(48)

                # Índice de la palabra activa en tiempo t
                progress = min(max(t / max(duration, 0.001), 0.0), 1.0)
                active_idx = min(int(progress * len(words)), len(words) - 1)

                # Agrupar palabras en líneas de 4 palabras
                words_per_line = 4
                lines = []
                for i in range(0, len(words), words_per_line):
                    lines.append((i, words[i:i + words_per_line]))

                # Determinar qué línea contiene la palabra activa
                active_line_idx = 0
                for idx, (start_word_i, line_words) in enumerate(lines):
                    if start_word_i <= active_idx < start_word_i + len(line_words):
                        active_line_idx = idx
                        break

                # Mostrar hasta 2 líneas a la vez alrededor de la línea activa
                visible_lines = lines[max(0, active_line_idx - 1): min(len(lines), active_line_idx + 2)]

                badge_w = 980
                line_height = 64
                badge_h = len(visible_lines) * line_height + 44
                badge_x = (width - badge_w) // 2
                badge_y = 1420 - (badge_h // 2)

                sub_badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
                sub_draw = ImageDraw.Draw(sub_badge)
                sub_draw.rounded_rectangle(
                    [(0, 0), (badge_w, badge_h)],
                    radius=26,
                    fill=(15, 23, 42, 230),
                    outline=(250, 204, 21, 240),
                    width=4,
                )

                # Dibujar palabras con destacado en amarillo para la palabra activa (Karaoke)
                for l_offset, (start_word_i, line_words) in enumerate(visible_lines):
                    ly = 22 + l_offset * line_height
                    
                    word_widths = []
                    for w in line_words:
                        bbox = sub_draw.textbbox((0, 0), w, font=font)
                        word_widths.append(bbox[2] - bbox[0])
                    
                    space_w = 14
                    total_line_w = sum(word_widths) + space_w * (len(line_words) - 1)
                    cur_x = (badge_w - total_line_w) // 2

                    for w_offset, (w, w_w) in enumerate(zip(line_words, word_widths)):
                        global_w_idx = start_word_i + w_offset
                        if global_w_idx == active_idx:
                            # Palabra ACTIVA (Karaoke Highlight): Amarillo brillante con bordes negros gruesos
                            fill_c = (250, 204, 21, 255)
                            sw = 4
                        elif global_w_idx < active_idx:
                            # Palabra YA HABLADA: Blanco puro
                            fill_c = (255, 255, 255, 255)
                            sw = 2
                        else:
                            # Palabra FUTURA: Blanco suave / gris claro
                            fill_c = (210, 215, 225, 230)
                            sw = 2

                        sub_draw.text(
                            (cur_x, ly),
                            w,
                            font=font,
                            fill=fill_c,
                            stroke_width=sw,
                            stroke_fill=(0, 0, 0, 255),
                        )
                        cur_x += w_w + space_w

                img.paste(sub_badge, (badge_x, badge_y), sub_badge)
        except Exception as exc:
            logger.warning(f"Error renderizando subtítulos karaoke sobre video: {exc}")

    return img.convert("RGB")


def compose_scenes_video_moviepy(segments: List[dict], output_path: str, total_duration: float) -> float:
    """Compone el video por escenas concatenando clips 9:16 de Pexels con overlay de producto y subtítulo Karaoke animado."""
    from moviepy.editor import (
        AudioFileClip,
        VideoFileClip,
        VideoClip,
        concatenate_audioclips,
        concatenate_videoclips,
    )

    logger.info(f"Componiendo video por escenas con MoviePy ({len(segments)} escenas, Duración objetivo estricta: {total_duration:.2f}s)...")
    video_clips = []
    audio_clips = []
    TARGET_W, TARGET_H = 1080, 1920

    for seg in segments:
        seg_duration = seg["duration"]
        per_clip = seg_duration / max(len(seg["video_paths"]), 1)
        scene_text = seg.get("text", "")

        prod_img_obj = None
        img_url = seg.get("image_url")
        if img_url:
            try:
                fetch_url = (
                    img_url.replace("localhost:9000", "minio:9000")
                    .replace("127.0.0.1:9000", "minio:9000")
                )
                headers = {"Host": "localhost:9000"} if "minio:9000" in fetch_url else {}
                logger.info(f"Descargando foto de producto desde: {fetch_url}")
                r = requests.get(fetch_url, headers=headers, timeout=8.0)
                if r.status_code == 200:
                    from io import BytesIO
                    prod_img_obj = Image.open(BytesIO(r.content)).copy()
                    logger.info("Imagen de producto descargada e instanciada con éxito.")
                else:
                    logger.warning(f"Status HTTP {r.status_code} al descargar imagen de producto: {r.status_code}")
            except Exception as e:
                logger.warning(f"No se pudo descargar imagen de producto: {e}")

        # 1. Ajuste del clip de audio de la escena a la duración exacta seg_duration
        try:
            a_clip = AudioFileClip(seg["audio_path"])
            if a_clip.duration > 0 and abs(a_clip.duration - seg_duration) > 0.05:
                ratio = a_clip.duration / seg_duration
                a_clip = a_clip.fl_time(lambda t, r=ratio: t * r, keep_duration=False).set_duration(seg_duration)
            audio_clips.append(a_clip)
        except Exception as exc:
            logger.warning(f"Error procesando audio {seg.get('audio_path')}: {exc}")

        # 2. Clips de video de la escena (Shorts transicionales de Pexels)
        block = []
        for path in seg["video_paths"]:
            try:
                v_clip = VideoFileClip(path)
                clip_ratio = v_clip.w / v_clip.h
                target_ratio = TARGET_W / TARGET_H
                if clip_ratio > target_ratio:
                    sub_clip = v_clip.resize(height=TARGET_H)
                    x_center = sub_clip.w / 2
                    sub_clip = sub_clip.crop(x1=x_center - TARGET_W / 2, width=TARGET_W)
                else:
                    sub_clip = v_clip.resize(width=TARGET_W)
                    y_center = sub_clip.h / 2
                    sub_clip = sub_clip.crop(y1=max(0, y_center - TARGET_H / 2), height=TARGET_H)

                sub_clip = sub_clip.subclip(0, min(sub_clip.duration, per_clip))

                _txt = scene_text
                _pimg = prod_img_obj
                _dur = seg_duration

                def _make_overlay_frame(gf, t, txt=_txt, p_img=_pimg, dur=_dur):
                    try:
                        frame = gf(t)
                        base = Image.fromarray(frame)
                        if base.size != (TARGET_W, TARGET_H):
                            base = base.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
                        out_img = draw_overlay_on_image(base, txt, p_img, t, dur)
                        return np.array(out_img)
                    except Exception as exc:
                        logger.warning(f"Error en _make_overlay_frame: {exc}")
                        return gf(t)

                sub_clip = sub_clip.fl(_make_overlay_frame)
                block.append(sub_clip)
            except Exception as exc:
                logger.warning(f"Error procesando clip {path}: {exc}")

        if not block:
            logger.info("Generando escena animada de fallback con imagen de producto y subtítulos karaoke...")
            _txt2 = scene_text
            _pimg2 = prod_img_obj
            _dur2 = seg_duration

            def make_frame(t, txt=_txt2, p_img=_pimg2, dur=_dur2):
                base = Image.new("RGB", (TARGET_W, TARGET_H), (15, 23, 42))
                out_img = draw_overlay_on_image(base, txt, p_img, t, dur)
                return np.array(out_img)

            v_clip = VideoClip(make_frame, duration=seg_duration)
            block.append(v_clip)

        video_clips.extend(block)

    final_video = concatenate_videoclips(video_clips, method="chain")
    final_audio = concatenate_audioclips(audio_clips) if len(audio_clips) > 1 else audio_clips[0]

    # Forzar duración objetivo ESTRICTA (15s, 30s, 45s, 60s)
    final_video = final_video.set_audio(final_audio)
    final_video = final_video.set_duration(total_duration)

    logger.info(f"Renderizando archivo final por escenas en {output_path} (Duración estricta: {total_duration:.2f}s)...")
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        threads=os.cpu_count() or 2,
        logger=None,
    )

    for clip in audio_clips + video_clips:
        try:
            clip.close()
        except Exception:
            pass

    return total_duration


async def _render_scene_pipeline(req: RenderRequest, temp_dir: str, output_mp4_path: str) -> float:
    """Pipeline de render por escenas con duración objetivo estricta (15s, 30s, 45s, 60s)."""
    raw_target = float(req.target_duration or req.max_duration_seconds or 30.0)
    # Sanear duraciones a uno de los 4 valores estrictos (15s, 30s, 45s, 60s)
    if raw_target <= 20:
        strict_duration = 15.0
    elif raw_target <= 37:
        strict_duration = 30.0
    elif raw_target <= 52:
        strict_duration = 45.0
    else:
        strict_duration = 60.0

    num_scenes = len(req.scenes) if req.scenes else 1
    per_scene_duration = strict_duration / num_scenes

    scene_audios: List[str] = []
    scene_clip_lists: List[List[str]] = []
    scene_durations: List[float] = []

    for idx, scene in enumerate(req.scenes):
        voice = scene.tts_voice or DEFAULT_VOICE
        scene_audio = os.path.join(temp_dir, f"scene_{idx}.mp3")
        logger.info(f"[{req.tenant_id}] Escena {idx + 1}/{num_scenes} ('{scene.block}') — TTS con voz '{voice}' (Objetivo: {per_scene_duration:.2f}s)")
        await generate_speech_audio(scene.text, scene_audio, voice)
        scene_audios.append(scene_audio)

        scene_keywords = _keywords_from_prompt(scene.visual_prompt, req.keywords, f"{req.title} {scene.text}")
        logger.info(f"[{req.tenant_id}] Escena {idx + 1} — búsqueda Pexels con keywords {scene_keywords}")
        scene_clips = await asyncio.to_thread(download_pexels_videos, scene_keywords, temp_dir, per_page=3)
        scene_clip_lists.append(scene_clips)

        scene_durations.append(per_scene_duration)

    segments = [
        {
            "audio_path": audio_path,
            "video_paths": clip_paths,
            "duration": per_scene_duration,
            "text": scene.text,
            "image_url": scene.image_url or req.product_image_url,
        }
        for audio_path, clip_paths, scene in zip(scene_audios, scene_clip_lists, req.scenes)
    ]
    return await asyncio.to_thread(compose_scenes_video_moviepy, segments, output_mp4_path, strict_duration)


def upload_to_minio(file_path: str, tenant_id: str) -> str:
    """Sube el archivo final .mp4 a MinIO y retorna la URL PRESIGNADA del objeto.

    REQ-SH-04: el bucket es PRIVADO → la URL devuelta es un presigned_get_object
    real (SH-04-1), NUNCA una raíz pública fabricada que 403 en prod (SH-04-2).
    Si MINIO_PUBLIC_ENDPOINT está seteado, la firma se hace contra ese host
    (browser-reachable) vía un signer client; si no, contra el endpoint del
    contenedor (D-4).
    """
    logger.info(f"Conectando a MinIO en {MINIO_ENDPOINT}...")
    minio_client = Minio(
        endpoint=_host_port(MINIO_ENDPOINT),
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        secure=_derive_secure(),
    )
    # Signer "público" opcional: MINIO_PUBLIC_ENDPOINT → firmar contra ese host
    # (native signing, sin string-surgery — D-4, SH-01-3).
    signer_client = minio_client
    if MINIO_PUBLIC_ENDPOINT:
        signer_client = Minio(
            endpoint=_host_port(MINIO_PUBLIC_ENDPOINT),
            access_key=MINIO_ROOT_USER,
            secret_key=MINIO_ROOT_PASSWORD,
            secure=_derive_secure(),
        )

    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)

    import uuid
    short_id = uuid.uuid4().hex[:8]
    clean_name = os.path.basename(file_path).replace(" ", "_")
    object_name = f"{tenant_id}/videos/reel_{short_id}_{clean_name}"
    minio_client.fput_object(MINIO_BUCKET, object_name, file_path, content_type="video/mp4")

    public_url = signer_client.presigned_get_object(MINIO_BUCKET, object_name)
    logger.info(f"Video subido exitosamente a MinIO: {public_url}")
    return public_url


BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://backend:8000/api/v1")
FALLBACK_BACKEND_URL = "http://localhost:8000/api/v1"


def report_render_progress(tenant_id: str, stage: str, message: str, percent: int):
    """Notifica el avance del renderizado a la API principal para retransmitir por SSE."""
    payload = {"stage": stage, "message": message, "percent": percent}
    for base_url in [BACKEND_API_URL, FALLBACK_BACKEND_URL]:
        try:
            requests.post(f"{base_url}/tenants/{tenant_id}/progress", json=payload, timeout=2.0)
            break
        except Exception:
            pass


@app.post("/render", response_model=RenderResponse, status_code=status.HTTP_201_CREATED)
async def render_video_endpoint(req: RenderRequest):
    """
    Endpoint principal para renderizar videos faceless a costo cero.
    Despacha las operaciones CPU-bound a hilos secundarios para no congelar el bucle de eventos de FastAPI.
    Garantiza la eliminación de todos los archivos temporales post-renderizado (Zero Waste).
    """
    temp_dir = tempfile.mkdtemp(prefix="viralsync_render_")
    audio_path = os.path.join(temp_dir, "speech.mp3")
    output_mp4_path = os.path.join(temp_dir, "final_output.mp4")

    logger.info(f"[{req.tenant_id}] Iniciando renderizado faceless no-bloqueante: '{req.title}'")
    report_render_progress(req.tenant_id, "start", "Iniciando renderizado faceless...", 5)

    # -- PR-A: render por escenas (REQ-VSR-01..06). Branch aditivo ANTES del
    #    pipeline flat; el bloque flat de abajo queda intacto (byte-idéntico).
    if req.scenes:
        logger.info(f"[{req.tenant_id}] Renderizando {len(req.scenes)} escenas del storyboard: '{req.title}'")
        try:
            report_render_progress(req.tenant_id, "audio", "Sintetizando narración por escenas con Edge-TTS...", 25)
            report_render_progress(req.tenant_id, "broll", "Buscando y descargando B-roll por escena desde Pexels...", 50)
            duration = await _render_scene_pipeline(req, temp_dir, output_mp4_path)

            report_render_progress(req.tenant_id, "moviepy", "Componiendo video por escenas 9:16 con MoviePy...", 75)
            report_render_progress(req.tenant_id, "minio", "Subiendo video MP4 producido a MinIO Storage...", 90)
            video_url = await asyncio.to_thread(upload_to_minio, output_mp4_path, req.tenant_id)

            report_render_progress(req.tenant_id, "completed", "Renderizado completado con éxito.", 100)
            return RenderResponse(
                status="completed",
                video_url=video_url,
                tenant_id=req.tenant_id,
                duration_seconds=duration,
            )
        except Exception as exc:
            logger.error(f"Error durante la ejecución del pipeline de renderizado por escenas: {exc}")
            raise HTTPException(status_code=500, detail=f"Error en renderizado de video: {str(exc)}")
        finally:
            # CRÍTICO PARA EL DISCO: limpieza absoluta (Zero Waste) en el branch de escenas
            logger.info(f"Ejecutando recolección de basura Zero Waste en {temp_dir}...")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info("Carpeta y archivos temporales eliminados del disco satisfactoriamente.")

    try:
        # 1. Generar audio con Edge-TTS
        report_render_progress(req.tenant_id, "audio", "Sintetizando voz en español con Edge-TTS...", 25)
        await generate_speech_audio(req.script_text, audio_path)

        # 2. Descargar clips de Pexels API en hilo secundario (Non-blocking I/O)
        report_render_progress(req.tenant_id, "broll", "Buscando y descargando clips B-roll 720p desde Pexels...", 50)
        downloaded_clips = await asyncio.to_thread(download_pexels_videos, req.keywords, temp_dir)

        # 3. Componer video con MoviePy en hilo secundario (Non-blocking CPU-bound)
        report_render_progress(req.tenant_id, "moviepy", "Componiendo y ajustando formato 9:16 con MoviePy...", 75)
        duration = await asyncio.to_thread(compose_video_moviepy, audio_path, downloaded_clips, output_mp4_path)

        # 4. Subir a MinIO
        report_render_progress(req.tenant_id, "minio", "Subiendo video MP4 producido a MinIO Storage...", 90)
        video_url = await asyncio.to_thread(upload_to_minio, output_mp4_path, req.tenant_id)

        report_render_progress(req.tenant_id, "completed", "Renderizado completado con éxito.", 100)

        return RenderResponse(
            status="completed",
            video_url=video_url,
            tenant_id=req.tenant_id,
            duration_seconds=duration,
        )

    except Exception as exc:
        logger.error(f"Error durante la ejecución del pipeline de renderizado: {exc}")
        raise HTTPException(status_code=500, detail=f"Error en renderizado de video: {str(exc)}")

    finally:
        # CRÍTICO PARA EL DISCO: Limpieza absoluta de la carpeta y archivos temporales ante cualquier resultado
        logger.info(f"Ejecutando recolección de basura Zero Waste en {temp_dir}...")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info("Carpeta y archivos temporales eliminados del disco satisfactoriamente.")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "faceless_video_renderer"}
