"""
Tests unitarios para el módulo de configuración.
"""

import json
import pytest
from src.core.config import Config, DEFAULT_CONFIG, load_config_from_env
from src.core.errors import ConfigurationError


class TestConfig:
    """Tests para la clase Config."""

    def test_config_por_defecto(self):
        config = Config()
        assert config.get("ollama_model") == "llama3.2:latest"
        assert config.get("teacher_speaker") == "auto"

    def test_config_personalizada(self):
        config_data = {"ollama_model": "llama3:latest", "verbose": True}
        config = Config(config_data)
        assert config.get("ollama_model") == "llama3:latest"
        assert config.get("verbose") is True

    def test_config_to_dict(self):
        config = Config()
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert "ollama_model" in config_dict

    def test_config_update(self):
        config = Config()
        config.update({"verbose": True})
        assert config.get("verbose") is True

    def test_config_modelo_invalido(self):
        with pytest.raises(ConfigurationError):
            Config({"ollama_model": ""})

    def test_config_log_level_invalido(self):
        with pytest.raises(ConfigurationError):
            Config({"log_level": "INVALIDO"})

    def test_config_input_source_no_json(self):
        with pytest.raises(ConfigurationError):
            Config({"input_source": "archivo.txt"})


class TestLoadConfigFromEnv:
    """Tests para load_config_from_env."""

    def test_carga_modelo_desde_env(self, monkeypatch):
        monkeypatch.setenv("GENERADOR_OLLAMA_MODEL", "llama3:latest")
        config = load_config_from_env()
        assert config["ollama_model"] == "llama3:latest"

    def test_carga_verbose_desde_env(self, monkeypatch):
        monkeypatch.setenv("GENERADOR_VERBOSE", "true")
        config = load_config_from_env()
        assert config["verbose"] is True

    def test_carga_opciones_ollama(self, monkeypatch):
        opciones = {"temperature": 0.5, "top_p": 0.9}
        monkeypatch.setenv("GENERADOR_OLLAMA_OPTIONS", json.dumps(opciones))
        config = load_config_from_env()
        assert config["ollama_options"]["temperature"] == 0.5

    def test_carga_input_source_desde_env(self, monkeypatch):
        monkeypatch.setenv("GENERADOR_INPUT_SOURCE", "transcripcion.json")
        config = load_config_from_env()
        assert config["input_source"] == "transcripcion.json"


class TestDefaultConfig:
    """Tests para la configuración por defecto."""

    def test_modelo_por_defecto(self):
        assert DEFAULT_CONFIG["ollama_model"] == "llama3.2:latest"

    def test_archivos_requeridos(self):
        required_keys = ["prompt_pdf", "structure_pdf", "json_prompt_pdf"]
        for key in required_keys:
            assert key in DEFAULT_CONFIG

    def test_opciones_ollama(self):
        assert "temperature" in DEFAULT_CONFIG["ollama_options"]
        assert "top_p" in DEFAULT_CONFIG["ollama_options"]
        assert "num_ctx" in DEFAULT_CONFIG["ollama_options"]

    def test_input_source_existe(self):
        assert "input_source" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["input_source"] == ""
