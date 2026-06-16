"""
Punto de entrada principal para el generador de informes pedagógicos.
"""

import sys
from .core.config import get_config
from .core.errors import (
    setup_logging, get_logger,
    PDFExtractionError, OllamaGenerationError,
    PDFGenerationError, JSONGenerationError,
    DataValidationError, ConfigurationError
)
from .core.generador_texto_ollama import generar_informe_completo

def main() -> int:
    """
    Función principal del generador de informes pedagógicos.

    Returns:
        Código de salida (0 para éxito, 1 para error)
    """
    try:
        # Configurar el sistema
        config = get_config()
        setup_logging(config.to_dict())
        logger = get_logger("main")

        logger.info("Iniciando generación de informe pedagógico")
        
        config_dict = config.to_dict().copy()
        claves_sensibles = ["password", "secret", "token", "api_key", "database_url"]
        
        for clave in config_dict:
            if any(palabra in clave.lower() for palabra in claves_sensibles):
                config_dict[clave] = "********"
    
        logger.debug(f"Configuración (filtrada): {config_dict}")

        # Generar el informe
        generar_informe_completo(config)

        logger.info("Generación de informe completada con éxito")
        return 0

    except (DataValidationError, PDFExtractionError, OllamaGenerationError,
            PDFGenerationError, JSONGenerationError, ConfigurationError,
            FileNotFoundError) as e:
        logger = get_logger("main")
        logger.error(f"Error en la ejecución del programa: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())