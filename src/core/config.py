"""
Módulo de configuración para el generador de informes pedagógicos.

Este módulo proporciona:
- Argumentos de línea de comandos
- Variables de entorno
- Configuración por defecto
- Validación de configuración
"""

import argparse
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

from .errors import ConfigurationError

# Configuración por defecto
DEFAULT_CONFIG = {
    "input_source": "",  # Ruta al JSON de transcripción
    "teacher_speaker": "auto",  # "auto" para detectar automáticamente
    "prompt_pdf": "PROMPTMEJORADO.pdf",
    "structure_pdf": "FORMATO_SALIDA.pdf",
    "json_prompt_pdf": "PROMPT_JSON.pdf",
    "output_pdf": "Respuesta_Agente_Ollama.pdf",
    "output_json": "data_auditoria.json",
    "ollama_model": "llama3.2:latest",
    "ollama_options": {
        "temperature": 0.1,
        "top_p": 0.8,
        "num_ctx": 8192,
        "repeat_penalty": 1.1
    },
    "log_level": "INFO",
    "log_file": "generador.log",
    "verbose": False
}

class Config:
    """
    Clase para manejar la configuración del sistema.
    """

    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        """
        Inicializa la configuración con valores por defecto o proporcionados.

        Args:
            config_data: Diccionario con configuración personalizada
        """
        self.config = DEFAULT_CONFIG.copy()
        if config_data:
            self.config.update(config_data)

        # Validar configuración
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Valida la configuración actual.

        Raises:
            ConfigurationError: Si la configuración es inválida
        """
        # Validar input_source (debe ser JSON)
        input_source = self.config.get("input_source", "")
        if input_source and not input_source.endswith(".json"):
            raise ConfigurationError("input_source debe ser un archivo JSON")

        # Validar rutas de archivos PDF de configuración
        for key in ["prompt_pdf", "structure_pdf", "json_prompt_pdf"]:
            if not isinstance(self.config[key], str) or not self.config[key].strip():
                raise ConfigurationError(f"El valor de {key} debe ser una cadena no vacía")

        # Validar modelo de Ollama
        if not isinstance(self.config["ollama_model"], str) or not self.config["ollama_model"].strip():
            raise ConfigurationError("El modelo de Ollama debe ser una cadena no vacía")

        # Validar opciones de Ollama
        if not isinstance(self.config["ollama_options"], dict):
            raise ConfigurationError("Las opciones de Ollama deben ser un diccionario")

        # Validar nivel de logging
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.config["log_level"] not in valid_log_levels:
            raise ConfigurationError(f"Nivel de log inválido. Debe ser uno de: {valid_log_levels}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración.

        Args:
            key: Clave de configuración
            default: Valor por defecto si la clave no existe

        Returns:
            Valor de configuración o default
        """
        return self.config.get(key, default)

    def update(self, updates: Dict[str, Any]) -> None:
        """
        Actualiza la configuración con nuevos valores.

        Args:
            updates: Diccionario con valores a actualizar
        """
        self.config.update(updates)
        self._validate_config()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la configuración a un diccionario.

        Returns:
            Diccionario con la configuración actual
        """
        return self.config.copy()

def load_config_from_file(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Carga configuración desde un archivo JSON.

    Args:
        config_path: Ruta al archivo de configuración

    Returns:
        Diccionario con la configuración cargada

    Raises:
        ConfigurationError: Si el archivo no existe o no es válido
    """
    if not config_path:
        # Buscar archivo de configuración en ubicaciones comunes
        possible_paths = [
            "config.json",
            ".generador_config.json",
            os.path.expanduser("~/.generador_config.json"),
            os.path.join(os.path.dirname(__file__), "config.json")
        ]

        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break

    if not config_path or not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise ConfigurationError(f"Error al cargar configuración desde {config_path}: {e}")

def load_config_from_env() -> Dict[str, Any]:
    """
    Carga configuración desde variables de entorno.

    Returns:
        Diccionario con la configuración cargada
    """
    config = {}

    # Mapear variables de entorno a claves de configuración
    env_mapping = {
        "GENERADOR_INPUT_SOURCE": "input_source",
        "GENERADOR_TEACHER_SPEAKER": "teacher_speaker",
        "GENERADOR_PROMPT_PDF": "prompt_pdf",
        "GENERADOR_STRUCTURE_PDF": "structure_pdf",
        "GENERADOR_JSON_PROMPT_PDF": "json_prompt_pdf",
        "GENERADOR_OUTPUT_PDF": "output_pdf",
        "GENERADOR_OUTPUT_JSON": "output_json",
        "GENERADOR_OLLAMA_MODEL": "ollama_model",
        "GENERADOR_LOG_LEVEL": "log_level",
        "GENERADOR_LOG_FILE": "log_file",
        "GENERADOR_VERBOSE": "verbose"
    }

    for env_var, config_key in env_mapping.items():
        if env_var in os.environ:
            value = os.environ[env_var]

            # Convertir tipos según la clave
            if config_key == "verbose":
                config[config_key] = value.lower() in ('true', '1', 't', 'y', 'yes')
            else:
                config[config_key] = value

    # Manejar opciones de Ollama
    if "GENERADOR_OLLAMA_OPTIONS" in os.environ:
        try:
            config["ollama_options"] = json.loads(os.environ["GENERADOR_OLLAMA_OPTIONS"])
        except json.JSONDecodeError:
            pass

    return config

