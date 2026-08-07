"""
logging_config.py

Módulo de configuración de logging estructurado JSON para ViralSync Backend.
En entorno de producción ('prod' / 'staging'), formatea todos los logs en JSON estructurado.
En entorno de desarrollo ('dev'), utiliza un formateador legible por humanos.
"""

import os
import json
import logging
import logging.config
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formatter que emite registros de log como objetos JSON estructurados."""

    def format(self, record: logging.LogRecord) -> str:
        log_object = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno,
        }

        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "tenant_id"):
            log_object["tenant_id"] = getattr(record, "tenant_id")

        return json.dumps(log_object, ensure_ascii=False)


def setup_logging():
    """Inicializa la configuración de logging dictConfig para la aplicación."""
    agency_env = os.getenv("AGENCY_ENV", "dev").lower()
    is_prod = agency_env in ("prod", "production", "staging")

    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "standard": {
                "format": format_str,
            },
        },
        "handlers": {
            "default": {
                "level": "INFO",
                "formatter": "json" if is_prod else "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["default"],
                "level": "INFO",
                "propagate": True,
            },
            "uvicorn": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "backend": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "agents": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)
