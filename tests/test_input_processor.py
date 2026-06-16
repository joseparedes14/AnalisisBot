"""
Tests unitarios para el modulo de procesamiento de entrada.
"""

import json
import pytest
from src.core.input_processor import (
    procesar_json_transcripcion,
    TranscriptAnalyzer,
)
from src.core.errors import DataValidationError


# Datos de prueba
SEGMENTS_EJEMPLO = [
    {
        "start": 0.0,
        "end": 5.0,
        "text": "Buenos dias a todos.",
        "speaker": "SPEAKER_00",
        "words": [
            {"word": "Buenos", "start": 0.0, "end": 0.5, "score": 0.9, "speaker": "SPEAKER_00"},
            {"word": "dias", "start": 0.5, "end": 1.0, "score": 0.85, "speaker": "SPEAKER_00"},
            {"word": "a", "start": 1.0, "end": 1.1, "score": 0.8, "speaker": "SPEAKER_00"},
            {"word": "todos.", "start": 1.1, "end": 1.5, "score": 0.88, "speaker": "SPEAKER_00"},
        ]
    },
    {
        "start": 5.5,
        "end": 7.0,
        "text": "Buenos dias profesor.",
        "speaker": "SPEAKER_01",
        "words": [
            {"word": "Buenos", "start": 5.5, "end": 5.8, "score": 0.82, "speaker": "SPEAKER_01"},
            {"word": "dias", "start": 5.8, "end": 6.1, "score": 0.79, "speaker": "SPEAKER_01"},
            {"word": "profesor.", "start": 6.1, "end": 6.8, "score": 0.85, "speaker": "SPEAKER_01"},
        ]
    },
    {
        "start": 7.5,
        "end": 15.0,
        "text": "Hoy vamos a hablar de senales.",
        "speaker": "SPEAKER_00",
        "words": [
            {"word": "Hoy", "start": 7.5, "end": 7.7, "score": 0.9, "speaker": "SPEAKER_00"},
            {"word": "vamos", "start": 7.7, "end": 7.9, "score": 0.88, "speaker": "SPEAKER_00"},
            {"word": "a", "start": 7.9, "end": 8.0, "score": 0.95, "speaker": "SPEAKER_00"},
            {"word": "hablar", "start": 8.0, "end": 8.3, "score": 0.92, "speaker": "SPEAKER_00"},
            {"word": "de", "start": 8.3, "end": 8.4, "score": 0.91, "speaker": "SPEAKER_00"},
            {"word": "senales.", "start": 8.4, "end": 9.0, "score": 0.89, "speaker": "SPEAKER_00"},
        ]
    },
    {
        "start": 15.5,
        "end": 16.0,
        "text": "OK.",
        "speaker": "SPEAKER_01",
        "words": [
            {"word": "OK.", "start": 15.5, "end": 15.8, "score": 0.7, "speaker": "SPEAKER_01"},
        ]
    },
    {
        "start": 16.5,
        "end": 25.0,
        "text": "Las senales son importantes para la comunicacion entre procesos.",
        "speaker": "SPEAKER_00",
        "words": [
            {"word": "Las", "start": 16.5, "end": 16.7, "score": 0.88, "speaker": "SPEAKER_00"},
            {"word": "senales", "start": 16.7, "end": 17.2, "score": 0.85, "speaker": "SPEAKER_00"},
            {"word": "son", "start": 17.2, "end": 17.4, "score": 0.9, "speaker": "SPEAKER_00"},
            {"word": "importantes", "start": 17.4, "end": 18.0, "score": 0.87, "speaker": "SPEAKER_00"},
            {"word": "para", "start": 18.0, "end": 18.2, "score": 0.92, "speaker": "SPEAKER_00"},
            {"word": "la", "start": 18.2, "end": 18.3, "score": 0.95, "speaker": "SPEAKER_00"},
            {"word": "comunicacion", "start": 18.3, "end": 19.0, "score": 0.88, "speaker": "SPEAKER_00"},
            {"word": "entre", "start": 19.0, "end": 19.2, "score": 0.91, "speaker": "SPEAKER_00"},
            {"word": "procesos.", "start": 19.2, "end": 20.0, "score": 0.86, "speaker": "SPEAKER_00"},
        ]
    },
]

analyzer = TranscriptAnalyzer()


class TestDetectarTeacher:
    def test_teacher_el_que_mas_habla(self):
        teacher = TranscriptAnalyzer._detectar_teacher(SEGMENTS_EJEMPLO)
        assert teacher == "SPEAKER_00"

    def test_teacher_segments_vacios(self):
        teacher = TranscriptAnalyzer._detectar_teacher([])
        assert teacher == "SPEAKER_00"


