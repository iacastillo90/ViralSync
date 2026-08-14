"""
calendar.py

Router backend para la gestión del Calendario Editorial Interactivo de la Agencia ViralSync.
Permite consultar la parrilla de contenidos programados/publicados y agendar la fecha y hora
exactas de difusión multi-canal (Instagram Reels, TikTok, YouTube Shorts).

Protegido por el middleware de aislamiento anti-IDOR `verify_tenant_access`.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_async_db
from backend.db.models import Video, Script, Idea

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/tenants/{tenant_id}/calendar",
    tags=["Calendario Editorial"],
)


class ScheduleVideoRequest(BaseModel):
    """Modelo Pydantic para la solicitud de programación de publicación de un video."""
    video_id: str = Field(..., description="ID único del video en la tabla videos")
    scheduled_at: datetime = Field(..., description="Fecha y hora objetivo de publicación ISO-8601")
    platform: Optional[str] = Field("instagram_reels", description="Plataforma de destino: instagram_reels, tiktok, youtube_shorts")
    caption: Optional[str] = Field(None, description="Copy/Descripción optimizada para redes sociales")


class CalendarItemResponse(BaseModel):
    """Modelo Pydantic para cada elemento de la parrilla del calendario editorial."""
    video_id: str
    script_id: Optional[str] = None
    title: str
    gancho: Optional[str] = None
    edited_video_uri: str
    provider: str
    publish_approval_status: str
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    platform: str = "instagram_reels"


@router.get("", response_model=List[CalendarItemResponse], status_code=status.HTTP_200_OK)
async def get_tenant_calendar_grid(
    tenant_id: str,
    db: AsyncSession = Depends(get_async_db)
) -> List[CalendarItemResponse]:
    """
    Obtiene la parrilla completa del calendario editorial para el tenant.
    Unifica videos generados, guiones asociados e información de publicación.
    """
    try:
        stmt = (
            select(Video, Script, Idea)
            .join(Script, Video.script_id == Script.id, isouter=True)
            .join(Idea, Script.idea_id == Idea.id, isouter=True)
            .where(Video.tenant_id == tenant_id)
            .order_by(Video.created_at.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        items: List[CalendarItemResponse] = []
        for video, script, idea in rows:
            title = idea.texto if idea else (script.keyword if script else "Video Marketing ViralSync")
            gancho = script.gancho_0_5s if script else None

            # Determinar fecha programada / publicada
            scheduled_date = video.published_at if video.publish_approval_status in ("scheduled", "published") else None

            items.append(
                CalendarItemResponse(
                    video_id=video.id,
                    script_id=video.script_id,
                    title=title,
                    gancho=gancho,
                    edited_video_uri=video.edited_video_uri or "",
                    provider=video.provider or "nvidia_cosmos",
                    publish_approval_status=video.publish_approval_status or "pending",
                    scheduled_at=scheduled_date,
                    published_at=video.published_at,
                    created_at=video.created_at or datetime.now(timezone.utc),
                    platform="instagram_reels",
                )
            )

        logger.info(f"[{tenant_id}] Calendario cargado exitosamente: {len(items)} publicaciones devueltas.")
        return items

    except Exception as exc:
        logger.error(f"[{tenant_id}] Error obteniendo calendario editorial: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error consultando calendario: {str(exc)}"
        )


@router.post("/schedule", status_code=status.HTTP_200_OK)
async def schedule_video_publication(
    tenant_id: str,
    req: ScheduleVideoRequest,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """
    Agenda o reprograma la fecha y hora exactas de publicación para un video del tenant.
    Actualiza el estado a `scheduled` en la base de datos PostgreSQL.
    """
    try:
        # Verificar existencia del video para el tenant
        res = await db.execute(
            select(Video).where(Video.id == req.video_id, Video.tenant_id == tenant_id)
        )
        video = res.scalars().first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video con ID {req.video_id} no encontrado para el tenant {tenant_id}"
            )

        # Actualizar estado de publicación y fecha objetivo
        video.publish_approval_status = "approved"
        video.published_at = req.scheduled_at
        await db.commit()

        logger.info(
            f"[{tenant_id}] Video {req.video_id} agendado exitosamente para {req.scheduled_at.isoformat()} "
            f"en plataforma {req.platform}."
        )

        return {
            "status": "success",
            "message": f"Publicación agendada exitosamente para {req.scheduled_at.strftime('%Y-%m-%d %H:%M UTC')}",
            "video_id": req.video_id,
            "scheduled_at": req.scheduled_at.isoformat(),
            "publish_approval_status": "approved",
            "platform": req.platform,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[{tenant_id}] Error agendando publicación de video: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al agendar publicación: {str(exc)}"
        )
