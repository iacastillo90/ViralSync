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
import shutil
import tempfile
import logging
import asyncio
import requests
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import edge_tts
from minio import Minio

# Configuración de Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("video_renderer")

app = FastAPI(
    title="ViralSync Faceless Video Renderer Microservice",
    version="1.0.0",
    description="Motor de renderizado autónomo de video a costo cero con Edge-TTS, Pexels y MoviePy",
)

# Variables de Entorno
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000").replace("http://", "").replace("https://", "")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "viralsync-media")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "es-MX-JorgeNeural")


class RenderRequest(BaseModel):
    title: str = Field(..., example="3 Errores al Escalar B2B")
    script_text: str = Field(..., example="El error principal no es la falta de herramientas, sino intentar abarcar todo sin foco.")
    keywords: List[str] = Field(default_factory=lambda: ["business", "technology", "office"])
    tenant_id: Optional[str] = Field(default="default_tenant")


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


def download_pexels_videos(keywords: List[str], temp_dir: str) -> List[str]:
    """Descarga de 3 a 4 clips de video verticales en formato HD usando Pexels API."""
    downloaded_files = []

    if not PEXELS_API_KEY:
        logger.warning("PEXELS_API_KEY no configurada. Generando aviso para clips vacíos.")
        return downloaded_files

    headers = {"Authorization": PEXELS_API_KEY}
    query = "+".join(keywords) if keywords else "business"
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=4"

    try:
        response = requests.get(url, headers=headers, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            for idx, video in enumerate(videos[:4]):
                video_files = video.get("video_files", [])
                # Buscar el mejor archivo de video vertical HD
                hd_file = next((vf for vf in video_files if vf.get("height", 0) >= 1280), None) or video_files[0] if video_files else None
                if hd_file and hd_file.get("link"):
                    video_url = hd_file["link"]
                    file_path = os.path.join(temp_dir, f"pexels_clip_{idx}.mp4")
                    logger.info(f"Descargando clip de Pexels {idx + 1}: {video_url[:50]}...")
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
    """Compone y renderiza el video vertical 9:16 (1080x1920) combinando audios y clips con MoviePy."""
    from moviepy.editor import AudioFileClip, VideoFileClip, concatenate_videoclips, ColorClip

    logger.info("Componiendo video final con MoviePy...")
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration

    clip_objects = []
    if video_paths:
        duration_per_clip = audio_duration / len(video_paths)
        for path in video_paths:
            try:
                v_clip = VideoFileClip(path)
                # Recortar duración del clip
                sub_clip = v_clip.subclip(0, min(v_clip.duration, duration_per_clip))
                # Redimensionar / Recortar a 9:16 (1080x1920)
                sub_clip = sub_clip.resize(height=1920)
                if sub_clip.w > 1080:
                    x_center = sub_clip.w / 2
                    sub_clip = sub_clip.crop(x1=x_center - 540, width=1080)
                clip_objects.append(sub_clip)
            except Exception as exc:
                logger.warning(f"Error procesando clip {path}: {exc}")

    # Fallback si no se pudieron cargar clips de Pexels
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
        preset="ultrafast",
        logger=None,
    )

    # Cerrar clips de MoviePy para liberar memoria RAM y handles
    audio_clip.close()
    final_video.close()
    for c in clip_objects:
        c.close()

    return audio_duration


def upload_to_minio(file_path: str, tenant_id: str) -> str:
    """Sube el archivo final .mp4 a MinIO y retorna la URL pública del objeto."""
    logger.info(f"Conectando a MinIO en {MINIO_ENDPOINT}...")
    minio_client = Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        secure=False,
    )

    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)

    object_name = f"{tenant_id}/faceless_output_{os.path.basename(file_path)}"
    minio_client.fput_object(MINIO_BUCKET, object_name, file_path, content_type="video/mp4")

    public_url = f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{object_name}"
    logger.info(f"Video subido exitosamente a MinIO: {public_url}")
    return public_url


@app.post("/render", response_model=RenderResponse, status_code=status.HTTP_201_CREATED)
async def render_video_endpoint(req: RenderRequest):
    """
    Endpoint principal para renderizar videos faceless a costo cero.
    Garantiza la eliminación de todos los archivos temporales post-renderizado (Zero Waste).
    """
    temp_dir = tempfile.mkdtemp(prefix="viralsync_render_")
    audio_path = os.path.join(temp_dir, "speech.mp3")
    output_mp4_path = os.path.join(temp_dir, "final_output.mp4")

    logger.info(f"[{req.tenant_id}] Iniciando renderizado faceless: '{req.title}'")

    try:
        # 1. Generar audio con Edge-TTS
        await generate_speech_audio(req.script_text, audio_path)

        # 2. Descargar clips de Pexels API
        downloaded_clips = download_pexels_videos(req.keywords, temp_dir)

        # 3. Componer video con MoviePy
        duration = compose_video_moviepy(audio_path, downloaded_clips, output_mp4_path)

        # 4. Subir a MinIO
        video_url = upload_to_minio(output_mp4_path, req.tenant_id)

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
        # CRÍTICO PARA EL DISCO: Limpieza absoluta de la carpeta y archivos temporales
        logger.info(f"Ejecutando limpieza estricta de disco (Zero Waste) en {temp_dir}...")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info("Carpeta y archivos temporales eliminados del disco satisfactoriamente.")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "faceless_video_renderer"}