class TestPromedioDuracion:
    def test_promedio_correcto(self):
        promedio = TranscriptAnalyzer._promedio_duracion(SEGMENTS_EJEMPLO)
        assert promedio == pytest.approx(4.6, rel=0.1)

    def test_promedio_vacio(self):
        assert TranscriptAnalyzer._promedio_duracion([]) == 0.0


class TestCalcularALD:
    def test_ald_calcula_gaps(self):
        ald = TranscriptAnalyzer._calcular_ald(SEGMENTS_EJEMPLO)
        assert ald == pytest.approx(0.5, rel=0.1)

    def test_ald_sin_gaps(self):
        segments = [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"},
        ]
        assert TranscriptAnalyzer._calcular_ald(segments) == 0.0


class TestCalcularTTC:
    def test_ttc_cuenta_cambios(self):
        ttc = TranscriptAnalyzer._calcular_ttc(SEGMENTS_EJEMPLO)
        assert ttc == 4

    def test_ttc_sin_cambios(self):
        segments = [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_00"},
        ]
        assert TranscriptAnalyzer._calcular_ttc(segments) == 0


class TestCalcularMR:
    def test_mr_bajo_score_es_mumble(self):
        segments = [
            {
                "start": 0.0, "end": 5.0, "speaker": "SPEAKER_00",
                "words": [
                    {"word": "hola", "score": 0.3},
                    {"word": "mundo", "score": 0.9},
                ]
            }
        ]
        mr = analyzer._calcular_mr(segments)
        assert mr == pytest.approx(0.5, rel=0.1)

    def test_mr_sin_words(self):
        segments = [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"}
        ]
        assert analyzer._calcular_mr(segments) == 0.0


class TestCalcularVSUR:
    def test_vsur_cuenta_cortos(self):
        vsur = analyzer._calcular_vsur(SEGMENTS_EJEMPLO)
        assert vsur == pytest.approx(0.4, rel=0.1)

    def test_vsur_vacio(self):
        assert analyzer._calcular_vsur([]) == 0.0


class TestContarIntervencionesSignificativas:
    def test_cuenta_mayores_3s(self):
        count = analyzer._contar_intervenciones_significativas(SEGMENTS_EJEMPLO)
        assert count == 3


class TestCalcularMetricas:
    def test_metricas_estructura(self):
        metricas = analyzer._calcular_metricas(SEGMENTS_EJEMPLO, "SPEAKER_00")
        assert "PSR" in metricas
        assert "APSUD" in metricas
        assert "SR" in metricas
        assert "ALD" in metricas
        assert "TTC" in metricas
        assert "MR" in metricas
        assert "VSUR" in metricas
        assert "PSUR" in metricas
        assert "distinct_students" in metricas
        assert "significant_interventions" in metricas

    def test_psr_rango(self):
        metricas = analyzer._calcular_metricas(SEGMENTS_EJEMPLO, "SPEAKER_00")
        assert 0 <= metricas["PSR"] <= 1

    def test_distinct_students(self):
        metricas = analyzer._calcular_metricas(SEGMENTS_EJEMPLO, "SPEAKER_00")
        assert metricas["distinct_students"] == 1


class TestProcesarJsonTranscripcion:
    def test_archivo_no_existe(self):
        with pytest.raises(FileNotFoundError):
            procesar_json_transcripcion("no_existe.json")

    def test_json_invalido(self, tmp_path):
        archivo = tmp_path / "invalido.json"
        archivo.write_text("no es json")
        with pytest.raises(DataValidationError):
            procesar_json_transcripcion(str(archivo))

    def test_json_sin_segments(self, tmp_path):
        archivo = tmp_path / "sin_segments.json"
        archivo.write_text(json.dumps({"otro_campo": []}))
        with pytest.raises(DataValidationError):
            procesar_json_transcripcion(str(archivo))

    def test_procesar_json_real(self):
        resultado = procesar_json_transcripcion("transcripcion-clase-umu.json")
        assert "metadata" in resultado
        assert "metricas" in resultado
        assert "timeline" in resultado
        assert resultado["metadata"]["duracion_total_segundos"] > 0
        assert resultado["metadata"]["total_intervenciones"] > 0

    def test_teacher_auto_detectado(self):
        resultado = procesar_json_transcripcion("transcripcion-clase-umu.json")
        assert resultado["teacher_speaker"] is not None
        assert len(resultado["teacher_speaker"]) > 0
