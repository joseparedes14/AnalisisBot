"""
Módulo de validación de datos para el generador de informes pedagógicos.

Este módulo proporciona:
- Validación de esquemas de datos
- Validación de parámetros de entrada
- Validación de estructuras de datos temporales
"""

from typing import Dict, Any, List, Union, Optional
from pydantic import BaseModel, field_validator, ValidationError
from .errors import DataValidationError, get_logger

# Configurar logger
logger = get_logger(__name__)

class TemporalDataItem(BaseModel):
    """Modelo para validar un item de datos temporales."""
    Minuto_Clase: int
    PSR: float
    APSUD: int
    PSU: int
    PSUR: int
    MR: int
    ALD: Optional[int] = None
    SR: Optional[float] = None
    TTC: Optional[float] = None
    VSUR: Optional[int] = None

    @field_validator('Minuto_Clase')
    @classmethod
    def validate_minuto_clase(cls, v):
        if not 0 <= v <= 60:
            raise ValueError('Minuto_Clase debe estar entre 0 y 60')
        return v

    @field_validator('PSR')
    @classmethod
    def validate_psr(cls, v):
        if not 1.0 <= v <= 5.0:
            raise ValueError('PSR debe estar entre 1.0 y 5.0')
        return v

    @field_validator('APSUD', 'PSU', 'PSUR', 'MR')
    @classmethod
    def validate_percentage(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Los valores porcentuales deben estar entre 0 y 100')
        return v

def validate_temporal_data(data: Union[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Valida datos temporales y los convierte a una lista de diccionarios.

    Args:
        data: Datos temporales en formato JSON string o lista de diccionarios

    Returns:
        Lista de diccionarios con los datos validados

    Raises:
        DataValidationError: Si los datos no son válidos
    """
    import json

    try:
        # Convertir string JSON a lista si es necesario
        if isinstance(data, str):
            data = json.loads(data)

        # Validar que sea una lista
        if not isinstance(data, list):
            raise DataValidationError("Los datos temporales deben ser una lista")

        # Validar cada item con Pydantic
        validated_data = []
        for item in data:
            try:
                validated_item = TemporalDataItem(**item).model_dump()
                validated_data.append(validated_item)
            except ValidationError as e:
                logger.warning(f"Item de datos temporales inválido: {item}. Error: {e}")
                continue

        if not validated_data:
            raise DataValidationError("No se encontraron datos temporales válidos")

        return validated_data

    except json.JSONDecodeError as e:
        raise DataValidationError(f"Error al parsear datos temporales JSON: {e}")
    except Exception as e:
        raise DataValidationError(f"Error al validar datos temporales: {e}")

def validate_config(config: Dict[str, Any]) -> None:
    """
    Valida la configuración del sistema.

    Args:
        config: Diccionario de configuración

    Raises:
        DataValidationError: Si la configuración es inválida
    """
    required_keys = [
        'input_source', 'prompt_pdf', 'structure_pdf', 'json_prompt_pdf',
        'output_pdf', 'output_json', 'ollama_model'
    ]

    for key in required_keys:
        if key not in config or not config[key]:
            raise DataValidationError(f"Falta el parámetro requerido: {key}")

    # Validar que input_source sea un JSON
    if not config['input_source'].endswith('.json'):
        raise DataValidationError("input_source debe ser un archivo JSON")

    # Validar que el archivo de entrada exista
    from pathlib import Path

    if not Path(config['input_source']).exists():
        logger.warning(f"El archivo {config['input_source']} no existe, pero se continuará con la ejecución")

    # Validar opciones de Ollama
    if 'ollama_options' in config and config['ollama_options']:
        options = config['ollama_options']
        if not isinstance(options, dict):
            raise DataValidationError("ollama_options debe ser un diccionario")

        if 'temperature' in options and not 0.0 <= options['temperature'] <= 1.0:
            raise DataValidationError("temperature debe estar entre 0.0 y 1.0")

        if 'top_p' in options and not 0.0 <= options['top_p'] <= 1.0:
            raise DataValidationError("top_p debe estar entre 0.0 y 1.0")

        if 'num_ctx' in options and options['num_ctx'] < 1024:
            raise DataValidationError("num_ctx debe ser al menos 1024")

        if 'repeat_penalty' in options and options['repeat_penalty'] < 0.0:
            raise DataValidationError("repeat_penalty debe ser mayor o igual a 0.0")