"""
json2video_client.py

Cliente API para el servicio de renderizado de video en la nube JSON2Video v2.
Crea películas con formato vertical (9:16), añade subtítulos dinámicos y audio narrado.
"""

import os
import time
import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class JSON2VideoClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("JSON2VIDEO_API_KEY", "")
        self.pexels_api_key = os.getenv("PEXELS_API_KEY", "")
        self.endpoint = "https://api.json2video.com/v2/movies"

    def _fetch_pexels_video_urls(self, keywords: List[str]) -> List[str]:
        """Consulta la API de Pexels para obtener URLs de descarga directa de clips verticales."""
        video_urls = []
        if not self.pexels_api_key:
            logger.warning("PEXELS_API_KEY no configurada. Usando videos stock por defecto.")
            return video_urls

        query = "+".join(keywords) if keywords else "business"
        url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=4"
        headers = {"Authorization": self.pexels_api_key}

        try:
            with httpx.Client() as client:
                response = client.get(url, headers=headers, timeout=12.0)
                if response.status_code == 200:
                    data = response.json()
                    videos = data.get("videos", [])
                    for video in videos:
                        video_files = video.get("video_files", [])
                        # Buscar un archivo con resolución razonable (720p/1080p)
                        light_file = next(
                            (vf for vf in video_files if 720 <= vf.get("height", 0) <= 1080),
                            video_files[0] if video_files else None
                        )
                        if light_file and light_file.get("link"):
                            video_urls.append(light_file["link"])
                else:
                    logger.warning(f"Pexels API respondió con código {response.status_code}")
        except Exception as exc:
            logger.error(f"Error consultando Pexels API: {exc}")

        return video_urls

    def render_video(
        self,
        script: Dict[str, Any],
        keywords: List[str],
        tenant_id: str,
        title: str = "ViralSync Marketing Video",
        voice: str = "es-MX-JorgeNeural",
    ) -> str:
        """
        Envía un payload de video a JSON2Video v2 API y realiza polling hasta que termine.
        Usa elementos de tipo 'voice' (Azure TTS) para no depender de almacenamiento local expuesto.
        Retorna la URL final del video .mp4 hospedado en la nube.

        ``voice`` (REQ-VOICE-03): voz Azure a usar en cada elemento voice; la
        persona del guion la inyecta el worker de render (json2video_voice).
        """
        if not self.api_key:
            raise ValueError("JSON2VIDEO_API_KEY no está configurada")

        # 1. Obtener URLs de videos de Pexels
        pexels_urls = self._fetch_pexels_video_urls(keywords)

        # 2. Estructurar las escenas con voz y subtítulos
        blocks = [
            {"text": script.get("gancho_0_5s", ""), "comment": "Hook"},
            {"text": script.get("contexto_5_30s", ""), "comment": "Context"},
            {"text": script.get("moraleja_30_50s", ""), "comment": "Morale"},
            {"text": script.get("cta_50_60s", ""), "comment": "CTA"},
        ]

        scenes = []
        for idx, block in enumerate(blocks):
            if not block["text"]:
                continue

            # Seleccionar un clip de video (reutilización circular si hay pocos clips)
            video_src = pexels_urls[idx % len(pexels_urls)] if pexels_urls else "https://assets.json2video.com/templates/assets/stock-1.mp4"

            scene_elements = [
                {
                    "type": "video",
                    "src": video_src,
                    "settings": {
                        "object-fit": "cover"
                    }
                },
                {
                    "type": "voice",
                    "text": block["text"],
                    "model": "azure",
                    "voice": voice
                },
                {
                    "type": "text",
                    "text": block["text"],
                    "settings": {
                        "font-family": "Outfit",
                        "font-size": "4.5vw",
                        "color": "#FFFFFF",
                        "text-align": "center",
                        "background-color": "rgba(15, 23, 42, 0.75)",
                        "border-radius": "12px",
                        "padding": "16px 24px",
                        "width": "80vw",
                        "position": "absolute",
                        "bottom": "15%",
                        "left": "10%"
                    }
                }
            ]

            # Al omitir 'duration' en la escena, JSON2Video calcula la duración
            # adaptándose al elemento más largo, en este caso el TTS 'voice'.
            scenes.append({
                "comment": block["comment"],
                "elements": scene_elements
            })

        # 3. Ensamblar payload completo
        payload = {
            "resolution": "instagram-story",  # 9:16 vertical
            "quality": "high",
            "draft": False,  # Sin marcas de agua
            "scenes": scenes
        }

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        logger.info(f"[{tenant_id}] Despachando película a JSON2Video v2 API...")
        try:
            with httpx.Client() as client:
                response = client.post(self.endpoint, json=payload, headers=headers, timeout=30.0)
                if response.status_code != 200:
                    logger.error(f"Error en JSON2Video API POST ({response.status_code}): {response.text}")
                    raise RuntimeError(f"JSON2Video POST failed with status {response.status_code}")

                data = response.json()
                if not data.get("success"):
                    raise RuntimeError(f"JSON2Video API returned error: {data}")

                project_id = data.get("project")
                if not project_id:
                    raise RuntimeError("No se recibió 'project' ID de JSON2Video")

                logger.info(f"[{tenant_id}] Renderizado iniciado (Project ID: {project_id}). Realizando polling...")

                # 4. Polling bloqueante en Celery (Máx 300 segundos)
                max_attempts = 60  # 60 intentos * 5s = 300s
                for attempt in range(max_attempts):
                    time.sleep(5)
                    poll_response = client.get(f"{self.endpoint}?project={project_id}", headers=headers, timeout=15.0)
                    if poll_response.status_code == 200:
                        poll_data = poll_response.json()
                        movie_data = poll_data.get("movie", {})
                        status = movie_data.get("status")
                        logger.info(f"[{tenant_id}] Estado JSON2Video (intento {attempt+1}/{max_attempts}): {status}")

                        if status == "done":
                            video_url = movie_data.get("url")
                            if video_url:
                                logger.info(f"[{tenant_id}] Renderizado en la nube finalizado: {video_url}")
                                return video_url
                            else:
                                raise RuntimeError("JSON2Video devolvió 'done' pero falta 'url' del video")
                        elif status == "error":
                            raise RuntimeError(f"Fallo de renderizado en JSON2Video: {movie_data.get('message')}")
                    else:
                        logger.warning(f"Fallo en polling JSON2Video (intento {attempt+1}): {poll_response.status_code}")

                raise TimeoutError("Excedido el límite de tiempo de 300 segundos esperando por JSON2Video")
        except Exception as exc:
            logger.error(f"Error orquestando la llamada a JSON2Video: {exc}")
            raise
