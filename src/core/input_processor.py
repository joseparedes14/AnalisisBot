"""
Módulo de procesamiento de entrada para el generador de informes pedagógicos.

Este módulo proporciona:
- Lectura y parseo de JSON de transcripción (Whisper)
- Cálculo de métricas reales de interacción en el aula
- Detección automática del profesor
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from .errors import DataValidationError, get_logger

logger = get_logger(__name__)


def procesar_json_transcripcion(json_path: str, teacher_speaker: str = "auto") -> Dict[str, Any]:
    """
    Lee un JSON de transcripción Whisper y calcula métricas reales.

    Args:
        json_path: Ruta al archivo JSON de transcripción
        teacher_speaker: "auto" para detectar automáticamente, o el nombre del speaker (ej. "SPEAKER_00")

    Returns:
        Dict con metadata, métricas y timeline

    Raises:
        DataValidationError: Si el JSON es inválido o no tiene la estructura esperada
        FileNotFoundError: Si el archivo no existe
    """
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

    # Detectar teacher
    if teacher_speaker == "auto":
        teacher = _detectar_teacher(segments)
        logger.info(f"Teacher auto-detectado: {teacher}")
    else:
        teacher = teacher_speaker

    # Calcular métricas
    metricas = _calcular_metricas(segments, teacher)

    # Calcular metadata
    metadata = _calcular_metadata(segments, teacher)

    # Generar timeline resumido (para el LLM)
    timeline = _generar_timeline(segments, teacher)

    resultado = {
        "metadata": metadata,
        "metricas": metricas,
        "timeline": timeline,
        "teacher_speaker": teacher
    }

    logger.info("Métricas calculadas correctamente")
    return resultado


def _detectar_teacher(segments: List[Dict[str, Any]]) -> str:
    """
    Detecta quién es el teacher (el que más tiempo habla).

    Args:
        segments: Lista de segmentos de la transcripción

    Returns:
        Nombre del speaker que más tiempo habla (ej. "SPEAKER_00")
    """
    tiempos_por_speaker = {}

    for seg in segments:
        speaker = seg.get("speaker", "UNKNOWN")
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        duracion = end - start

        tiempos_por_speaker[speaker] = tiempos_por_speaker.get(speaker, 0) + duracion

    if not tiempos_por_speaker:
        return "SPEAKER_00"

    # Retornar el speaker con más tiempo
    teacher = max(tiempos_por_speaker, key=tiempos_por_speaker.get)
    logger.debug(f"Tiempos por speaker: {tiempos_por_speaker}")
    return teacher


def _calcular_metadata(segments: List[Dict[str, Any]], teacher: str) -> Dict[str, Any]:
    """
    Calcula metadata general de la sesión.

    Args:
        segments: Lista de segmentos
        teacher: Speaker del teacher

    Returns:
        Dict con metadata
    """
    # Duración total (del primer al último segmento)
    if segments:
        inicio = segments[0].get("start", 0)
        fin = segments[-1].get("end", 0)
        duracion_total = fin - inicio
    else:
        duracion_total = 0

    # Speakers únicos
    speakers = set(seg.get("speaker", "UNKNOWN") for seg in segments)
    num_estudiantes = len(speakers) - 1 if teacher in speakers else len(speakers)

    # Total de intervenciones
    total_intervenciones = len(segments)

    return {
        "duracion_total_segundos": round(duracion_total, 2),
        "duracion_total_minutos": round(duracion_total / 60, 2),
        "numero_estudiantes": num_estudiantes,
        "total_intervenciones": total_intervenciones,
        "speakers_detectados": list(speakers)
    }


def _calcular_metricas(segments: List[Dict[str, Any]], teacher: str) -> Dict[str, Any]:
    """
    Calcula las 11 métricas definidas en el PROMPTMEJORADO.

    Args:
        segments: Lista de segmentos
        teacher: Speaker del teacher

    Returns:
        Dict con las métricas calculadas
    """
    # Separar segmentos por rol
    seg_teacher = [s for s in segments if s.get("speaker") == teacher]
    seg_students = [s for s in segments if s.get("speaker") != teacher]

    # Tiempos totales por rol
    tiempo_teacher = sum(s.get("end", 0) - s.get("start", 0) for s in seg_teacher)
    tiempo_students = sum(s.get("end", 0) - s.get("start", 0) for s in seg_students)
    tiempo_total_hablando = tiempo_teacher + tiempo_students

    # Duración total de la sesión (para SR)
    if segments:
        inicio_sesion = segments[0].get("start", 0)
        fin_sesion = segments[-1].get("end", 0)
        duracion_sesion = fin_sesion - inicio_sesion
    else:
        duracion_sesion = 0

    # 1. PSR (Participation Speech Ratio)
    psr = round(tiempo_teacher / tiempo_total_hablando, 4) if tiempo_total_hablando > 0 else 0

    # 2. APSUD (Average Duration of Utterances)
    apsud_teacher = _promedio_duracion(seg_teacher)
    apsud_students = _promedio_duracion(seg_students)
    apsud_total = _promedio_duracion(segments)

    # 3. SR (Speaking Ratio)
    sr_teacher = round(tiempo_teacher / duracion_sesion, 4) if duracion_sesion > 0 else 0
    sr_students = round(tiempo_students / duracion_sesion, 4) if duracion_sesion > 0 else 0

    # 4. ALD (Average Length of Silence)
    ald = _calcular_ald(segments)

    # 5. TTC (Turn-Taking Count)
    ttc = _calcular_ttc(segments)

    # 6. MR (Mumble Ratio)
    mr = _calcular_mr(segments)

    # 7. VSUR (Very Short Utterance Ratio)
    vsur_teacher = _calcular_vsur(seg_teacher)
    vsur_students = _calcular_vsur(seg_students)

    # 8. PSUR (Utterance Ratio)
    total_turnos = len(segments)
    psur_teacher = round(len(seg_teacher) / total_turnos, 4) if total_turnos > 0 else 0
    psur_students = round(len(seg_students) / total_turnos, 4) if total_turnos > 0 else 0

    # 9. Number of distinct students
    speakers_students = set(s.get("speaker", "UNKNOWN") for s in seg_students)
    distinct_students = len(speakers_students)

    # 10. Number of significant interventions (>= 3 segundos)
    intervenciones_significativas = _contar_intervenciones_significativas(segments)

    return {
        "PSR": psr,
        "APSUD": {
            "teacher": round(apsud_teacher, 2),
            "students": round(apsud_students, 2),
            "total": round(apsud_total, 2)
        },
        "SR": {
            "teacher": sr_teacher,
            "students": sr_students
        },
        "ALD": round(ald, 2),
        "TTC": ttc,
        "MR": round(mr, 4),
        "VSUR": {
            "teacher": round(vsur_teacher, 4),
            "students": round(vsur_students, 4)
        },
        "PSUR": {
            "teacher": psur_teacher,
            "students": psur_students
        },
        "distinct_students": distinct_students,
        "significant_interventions": intervenciones_significativas
    }


def _promedio_duracion(segments: List[Dict[str, Any]]) -> float:
    """Calcula la duración promedio de los segmentos."""
    if not segments:
        return 0.0

    duraciones = [s.get("end", 0) - s.get("start", 0) for s in segments]
    return sum(duraciones) / len(duraciones)


def _calcular_ald(segments: List[Dict[str, Any]]) -> float:
    """
    Calcula ALD (Average Length of Silence).
    Promedio de pausas entre segmentos consecutivos.
    """
    if len(segments) < 2:
        return 0.0

    gaps = []
    for i in range(1, len(segments)):
        gap_inicio = segments[i - 1].get("end", 0)
        gap_fin = segments[i].get("start", 0)
        gap = gap_fin - gap_inicio
        if gap > 0:  # Solo contar gaps positivos (pausas reales)
            gaps.append(gap)

    return sum(gaps) / len(gaps) if gaps else 0.0


def _calcular_ttc(segments: List[Dict[str, Any]]) -> int:
    """
    Calcula TTC (Turn-Taking Count).
    Número de veces que cambia el speaker entre segmentos consecutivos.
    """
    if len(segments) < 2:
        return 0

    cambios = 0
    for i in range(1, len(segments)):
        speaker_anterior = segments[i - 1].get("speaker")
        speaker_actual = segments[i].get("speaker")
        if speaker_actual != speaker_anterior:
            cambios += 1

    return cambios


def _calcular_mr(segments: List[Dict[str, Any]]) -> float:
    """
    Calcula MR (Mumble Ratio).
    Proporción del tiempo clasificado como "murmullo" (habla poco inteligible).
    Se estima usando el score de confianza de las palabras: bajo score = murmullo.
    """
    todos_scores = []
    for seg in segments:
        words = seg.get("words", [])
        for word in words:
            score = word.get("score")
            if score is not None:
                todos_scores.append(score)

    if not todos_scores:
        return 0.0

    # Considerar "murmullo" las palabras con score < 0.5
    mumble_count = sum(1 for s in todos_scores if s < 0.5)
    return mumble_count / len(todos_scores)


def _calcular_vsur(segments: List[Dict[str, Any]]) -> float:
    """
    Calcula VSUR (Very Short Utterance Ratio).
    Fracción de intervenciones < 2 segundos sobre el total.
    """
    if not segments:
        return 0.0

    cortos = sum(1 for s in segments if (s.get("end", 0) - s.get("start", 0)) < 2.0)
    return cortos / len(segments)


def _contar_intervenciones_significativas(segments: List[Dict[str, Any]]) -> int:
    """
    Cuenta intervenciones significativas (>= 3 segundos).
    """
    return sum(1 for s in segments if (s.get("end", 0) - s.get("start", 0)) >= 3.0)


def _generar_timeline(segments: List[Dict[str, Any]], teacher: str) -> List[Dict[str, Any]]:
    """
    Genera un timeline resumido para el LLM.
    Agrupa segmentos en bloques de ~5 minutos.
    """
    if not segments:
        return []

    # Determinar duración total
    inicio = segments[0].get("start", 0)
    fin = segments[-1].get("end", 0)
    duracion = fin - inicio

    # Dividir en bloques de 5 minutos (300 segundos)
    tamano_bloque = 300
    num_bloques = max(1, int(duracion / tamano_bloque) + 1)

    timeline = []
    for i in range(num_bloques):
        bloque_inicio = inicio + (i * tamano_bloque)
        bloque_fin = bloque_inicio + tamano_bloque

        # Filtrar segmentos en este bloque
        seg_bloque = [
            s for s in segments
            if bloque_inicio <= s.get("start", 0) < bloque_fin
        ]

        if not seg_bloque:
            continue

        # Calcular métricas del bloque
        seg_teacher = [s for s in seg_bloque if s.get("speaker") == teacher]
        seg_students = [s for s in seg_bloque if s.get("speaker") != teacher]

        tiempo_teacher = sum(s.get("end", 0) - s.get("start", 0) for s in seg_teacher)
        tiempo_students = sum(s.get("end", 0) - s.get("start", 0) for s in seg_students)
        tiempo_total = tiempo_teacher + tiempo_students

        psr_bloque = round(tiempo_teacher / tiempo_total, 2) if tiempo_total > 0 else 0

        timeline.append({
            "bloque": i + 1,
            "inicio_min": round((bloque_inicio - inicio) / 60, 1),
            "fin_min": round((bloque_fin - inicio) / 60, 1),
            "psr": psr_bloque,
            "intervenciones_teacher": len(seg_teacher),
            "intervenciones_students": len(seg_students),
            "total_intervenciones": len(seg_bloque)
        })

    return timeline
