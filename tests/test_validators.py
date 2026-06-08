"""
Tests unitarios para el módulo de validación de datos.
"""

import pytest
from src.core.validators import validate_temporal_data, validate_config, TemporalDataItem
from src.core.errors import DataValidationError


class TestTemporalDataItem:
    """Tests para el modelo TemporalDataItem."""

    def test_item_valido(self):
        item = TemporalDataItem(
            Minuto_Clase=30,
            PSR=3.5,
            APSUD=75,
            PSU=60,
            PSUR=55,
            MR=25
        )
        assert item.Minuto_Clase == 30
        assert item.PSR == 3.5

    def test_item_con_opcionales(self):
        item = TemporalDataItem(
            Minuto_Clase=10,
            PSR=2.0,
            APSUD=80,
            PSU=70,
            PSUR=65,
            MR=20,
            ALD=5,
            SR=0.8,
            TTC=3.5,
            VSUR=10
        )
        assert item.ALD == 5
        assert item.TTC == 3.5

    def test_minuto_fuera_de_rango(self):
        with pytest.raises(ValueError):
            TemporalDataItem(
                Minuto_Clase=65,  # Fuera de rango (0-60)
                PSR=3.0,
                APSUD=50,
                PSU=50,
                PSUR=50,
                MR=50
            )

    def test_psr_fuera_de_rango(self):
        with pytest.raises(ValueError):
            TemporalDataItem(
                Minuto_Clase=30,
                PSR=6.0,  # Fuera de rango (1.0-5.0)
                APSUD=50,
                PSU=50,
                PSUR=50,
                MR=50
            )

    def test_porcentaje_fuera_de_rango(self):
        with pytest.raises(ValueError):
            TemporalDataItem(
                Minuto_Clase=30,
                PSR=3.0,
                APSUD=150,  # Fuera de rango (0-100)
                PSU=50,
                PSUR=50,
                MR=50
            )


class TestValidateTemporalData:
    """Tests para la función validate_temporal_data."""

    def test_lista_valida(self):
        datos = [
            {"Minuto_Clase": 0, "PSR": 2.0, "APSUD": 50, "PSU": 40, "PSUR": 35, "MR": 60},
            {"Minuto_Clase": 30, "PSR": 4.0, "APSUD": 85, "PSU": 75, "PSUR": 70, "MR": 20}
        ]
        resultado = validate_temporal_data(datos)
        assert len(resultado) == 2
        assert resultado[0]["Minuto_Clase"] == 0

    def test_string_json_valido(self):
        import json
        datos_json = json.dumps([
            {"Minuto_Clase": 0, "PSR": 2.0, "APSUD": 50, "PSU": 40, "PSUR": 35, "MR": 60}
        ])
        resultado = validate_temporal_data(datos_json)
        assert len(resultado) == 1

    def test_lista_vacia(self):
        with pytest.raises(DataValidationError):
            validate_temporal_data([])

    def test_no_lista(self):
        with pytest.raises(DataValidationError):
            validate_temporal_data({"Minuto_Clase": 0})

    def test_item_invalido_se_omite(self):
        datos = [
            {"Minuto_Clase": 0, "PSR": 2.0, "APSUD": 50, "PSU": 40, "PSUR": 35, "MR": 60},
            {"Minuto_Clase": 70, "PSR": 2.0, "APSUD": 50, "PSU": 40, "PSUR": 35, "MR": 60},  # Inválido
            {"Minuto_Clase": 30, "PSR": 4.0, "APSUD": 85, "PSU": 75, "PSUR": 70, "MR": 20}
        ]
        resultado = validate_temporal_data(datos)
        assert len(resultado) == 2  # Se omite el inválido

    def test_json_invalido(self):
        with pytest.raises(DataValidationError):
            validate_temporal_data("no es json")


class TestValidateConfig:
    """Tests para la función validate_config."""

    def test_config_valida(self):
        config = {
            "input_pdf": "PruebaInforme.pdf",
            "prompt_pdf": "PROMPTMEJORADO.pdf",
            "structure_pdf": "FORMATO_SALIDA.pdf",
            "json_prompt_pdf": "PROMPT_JSON.pdf",
            "output_pdf": "salida.pdf",
            "output_json": "salida.json",
            "ollama_model": "llama3.2:latest"
        }
        # No debería lanzar excepción
        validate_config(config)

    def test_config_falta_parametro(self):
        config = {
            "input_pdf": "PruebaInforme.pdf"
            # Faltan otros parámetros requeridos
        }
        with pytest.raises(DataValidationError):
            validate_config(config)

    def test_config_opciones_invalidas(self):
        config = {
            "input_pdf": "PruebaInforme.pdf",
            "prompt_pdf": "PROMPTMEJORADO.pdf",
            "structure_pdf": "FORMATO_SALIDA.pdf",
            "json_prompt_pdf": "PROMPT_JSON.pdf",
            "output_pdf": "salida.pdf",
            "output_json": "salida.json",
            "ollama_model": "llama3.2:latest",
            "ollama_options": {
                "temperature": 2.0  # Fuera de rango
            }
        }
        with pytest.raises(DataValidationError):
            validate_config(config)
