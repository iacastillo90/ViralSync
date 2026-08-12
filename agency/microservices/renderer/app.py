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
    max_duration_seconds: Optional[float] = Field(default=45.0)


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
    """Deriva keywords de búsqueda limpias y temáticas para Pexels API."""
    combined = f"{context_text} {visual_prompt or ''}".lower()

    # Mapeos temáticos según el nicho/producto detectado
    mappings = [
        (["mic", "microfono", "k688", "fifine", "audio", "sonido", "podcast", "voz"], ["microphone", "podcast", "studio audio"]),
        (["camara", "video", "foto", "fotografia"], ["camera", "filmmaking", "studio"]),
        (["software", "saas", "app", "codigo", "dev", "b2b", "ia", "tecnologia"], ["coding", "laptop", "technology"]),
        (["gym", "fitness", "entrenamiento", "deporte"], ["fitness", "workout", "gym"]),
        (["moda", "ropa", "zapatillas", "outfit", "estilo"], ["fashion", "clothing", "style"]),
        (["comida", "restaurante", "cocina"], ["food", "cooking", "restaurant"]),
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
    return meaningful[:3] if meaningful else (fallback or ["business"])


def _scene_duration_seconds(scene: RenderScene, audio_path: str) -> float:
    """Duración de una escena: `duration_s` explícito o largo natural del TTS (VSR-05)."""
    if scene.duration_s is not None:
        return scene.duration_s
    return audio_duration_seconds(audio_path)


def _scenes_total_duration(scene_durations: List[float], max_duration_seconds: Optional[float]) -> float:
    """Cap total: min(suma de escenas, max_duration_seconds o 45.0) (VSR-05, D3)."""
    cap = max_duration_seconds or 45.0
    return min(sum(scene_durations), cap)


def download_pexels_videos(keywords: List[str], temp_dir: str, per_page: int = 4) -> List[str]:
    """Descarga clips de video verticales en formato HD usando Pexels API.

    `per_page` acota la búsqueda: el pipeline flat usa 4 (comportamiento
    histórico intacto); el render por escenas usa 2 (D3, búsquedas acotadas).
    """
    downloaded_files = []

    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY no configurada. Generando aviso para clips vacíos.")
        return downloaded_files

    headers = {"Authorization": PEXELS_API_KEY}
    query = "+".join(keywords) if keywords else "business"
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page={per_page}"

    try:
        response = requests.get(url, headers=headers, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            for idx, video in enumerate(videos[:per_page]):
                video_files = video.get("video_files", [])
                light_file = next((vf for vf in video_files if 720 <= vf.get("height", 0) <= 1080), None) or video_files[0] if video_files else None
                if light_file and light_file.get("link"):
                    video_url = light_file["link"]
                    file_path = os.path.join(temp_dir, f"pexels_clip_{idx}.mp4")
                    logger.info(f"Filtro Hardware (720p): Descargando clip Pexels {idx + 1}...")
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
    """Compone y renderiza el video vertical 9:16 combinando audios y clips con MoviePy (Máx 45s)."""
    from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips, ColorClip

    logger.info("Componiendo video final con MoviePy...")
    audio_clip = AudioFileClip(audio_path)
    audio_duration = min(audio_clip.duration, 45.0)

    clip_objects = []
    if video_paths:
        duration_per_clip = audio_duration / len(video_paths)
        for path in video_paths:
            try:
                v_clip = VideoFileClip(path)
                sub_clip = v_clip.subclip(0, min(v_clip.duration, duration_per_clip))
                sub_clip = sub_clip.resize(height=1920)
                if sub_clip.w > 1080:
                    x_center = sub_clip.w / 2
                    sub_clip = sub_clip.crop(x1=x_center - 540, width=1080)
                clip_objects.append(sub_clip)
            except Exception as exc:
                logger.warning(f"Error procesando clip {path}: {exc}")

    if not clip_objects:
        logger.info("Usando fondo dinámico de fallback para el renderizado...")
        fallback_clip = ColorClip(size=(1080, 1920), color=(15, 23, 42), duration=audio_duration)
        clip_objects.append(fallback_clip)

    final_video = concatenate_videoclips(clip_objects, method="compose")
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
        c.close()

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
    """Superpone tarjeta de producto flotante y subtítulo con badge sobre la imagen base del video."""
    width, height = base_img.size
    img = base_img.convert("RGBA")

    # 1. Tarjeta flotante de producto (tercio superior: y=260..680)
    if prod_img:
        try:
            card_size = 420
            progress = min(max(t / max(duration, 0.1), 0.0), 1.0)
            zoom = 1.0 + 0.04 * np.sin(progress * np.pi)
            cur_w = int(card_size * zoom)
            cur_h = int(card_size * zoom)

            p_rgba = prod_img.copy().convert("RGBA").resize((cur_w, cur_h), Image.Resampling.LANCZOS)

            pos_x = (width - cur_w) // 2
            pos_y = 260 + (card_size - cur_h) // 2

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

    # 2. Subtítulo badge en el tercio inferior (y=1450)
    if text:
        try:
            lines = textwrap.wrap(text, width=28)
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

            line_height = 58
            badge_w = 960
            badge_h = len(lines) * line_height + 40
            badge_x = (width - badge_w) // 2
            badge_y = 1450 - (badge_h // 2)

            sub_badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
            sub_draw = ImageDraw.Draw(sub_badge)
            sub_draw.rounded_rectangle(
                [(0, 0), (badge_w, badge_h)],
                radius=24,
                fill=(15, 23, 42, 230),
                outline=(250, 204, 21, 240),
                width=3,
            )

            for idx, line in enumerate(lines):
                ly = 25 + idx * line_height
                text_color = (250, 204, 21, 255) if idx == 0 else (255, 255, 255, 255)
                if use_ttf:
                    bbox = sub_draw.textbbox((0, 0), line, font=font)
                    tw = bbox[2] - bbox[0]
                    tx = (badge_w - tw) // 2
                    sub_draw.text((tx, ly), line, font=font, fill=text_color, stroke_width=2, stroke_fill=(0, 0, 0))
                else:
                    bbox = sub_draw.textbbox((0, 0), line, font=font)
                    tw = bbox[2] - bbox[0]
                    tx = (badge_w - tw) // 2
                    sub_draw.text((tx, ly), line, font=font, fill=text_color)

            img.paste(sub_badge, (badge_x, badge_y), sub_badge)
        except Exception as exc:
            logger.warning(f"Error renderizando subtítulos sobre video: {exc}")

    return img.convert("RGB")


def compose_scenes_video_moviepy(segments: List[dict], output_path: str, total_duration: float) -> float:
    """Compone el video por escenas concatenando clips 9:16 de Pexels con overlay de producto y subtítulo."""
    from moviepy.editor import (
        AudioFileClip,
        VideoFileClip,
        VideoClip,
        concatenate_audioclips,
        concatenate_videoclips,
    )

    logger.info(f"Componiendo video por escenas con MoviePy ({len(segments)} escenas)...")
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

                def _overlay_fn(frame, txt=_txt, p_img=_pimg, dur=_dur):
                    try:
                        base = Image.fromarray(frame)
                        if base.size != (TARGET_W, TARGET_H):
                            base = base.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
                        out_img = draw_overlay_on_image(base, txt, p_img, 0.0, dur)
                        return np.array(out_img)
                    except Exception as exc:
                        logger.warning(f"Error en _overlay_fn: {exc}")
                        return frame

                sub_clip = sub_clip.fl_image(_overlay_fn)
                block.append(sub_clip)
            except Exception as exc:
                logger.warning(f"Error procesando clip {path}: {exc}")

        if not block:
            logger.info("Generando escena animada de fallback con imagen de producto y subtítulos...")
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
        audio_clips.append(AudioFileClip(seg["audio_path"]))

    final_video = concatenate_videoclips(video_clips, method="chain")
    final_audio = concatenate_audioclips(audio_clips) if len(audio_clips) > 1 else audio_clips[0]

    real_duration = final_audio.duration if (final_audio and hasattr(final_audio, "duration") and final_audio.duration > 0) else total_duration

    if final_video.duration > real_duration:
        logger.info(f"Recortando línea de tiempo del video de {final_video.duration:.2f}s a la duración real del audio ({real_duration:.2f}s)...")
        final_video = final_video.subclip(0, real_duration)

    final_video = final_video.set_audio(final_audio)
    final_video = final_video.set_duration(real_duration)

    logger.info(f"Renderizando archivo final por escenas en {output_path} (Duración real del audio: {real_duration:.2f}s)...")
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
    """Pipeline de render por escenas (REQ-VSR-03/04/05, D3).

    Por cada escena: TTS con `tts_voice` (o DEFAULT_VOICE), b-roll con keywords
    derivadas de `visual_prompt` (o las del payload) y per_page=2, duración
    `duration_s` o largo natural del TTS. Se concatena en orden y se capa el
    total a `min(suma, max_duration_seconds or 45.0)`.
    """
    scene_audios: List[str] = []
    scene_clip_lists: List[List[str]] = []
    scene_durations: List[float] = []

    for idx, scene in enumerate(req.scenes):
        voice = scene.tts_voice or DEFAULT_VOICE
        scene_audio = os.path.join(temp_dir, f"scene_{idx}.mp3")
        logger.info(f"[{req.tenant_id}] Escena {idx + 1} ('{scene.block}') — TTS con voz '{voice}'")
        await generate_speech_audio(scene.text, scene_audio, voice)
        scene_audios.append(scene_audio)

        scene_keywords = _keywords_from_prompt(scene.visual_prompt, req.keywords, f"{req.title} {scene.text}")
        logger.info(f"[{req.tenant_id}] Escena {idx + 1} — búsqueda Pexels con keywords {scene_keywords}")
        scene_clips = await asyncio.to_thread(download_pexels_videos, scene_keywords, temp_dir, per_page=2)
        scene_clip_lists.append(scene_clips)

        scene_durations.append(_scene_duration_seconds(scene, scene_audio))

    total_duration = _scenes_total_duration(scene_durations, req.max_duration_seconds)
    segments = [
        {
            "audio_path": audio_path,
            "video_paths": clip_paths,
            "duration": duration,
            "text": scene.text,
            "image_url": scene.image_url or req.product_image_url,
        }
        for audio_path, clip_paths, duration, scene in zip(scene_audios, scene_clip_lists, scene_durations, req.scenes)
    ]
    return await asyncio.to_thread(compose_scenes_video_moviepy, segments, output_mp4_path, total_duration)


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
