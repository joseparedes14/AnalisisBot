"""
Módulo de manejo de errores y logging para el generador de informes pedagógicos.

Este módulo proporciona:
- Excepciones personalizadas
- Sistema de logging configurado
- Funciones de manejo de errores
"""

import logging
import logging.config
from typing import Optional, Dict, Any

# Excepciones personalizadas
class PDFExtractionError(Exception):
    """Error al extraer texto de un archivo PDF."""
    pass

class OllamaGenerationError(Exception):
    """Error al generar texto con Ollama."""
    pass

class PDFGenerationError(Exception):
    """Error al generar un archivo PDF."""
    pass

class JSONGenerationError(Exception):
    """Error al generar o procesar JSON."""
    pass

class DataValidationError(Exception):
    """Error de validación de datos."""
    pass

class ConfigurationError(Exception):
    """Error en la configuración del sistema."""
    pass

def setup_logging(config: Dict[str, Any]) -> None:
    """
    Configura el sistema de logging.

    Args:
        config: Diccionario con la configuración de logging
    """
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "verbose": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": config.get("log_level", "INFO"),
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.FileHandler",
                "formatter": "verbose",
                "level": config.get("log_level", "INFO"),
                "filename": config.get("log_file", "generador.log"),
                "encoding": "utf8"
            }
        },
        "root": {
            "handlers": ["console", "file"],
            "level": config.get("log_level", "INFO"),
        }
    }

    # Si verbose está activado, usar el formatter verbose para consola
    if config.get("verbose", False):
        log_config["handlers"]["console"]["formatter"] = "verbose"

    logging.config.dictConfig(log_config)

def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger con el nombre especificado.

    Args:
        name: Nombre del logger

    Returns:
        Logger configurado
    """
    return logging.getLogger(name)

def log_exception(logger: logging.Logger, exc: Exception, message: str,
                  extra: Optional[Dict[str, Any]] = None) -> None:
    """
    Registra una excepción con información detallada.

    Args:
        logger: Logger a utilizar
        exc: Excepción a registrar
        message: Mensaje descriptivo
        extra: Información adicional para el log
    """
    logger.error(f"{message} | Tipo: {type(exc).__name__} | Detalle: {exc}", exc_info=True)