def parse_args() -> argparse.Namespace:
    """
    Parsea los argumentos de línea de comandos.

    Returns:
        Objeto Namespace con los argumentos parseados
    """
    parser = argparse.ArgumentParser(
        description='Generador de informes pedagógicos con Ollama',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Archivos de entrada
    parser.add_argument('--input', '-i', required=True,
                        help='Ruta al archivo JSON de transcripción')
    parser.add_argument('--teacher',
                        help='Speaker del teacher (default: auto-detect)')
    parser.add_argument('--prompt', '-p',
                        help='Archivo PDF con el prompt de la tarea')
    parser.add_argument('--structure', '-s',
                        help='Archivo PDF con las instrucciones de estructura')
    parser.add_argument('--json-prompt', '-j',
                        help='Archivo PDF con el prompt para extracción JSON')

    # Archivos de salida
    parser.add_argument('--output-pdf', '-o',
                        help='Archivo PDF de salida')
    parser.add_argument('--output-json',
                        help='Archivo JSON de salida')

    # Configuración de Ollama
    parser.add_argument('--model', '-m',
                        help='Modelo de Ollama a utilizar')
    parser.add_argument('--temperature', type=float,
                        help='Temperatura para la generación')
    parser.add_argument('--top-p', type=float,
                        help='Top-p para la generación')
    parser.add_argument('--num-ctx', type=int,
                        help='Contexto máximo para el modelo')
    parser.add_argument('--repeat-penalty', type=float,
                        help='Penalización por repetición')

    # Configuración de logging
    parser.add_argument('--log-level',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Nivel de logging')
    parser.add_argument('--log-file',
                        help='Archivo de log')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Modo verbose')

    # Configuración
    parser.add_argument('--config', '-c',
                        help='Archivo de configuración JSON')

    return parser.parse_args()

def get_config() -> Config:
    """
    Obtiene la configuración combinando todas las fuentes.

    Returns:
        Objeto Config con la configuración combinada
    """
    # Parsear argumentos de línea de comandos
    args = parse_args()

    # Cargar configuración desde archivo
    config_from_file = {}
    if args.config:
        config_from_file = load_config_from_file(args.config)
    else:
        config_from_file = load_config_from_file()

    # Cargar configuración desde variables de entorno
    config_from_env = load_config_from_env()

    # Combinar configuraciones (el orden importa: los últimos tienen prioridad)
    combined_config = DEFAULT_CONFIG.copy()
    combined_config.update(config_from_file)
    combined_config.update(config_from_env)

    # Convertir argumentos de línea de comandos a diccionario
    args_dict = vars(args)

    # Filtrar argumentos que son None (no especificados)
    args_dict = {k: v for k, v in args_dict.items() if v is not None}

    # Mapear nombres de argumentos a claves de configuración
    arg_mapping = {
        'input': 'input_source',
        'teacher': 'teacher_speaker',
        'prompt': 'prompt_pdf',
        'structure': 'structure_pdf',
        'json_prompt': 'json_prompt_pdf',
        'output_pdf': 'output_pdf',
        'output_json': 'output_json',
        'model': 'ollama_model',
        'temperature': 'temperature',
        'top_p': 'top_p',
        'num_ctx': 'num_ctx',
        'repeat_penalty': 'repeat_penalty',
        'log_level': 'log_level',
        'log_file': 'log_file',
        'verbose': 'verbose'
    }

    # Actualizar configuración con argumentos de línea de comandos
    for arg_name, config_key in arg_mapping.items():
        if arg_name in args_dict:
            # Manejo especial para opciones de Ollama
            if arg_name in ['temperature', 'top_p', 'num_ctx', 'repeat_penalty']:
                if 'ollama_options' not in combined_config:
                    combined_config['ollama_options'] = {}
                combined_config['ollama_options'][arg_name] = args_dict[arg_name]
            else:
                combined_config[config_key] = args_dict[arg_name]

    return Config(combined_config)