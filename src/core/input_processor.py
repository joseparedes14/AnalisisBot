"""
Modulo de procesamiento de entrada para el generador de informes pedagogicos.

Proporciona:
- Lectura y parseo de JSON de transcripcion (Whisper)
- Calculo de metricas reales de interaccion en el aula
- Deteccion automatica del profesor
"""

import json
from dataclasses import dataclass
from typing import Dict, Any, List
from pathlib import Path

from .errors import DataValidationError, get_logger

logger = get_logger(__name__)


@dataclass
class TranscriptAnalyzer:
    """Analizador de transcripciones de aula con umbrales configurables.

    Args:
        mumble_threshold: Score minimo para considerar una palabra como nitida (default: 0.5)
        short_utterance_max: Duracion maxima en segundos para intervencion corta (default: 2.0)
        significant_intervention_min: Duracion minima para intervencion significativa (default: 3.0)
        block_size: Tamano de cada bloque en segundos para timeline (default: 300 = 5 min)
    """
    mumble_threshold: float = 0.5
    short_utterance_max: float = 2.0
    significant_intervention_min: float = 3.0
    block_size: int = 300

    def procesar(self, json_path: str, teacher_speaker: str = "auto") -> Dict[str, Any]:
        """Lee un JSON de transcripcion Whisper y calcula metricas reales."""
        ruta = Path(json_path)
        if not ruta.exists():
            raise FileNotFoundError(f"El archivo JSON no existe: {json_path}")

        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                datos = json.load(f)
        except json.JSONDecodeError as e:
            raise DataValidationError(f"Error al parsear el JSON: {e}")

        if "segments" not in datos:
            raise DataValidationError("El JSON no contiene el campo 'segments'")

        segments = datos["segments"]
        if not segments:
            raise DataValidationError("El JSON no contiene segmentos")

        logger.info(f"JSON cargado correctamente: {len(segments)} segmentos encontrados")

        teacher = self._detectar_teacher(segments) if teacher_speaker == "auto" else teacher_speaker
        logger.info(f"Teacher: {teacher}")

        metricas = self._calcular_metricas(segments, teacher)
        metadata = self._calcular_metadata(segments, teacher)
        timeline = self._generar_timeline(segments, teacher)

        logger.info("Metricas calculadas correctamente")
        return {
            "metadata": metadata,
            "metricas": metricas,
            "timeline": timeline,
            "teacher_speaker": teacher,
        }

    @staticmethod
    def _detectar_teacher(segments: List[Dict[str, Any]]) -> str:
        """Detecta quien es el teacher (el que mas tiempo habla)."""
        tiempos_por_speaker = {}
        for seg in segments:
            speaker = seg.get("speaker", "UNKNOWN")
            duracion = seg.get("end", 0) - seg.get("start", 0)
            tiempos_por_speaker[speaker] = tiempos_por_speaker.get(speaker, 0) + duracion

        if not tiempos_por_speaker:
            return "SPEAKER_00"
        teacher = max(tiempos_por_speaker, key=tiempos_por_speaker.get)
        logger.debug(f"Tiempos por speaker: {tiempos_por_speaker}")
        return teacher

    @staticmethod
    def _calcular_metadata(segments: List[Dict[str, Any]], teacher: str) -> Dict[str, Any]:
        """Calcula metadata general de la sesion."""
        if segments:
            inicio = segments[0].get("start", 0)
            fin = segments[-1].get("end", 0)
            duracion_total = fin - inicio
        else:
            duracion_total = 0

        speakers = set(seg.get("speaker", "UNKNOWN") for seg in segments)
        num_estudiantes = len(speakers) - 1 if teacher in speakers else len(speakers)

        return {
            "duracion_total_segundos": round(duracion_total, 2),
            "duracion_total_minutos": round(duracion_total / 60, 2),
            "numero_estudiantes": num_estudiantes,
            "total_intervenciones": len(segments),
            "speakers_detectados": list(speakers),
        }

    def _calcular_metricas(self, segments: List[Dict[str, Any]], teacher: str) -> Dict[str, Any]:
        """Calcula las 11 metricas definidas."""
        seg_teacher = [s for s in segments if s.get("speaker") == teacher]
        seg_students = [s for s in segments if s.get("speaker") != teacher]

        tiempo_teacher = sum(s.get("end", 0) - s.get("start", 0) for s in seg_teacher)
        tiempo_students = sum(s.get("end", 0) - s.get("start", 0) for s in seg_students)
        tiempo_total_hablando = tiempo_teacher + tiempo_students

        if segments:
            inicio_sesion = segments[0].get("start", 0)
            fin_sesion = segments[-1].get("end", 0)
            duracion_sesion = fin_sesion - inicio_sesion
        else:
            duracion_sesion = 0

        # PSR
        psr = round(tiempo_teacher / tiempo_total_hablando, 4) if tiempo_total_hablando > 0 else 0

        # APSUD
        apsud_teacher = self._promedio_duracion(seg_teacher)
        apsud_students = self._promedio_duracion(seg_students)
        apsud_total = self._promedio_duracion(segments)

        # SR
        sr_teacher = round(tiempo_teacher / duracion_sesion, 4) if duracion_sesion > 0 else 0
        sr_students = round(tiempo_students / duracion_sesion, 4) if duracion_sesion > 0 else 0

        # ALD, TTC, MR
        ald = self._calcular_ald(segments)
        ttc = self._calcular_ttc(segments)
        mr = self._calcular_mr(segments)

        # VSUR
        vsur_teacher = self._calcular_vsur(seg_teacher)
        vsur_students = self._calcular_vsur(seg_students)

        # PSUR
        total_turnos = len(segments)
        psur_teacher = round(len(seg_teacher) / total_turnos, 4) if total_turnos > 0 else 0
        psur_students = round(len(seg_students) / total_turnos, 4) if total_turnos > 0 else 0

        # Distinct students
        speakers_students = set(s.get("speaker", "UNKNOWN") for s in seg_students)
        distinct_students = len(speakers_students)

        # Significant interventions
        intervenciones_significativas = self._contar_intervenciones_significativas(segments)

        return {
            "PSR": psr,
            "APSUD": {
                "teacher": round(apsud_teacher, 2),
                "students": round(apsud_students, 2),
                "total": round(apsud_total, 2),
            },
            "SR": {"teacher": sr_teacher, "students": sr_students},
            "ALD": round(ald, 2),
            "TTC": ttc,
            "MR": round(mr, 4),
            "VSUR": {
                "teacher": round(vsur_teacher, 4),
                "students": round(vsur_students, 4),
            },
            "PSUR": {
                "teacher": psur_teacher,
                "students": psur_students,
            },
            "distinct_students": distinct_students,
            "significant_interventions": intervenciones_significativas,
        }

    @staticmethod
    def _promedio_duracion(segments: List[Dict[str, Any]]) -> float:
        if not segments:
            return 0.0
        duraciones = [s.get("end", 0) - s.get("start", 0) for s in segments]
        return sum(duraciones) / len(duraciones)

    @staticmethod
    def _calcular_ald(segments: List[Dict[str, Any]]) -> float:
        if len(segments) < 2:
            return 0.0
        gaps = []
        for i in range(1, len(segments)):
            start_prev = segments[i - 1].get("end", 0)
            end_curr = segments[i].get("start", 0)
            gap = end_curr - start_prev
            if gap > 0:
                gaps.append(gap)
        return sum(gaps) / len(gaps) if gaps else 0.0

    @staticmethod
    def _calcular_ttc(segments: List[Dict[str, Any]]) -> int:
        if len(segments) < 2:
            return 0
        cambios = 0
        for i in range(1, len(segments)):
            if segments[i].get("speaker") != segments[i - 1].get("speaker"):
                cambios += 1
        return cambios

    def _calcular_mr(self, segments: List[Dict[str, Any]]) -> float:
        todos_scores = []
        for seg in segments:
            for word in seg.get("words", []):
                score = word.get("score")
                if score is not None:
                    todos_scores.append(score)
        if not todos_scores:
            return 0.0
        mumble_count = sum(1 for s in todos_scores if s < self.mumble_threshold)
        return mumble_count / len(todos_scores)

    def _calcular_vsur(self, segments: List[Dict[str, Any]]) -> float:
        if not segments:
            return 0.0
        cortos = sum(
            1 for s in segments
            if (s.get("end", 0) - s.get("start", 0)) < self.short_utterance_max
        )
        return cortos / len(segments)

    def _contar_intervenciones_significativas(self, segments: List[Dict[str, Any]]) -> int:
        return sum(
            1 for s in segments
            if (s.get("end", 0) - s.get("start", 0)) >= self.significant_intervention_min
        )

    def _generar_timeline(self, segments: List[Dict[str, Any]], teacher: str) -> List[Dict[str, Any]]:
        if not segments:
            return []

        inicio = segments[0].get("start", 0)
        fin = segments[-1].get("end", 0)
        duracion = fin - inicio
        num_bloques = max(1, int(duracion / self.block_size) + 1)

        timeline = []
        for i in range(num_bloques):
            bloque_inicio = inicio + (i * self.block_size)
            bloque_fin = bloque_inicio + self.block_size

            seg_bloque = [
                s for s in segments
                if bloque_inicio <= s.get("start", 0) < bloque_fin
            ]
            if not seg_bloque:
                continue

            seg_t = [s for s in seg_bloque if s.get("speaker") == teacher]
            seg_s = [s for s in seg_bloque if s.get("speaker") != teacher]

            tiempo_t = sum(s.get("end", 0) - s.get("start", 0) for s in seg_t)
            tiempo_s = sum(s.get("end", 0) - s.get("start", 0) for s in seg_s)
            tiempo_total = tiempo_t + tiempo_s
            psr_bloque = round(tiempo_t / tiempo_total, 2) if tiempo_total > 0 else 0

            timeline.append({
                "bloque": i + 1,
                "inicio_min": round((bloque_inicio - inicio) / 60, 1),
                "fin_min": round((bloque_fin - inicio) / 60, 1),
                "psr": psr_bloque,
                "intervenciones_teacher": len(seg_t),
                "intervenciones_students": len(seg_s),
                "total_intervenciones": len(seg_bloque),
            })

        return timeline


def procesar_json_transcripcion(json_path: str, teacher_speaker: str = "auto") -> Dict[str, Any]:
    """Wrapper de compatibilidad que usa TranscriptAnalyzer con valores por defecto."""
    return TranscriptAnalyzer().procesar(json_path, teacher_speaker)
