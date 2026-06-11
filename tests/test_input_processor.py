"""
Tests unitarios para el módulo de procesamiento de entrada.
"""

import json
import pytest
from src.core.input_processor import (
    procesar_json_transcripcion,
    _detectar_teacher,
    _calcular_metricas,
    _promedio_duracion,
    _calcular_ald,
    _calcular_ttc,
    _calcular_mr,
    _calcular_vsur,
    _contar_intervenciones_significativas,
)
from src.core.errors import DataValidationError


# Datos de prueba
SEGMENTS_EJEMPLO = [
    {
        "start": 0.0,
        "end": 5.0,
        "text": "Buenos días a todos.",
        "speaker": "SPEAKER_00",
        "words": [
            {"word": "Buenos", "start": 0.0, "end": 0.5, "score": 0.9, "speaker": "SPEAKER_00"},
            {"word": "días", "start": 0.5, "end": 1.0, "score": 0.85, "speaker": "SPEAKER_00"},
            {"word": "a", "start": 1.0, "end": 1.1, "score": 0.8, "speaker": "SPEAKER_00"},
            {"word": "todos.", "start": 1.1, "end": 1.5, "score": 0.88, "speaker": "SPEAKER_00"},
        ]
    },
    {
        "start": 5.5,
        "end": 7.0,
        "text": "Buenos días profesor.",
        "speaker": "SPEAKER_01",
        "words": [
            {"word": "Buenos", "start": 5.5, "end": 5.8, "score": 0.82, "speaker": "SPEAKER_01"},
            {"word": "días", "start": 5.8, "end": 6.1, "score": 0.79, "speaker": "SPEAKER_01"},
            {"word": "profesor.", "start": 6.1, "end": 6.8, "score": 0.85, "speaker": "SPEAKER_01"},
        ]
    },
    {
        "start": 7.5,
        "end": 15.0,
        "text": "Hoy vamos a hablar de señales.",
        "speaker": "SPEAKER_00",
        "words": [
            {"word": "Hoy", "start": 7.5, "end": 7.7, "score": 0.9, "speaker": "SPEAKER_00"},
            {"word": "vamos", "start": 7.7, "end": 7.9, "score": 0.88, "speaker": "SPEAKER_00"},
            {"word": "a", "start": 7.9, "end": 8.0, "score": 0.95, "speaker": "SPEAKER_00"},
            {"word": "hablar", "start": 8.0, "end": 8.3, "score": 0.92, "speaker": "SPEAKER_00"},
            {"word": "de", "start": 8.3, "end": 8.4, "score": 0.91, "speaker": "SPEAKER_00"},
            {"word": "señales.", "start": 8.4, "end": 9.0, "score": 0.89, "speaker": "SPEAKER_00"},
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
        "text": "Las señales son importantes para la comunicación entre procesos.",
        "speaker": "SPEAKER_00",
        "words": [
            {"word": "Las", "start": 16.5, "end": 16.7, "score": 0.88, "speaker": "SPEAKER_00"},
            {"word": "señales", "start": 16.7, "end": 17.2, "score": 0.85, "speaker": "SPEAKER_00"},
            {"word": "son", "start": 17.2, "end": 17.4, "score": 0.9, "speaker": "SPEAKER_00"},
            {"word": "importantes", "start": 17.4, "end": 18.0, "score": 0.87, "speaker": "SPEAKER_00"},
            {"word": "para", "start": 18.0, "end": 18.2, "score": 0.92, "speaker": "SPEAKER_00"},
            {"word": "la", "start": 18.2, "end": 18.3, "score": 0.95, "speaker": "SPEAKER_00"},
            {"word": "comunicación", "start": 18.3, "end": 19.0, "score": 0.88, "speaker": "SPEAKER_00"},
            {"word": "entre", "start": 19.0, "end": 19.2, "score": 0.91, "speaker": "SPEAKER_00"},
            {"word": "procesos.", "start": 19.2, "end": 20.0, "score": 0.86, "speaker": "SPEAKER_00"},
        ]
    },
]


class TestDetectarTeacher:
    """Tests para la función _detectar_teacher."""

    def test_teacher_el_que_mas_habla(self):
        """El teacher debe ser el speaker con más tiempo de habla."""
        teacher = _detectar_teacher(SEGMENTS_EJEMPLO)
        assert teacher == "SPEAKER_00"  # Tiene más tiempo

    def test_teacher_segments_vacios(self):
        """Con segments vacíos, debe retornar SPEAKER_00 por defecto."""
        teacher = _detectar_teacher([])
        assert teacher == "SPEAKER_00"


class TestPromedioDuracion:
    """Tests para la función _promedio_duracion."""

    def test_promedio_correcto(self):
        """El promedio debe ser la suma de duraciones dividida por cantidad."""
        promedio = _promedio_duracion(SEGMENTS_EJEMPLO)
        # Duraciones: 5.0, 1.5, 7.5, 0.5, 8.5 = 23.0 / 5 = 4.6
        assert promedio == pytest.approx(4.6, rel=0.1)

    def test_promedio_vacio(self):
        """Con segments vacíos, debe retornar 0."""
        assert _promedio_duracion([]) == 0.0


class TestCalcularALD:
    """Tests para la función _calcular_ald."""

    def test_ald_calcula_gaps(self):
        """ALD debe calcular el promedio de pausas entre segmentos."""
        ald = _calcular_ald(SEGMENTS_EJEMPLO)
        # Gaps: 0.5 (5.0->5.5), 0.5 (7.0->7.5), 0.5 (15.0->15.5), 0.5 (16.0->16.5)
        # Promedio: 0.5
        assert ald == pytest.approx(0.5, rel=0.1)

    def test_ald_sin_gaps(self):
        """Si no hay gaps positivos, debe retornar 0."""
        segments = [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"},
        ]
        assert _calcular_ald(segments) == 0.0


class TestCalcularTTC:
    """Tests para la función _calcular_ttc."""

    def test_ttc_cuenta_cambios(self):
        """TTC debe contar los cambios de speaker."""
        ttc = _calcular_ttc(SEGMENTS_EJEMPLO)
        # Cambios: 0->1, 1->0, 0->1, 1->0 = 4 cambios
        assert ttc == 4

    def test_ttc_sin_cambios(self):
        """Si todos hablan seguido, TTC debe ser 0."""
        segments = [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
            {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_00"},
        ]
        assert _calcular_ttc(segments) == 0


class TestCalcularMR:
    """Tests para la función _calcular_mr."""

    def test_mr_bajo_score_es_mumble(self):
        """Words con score bajo deben contar como murmullo."""
        segments = [
            {
                "start": 0.0, "end": 5.0, "speaker": "SPEAKER_00",
                "words": [
                    {"word": "hola", "score": 0.3},  # mumble
                    {"word": "mundo", "score": 0.9},  # no mumble
                ]
            }
        ]
        mr = _calcular_mr(segments)
        assert mr == pytest.approx(0.5, rel=0.1)

    def test_mr_sin_words(self):
        """Si no hay words con score, debe retornar 0."""
        segments = [
            {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"}
        ]
        assert _calcular_mr(segments) == 0.0


class TestCalcularVSUR:
    """Tests para la función _calcular_vsur."""

    def test_vsur_cuenta_cortos(self):
        """VSUR debe contar intervenciones < 2 segundos."""
        vsur = _calcular_vsur(SEGMENTS_EJEMPLO)
        # 2 segmentos < 2s: 1.5s (segundo) y 0.5s (cuarto)
        # 2/5 = 0.4
        assert vsur == pytest.approx(0.4, rel=0.1)

    def test_vsur_vacio(self):
        """Con segments vacíos, debe retornar 0."""
        assert _calcular_vsur([]) == 0.0


class TestContarIntervencionesSignificativas:
    """Tests para la función _contar_intervenciones_significativas."""

    def test_cuenta_mayores_3s(self):
        """Debe contar intervenciones >= 3 segundos."""
        count = _contar_intervenciones_significativas(SEGMENTS_EJEMPLO)
        # 3 segmentos >= 3s (5.0, 7.5, 8.5)
        assert count == 3


class TestCalcularMetricas:
    """Tests para la función _calcular_metricas."""

    def test_metricas_estructura(self):
        """Las métricas deben tener la estructura correcta."""
        metricas = _calcular_metricas(SEGMENTS_EJEMPLO, "SPEAKER_00")

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
        """PSR debe estar entre 0 y 1."""
        metricas = _calcular_metricas(SEGMENTS_EJEMPLO, "SPEAKER_00")
        assert 0 <= metricas["PSR"] <= 1

    def test_distinct_students(self):
        """Debe haber 1 estudiante distinto (excluyendo teacher)."""
        metricas = _calcular_metricas(SEGMENTS_EJEMPLO, "SPEAKER_00")
        assert metricas["distinct_students"] == 1


class TestProcesarJsonTranscripcion:
    """Tests para la función principal procesar_json_transcripcion."""

    def test_archivo_no_existe(self):
        """Debe lanzar FileNotFoundError si el archivo no existe."""
        with pytest.raises(FileNotFoundError):
            procesar_json_transcripcion("no_existe.json")

    def test_json_invalido(self, tmp_path):
        """Debe lanzar DataValidationError con JSON inválido."""
        archivo = tmp_path / "invalido.json"
        archivo.write_text("no es json")
        with pytest.raises(DataValidationError):
            procesar_json_transcripcion(str(archivo))

    def test_json_sin_segments(self, tmp_path):
        """Debe lanzar DataValidationError sin campo segments."""
        archivo = tmp_path / "sin_segments.json"
        archivo.write_text(json.dumps({"otro_campo": []}))
        with pytest.raises(DataValidationError):
            procesar_json_transcripcion(str(archivo))

    def test_procesar_json_real(self):
        """Debe procesar el JSON de ejemplo real."""
        resultado = procesar_json_transcripcion(
            "transcripcion-clase-umu.json"
        )

        assert "metadata" in resultado
        assert "metricas" in resultado
        assert "timeline" in resultado
        assert resultado["metadata"]["duracion_total_segundos"] > 0
        assert resultado["metadata"]["total_intervenciones"] > 0

    def test_teacher_auto_detectado(self):
        """El teacher debe ser auto-detectado correctamente."""
        resultado = procesar_json_transcripcion(
            "transcripcion-clase-umu.json"
        )

        assert resultado["teacher_speaker"] is not None
        assert len(resultado["teacher_speaker"]) > 0
