"""
Modulo principal para la generacion de informes pedagogicos con Ollama.

Este modulo proporciona las funciones principales para:
- Extraer texto de archivos PDF
- Generar informes estructurados con Ollama
- Guardar resultados en PDF y JSON
"""

import json
import os
import concurrent.futures
from typing import Optional, Dict, Any, Union, List, Tuple
from pathlib import Path

# Importar dependencias
try:
    import ollama
except ImportError:
    ollama = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# Importar modulos locales
from .errors import (
    PDFExtractionError,
    OllamaGenerationError,
    PDFGenerationError,
    JSONGenerationError,
    DataValidationError,
    get_logger
)
from .validators import validate_temporal_data, validate_config
from ..utils.simulador import generar_datos_temporales

# Configurar logger
logger = get_logger(__name__)

def verificar_ollama(modelo: str = 'gpt-oss:120b-cloud') -> bool:
    """
    Verifica si Ollama esta disponible y el modelo esta instalado.

    Args:
        modelo: Nombre del modelo a verificar

    Returns:
        True si Ollama esta disponible y el modelo esta instalado
    """
    if ollama is None:
        logger.error("Libreria ollama no instalada")
        return False

    try:
        # Verificar si el servicio esta disponible
        modelos = ollama.list()
        modelos_disponibles = [m['model'] for m in modelos.get('models', [])]

        if modelo in modelos_disponibles:
            logger.info(f"Modelo '{modelo}' encontrado y disponible")
            return True
        else:
            logger.warning(f"Modelo '{modelo}' no encontrado. Modelos disponibles: {modelos_disponibles}")
            logger.info(f"Para instalar el modelo: ollama pull {modelo}")
            return False

    except Exception as e:
        logger.error(f"Error al conectar con Ollama: {e}")
        logger.info("Asegurate de que Ollama este en ejecucion")
        return False

def extraer_texto_pdf(ruta_pdf: str) -> str:
    """
    Lee un archivo PDF y extrae todo su texto pagina por pagina.

    Args:
        ruta_pdf: Ruta al archivo PDF

    Returns:
        Texto extraido del PDF

    Raises:
        PDFExtractionError: Si ocurre un error al extraer el texto
        FileNotFoundError: Si el archivo no existe
    """
    if fitz is None:
        raise PDFExtractionError("La libreria PyMuPDF (fitz) no esta instalada. "
                                "Instalala con: pip install pymupdf")

    ruta_absoluta = str(Path(ruta_pdf).resolve())
    if not Path(ruta_absoluta).exists():
        raise FileNotFoundError(f"El archivo '{ruta_absoluta}' no existe")

    try:
        logger.info(f"Extrayendo texto de PDF: {ruta_absoluta}")
        texto_completo = ""
        doc = fitz.open(ruta_absoluta)

        for num_pagina in range(len(doc)):
            pagina = doc.load_page(num_pagina)
            texto_completo += pagina.get_text("text") + "\n"

        texto_completo = texto_completo.strip()
        logger.debug(f"Extraidos {len(texto_completo)} caracteres de {ruta_absoluta}")

        if len(texto_completo) < 20:
            logger.warning(f"El PDF {ruta_absoluta} contiene muy poco texto. "
                          "Puede ser una imagen escaneada o estar vacio.")

        return texto_completo

    except Exception as e:
        logger.error(f"Error al extraer texto de {ruta_absoluta}: {e}")
        raise PDFExtractionError(f"Error al extraer texto de {ruta_absoluta}: {e}")

def generar_tabla_markdown(datos: List[Dict[str, Any]]) -> str:
    """
    Genera una tabla en formato Markdown a partir de una lista de diccionarios.

    Args:
        datos: Lista de diccionarios con los datos

    Returns:
        Tabla en formato Markdown
    """
    if not datos or not isinstance(datos, list) or not isinstance(datos[0], dict):
        return ""

    # Extraemos las claves directamente para hacerlas encabezados
    claves = list(datos[0].keys())

    # Construimos la tabla Markdown
    encabezado = "| " + " | ".join(claves) + " |"
    separador = "| " + " | ".join(["---"] * len(claves)) + " |"

    filas = ["| " + " | ".join(str(item.get(k, "")) for k in claves) + " |"
             for item in datos]

    return "\n".join([encabezado, separador] + filas)

def generar_texto_estructurado(
    informacion: str,
    prompt_tarea: str,
    instrucciones_estructura: str,
    datos_temporales_json: Optional[Union[str, List[Dict[str, Any]]]] = None,
    modelo: str = 'gpt-oss:120b-cloud',
    options: Optional[Dict[str, Any]] = None
) -> str:
    """
    Genera un texto estructurado usando Ollama.

    Args:
        informacion: Texto con la informacion de contexto
        prompt_tarea: Prompt que describe la tarea a realizar
        instrucciones_estructura: Instrucciones para la estructura del informe
        datos_temporales_json: Datos temporales en formato JSON o lista de diccionarios (opcional)
        modelo: Modelo de Ollama a utilizar
        options: Opciones adicionales para la generacion

    Returns:
        Texto generado por el modelo

    Raises:
        OllamaGenerationError: Si ocurre un error al generar el texto
        DataValidationError: Si los datos temporales no son validos
    """
    if ollama is None:
        raise OllamaGenerationError("La libreria ollama no esta instalada. "
                                  "Instalala con: pip install ollama")

    # Configurar opciones por defecto - ajuste para análisis más limpio
    if options is None:
        options = {
            "temperature": 0.1,
            "top_p": 0.8,
            "num_ctx": 8192,
            "repeat_penalty": 1.1
        }

    # 1. Mensaje de Sistema (System Prompt) - Optimizado
    mensaje_sistema = f"""Eres un analista pedagógico experto. Redacta informes profundos y bien razonados, anclándote exclusivamente en los datos proporcionados.

-REGLAS DE GENERACION:
       -1. FIDELIDAD: Los datos cuantitativos proveniran UNICAMENTE de la INFORMACION DE CONTEXTO. No inventes met
          -ricas ni numeros.
       -2. PROFUNDIDAD Y PENSAMIENTO CRITICO (MUY IMPORTANTE): Ve mas alla de lo descriptivo. Para cada metrica o
          -hallazgo clave, realiza una EVALUACION CRITICA EXHAUSTIVA: explora el "por que" detras de los numeros, for
          -mula hipotesis logicas de por que ocurrieron, cruza la informacion de distintas variables (correlaciones),
          - previene riesgos y plantea recomendaciones estrategicas a nivel macro.
       -3. ESTILO: Escribe con un tono sumo, formal, complejo y altamente argumentativo, digno de una auditoria de
          - alto nivel o tesis.
       -4. ESTRUCTURA: Encaja esta narrativa extensa dentro de los encabezados solicitados. No anadas saludos ni c
          -omentarios extra fuera de la estructura.
       -5. NO REPETICION: Genera CADA SECCION EXACTAMENTE UNA VEZ. Cuando llegues al final de la estructura solici
          -tada, DEBES DETENERTE de inmediato. JAMAS repitas bloques, cierres o recomendaciones.
       -6. ANALISIS DENSO Y VINCULADO DE LAS 8 VARIABLES GLOBALES: En "Metricas Globales y Comparativas", ESTA PRO
          -HIBIDO listar simplemente los valores y hacer un resumen generico o separado al final. DEBES dedicar un te
          -xto robusto y extenso por CADA UNA de las 8 variables obligatorias (PSR, APSUD, ALD, SR, TTC, MR, VSUR, PS
          -UR).
       -Para cada metrica, utiliza obligatoriamente este formato integrado en parrafos:
       -"**[NOMBRE DE LA METRICA] ([Valor exacto])**: [Redacta de manera fluida un ANALISIS PROFUNDO E INTEGRADO.
          -Debes incluir OBLIGATORIAMENTE: 1. Interpretacion pedagogica (que clima o dinamica de poder refleja este n
          -umero de forma subyacente?), 2. Interconexion cruzada (relaciona este dato explicitamente con al menos OTR
          -A metrica distinta, por ejemplo, vincula el indice TTC con el PSR o las intervenciones breves VSUR), y 3.
          -Hipotesis critica (deduce como esta combinacion afecta la asimilacion del conocimiento y el rol de los alu
          -mnos).
       -BAJO NINGUN CONCEPTO te limites a reescribir la definicion matematica de la metrica o a decir 'el docente
          -habla el 80%']. La superficialidad y la falta de interconexion son fallos criticos.
       -7. AGRUPACION EN BLOQUES IRREGULARES CON DATOS REALES: Rompe la sesion en bloques temporales asimetricos (
          -ej. 0-14, 14-37, etc.) garantizando siempre un minimo de 10 min por bloque. Jamas cortes matematicamente d
          -e 10 en 10. Dentro de cada bloque analiza SOLO "Protagonismo" y "Dinamica Discursiva". FUNDAMENTAL: Observ
          -a la tabla de datos temporal REAL provista, deduce a partir de sus variaciones por que elegiste ese bloque
          - y explica con profundidad pedagogica que estaba haciendo el docente apoyandote en ESOS numeros reales.
       -8. PROHIBICION DE TABLAS DE BLOQUES AL CIERRE: Es critico que al final NO introduzcas tablas de resumen po
          -r bloque ni enumeraciones que no esten dictadas especificamente por las instrucciones formales.
       -9. PARTICIPACION ESTUDIANTIL CON DATOS REALES: En "Analisis de la participacion estudiantil", DEBES extrae
          -r y utilizar obligatoriamente los datos de las intervenciones (ej. "Number of distinct students", "Number
          -of significant interventions", etc.) que se provean en el contexto de entrada. Asegurate de diagnosticar e
          -n base a esos numeros si la participacion es concentrada (pocas voces) o distribuida.
INSTRUCCIONES DE ESTRUCTURA:
{instrucciones_estructura}
"""

    # 2. Mensaje del Usuario (User Prompt)
    bloque_temporal_str = ""

    if datos_temporales_json:
        try:
            # Validar y procesar datos temporales
            datos_validados = validate_temporal_data(datos_temporales_json)

            # Generar tabla Markdown
            tabla_md = generar_tabla_markdown(datos_validados)

            if tabla_md:
                bloque_temporal_str = f"\nDATOS TEMPORALES DEL DESARROLLO (EN FORMATO TABLA):\n\n{tabla_md}\n\n"
            else:
                # Si no se pudo generar tabla, usar JSON
                bloque_temporal_str = f"\nDATOS TEMPORALES DEL DESARROLLO (JSON):\n\"\"\"\n{datos_temporales_json}\n\"\"\"\n"

        except DataValidationError as e:
            logger.warning(f"Datos temporales invalidos: {e}. Usando formato JSON crudo.")
            bloque_temporal_str = f"\nDATOS TEMPORALES DEL DESARROLLO (JSON):\n\"\"\"\n{datos_temporales_json}\n\"\"\"\n"
        except Exception as e:
            logger.warning(f"Error al procesar datos temporales: {e}. Usando formato JSON crudo.")
            bloque_temporal_str = f"\nDATOS TEMPORALES DEL DESARROLLO (JSON):\n\"\"\"\n{datos_temporales_json}\n\"\"\"\n"

    mensaje_usuario = f"""INFORMACION DE CONTEXTO:
{informacion}
{bloque_temporal_str}

TAREA A REALIZAR CON LA INFORMACION (PROMPT):
{prompt_tarea}
"""

    try:
        logger.info(f"Generando texto con modelo {modelo}")
        logger.debug(f"Opciones de generacion: {options}")

        # Llamada al modelo local usando la libreria de Ollama
        respuesta = ollama.chat(
            model=modelo,
            messages=[
                {'role': 'system', 'content': mensaje_sistema},
                {'role': 'user', 'content': mensaje_usuario}
            ],
            options=options
        )

        return respuesta['message']['content']

    except Exception as e:
        error_msg = f"Error al generar texto con Ollama: {e}"
        logger.error(error_msg)
        raise OllamaGenerationError(f"{error_msg}\nVerifica que Ollama este abierto y tengas el modelo '{modelo}' instalado.")

def _buscar_fuente_unicode() -> str:
    """
    Busca una fuente TTF con soporte Unicode en ubicaciones comunes del sistema.

    Returns:
        Ruta a la fuente encontrada, o cadena vacia si no se encuentra ninguna.
    """
    import platform

    candidatos = []

    if platform.system() == "Windows":
        windir = Path(os.environ.get("WINDIR", "C:\\Windows"))
        fonts_dir = windir / "Fonts"
        candidatos = [
            fonts_dir / "arial.ttf",
            fonts_dir / "segoeui.ttf",
            fonts_dir / "calibri.ttf",
            fonts_dir / "tahoma.ttf",
            fonts_dir / "verdana.ttf",
        ]
    elif platform.system() == "Darwin":  # macOS
        candidatos = [
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/Library/Fonts/Arial.ttf"),
            Path("/System/Library/Fonts/Helvetica.ttf"),
        ]
    else:  # Linux y otros Unix
        rutas = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        ]
        candidatos = [Path(r) for r in rutas]

    for ruta in candidatos:
        if ruta.exists():
            return str(ruta.resolve())

    return ""


def guardar_resultado_en_pdf(texto: str, nombre_archivo: str = "resultado_agente.pdf") -> bool:
    """
    Guarda el texto proporcionado en un archivo PDF.

    Args:
        texto: Texto a guardar en el PDF
        nombre_archivo: Nombre del archivo PDF de salida

    Returns:
        True si se guardo correctamente, False en caso contrario

    Raises:
        PDFGenerationError: Si ocurre un error al generar el PDF
    """
    # Intentar importar reportlab (mejor soporte Unicode)
    reportlab = None
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import inch
        reportlab = True
    except ImportError:
        pass

    # Intentar fpdf2 como alternativa (el paquete es fpdf2, pero el módulo se importa como fpdf)
    fpdf2_mod = None
    try:
        from fpdf import FPDF as FPDF2
        fpdf2_mod = FPDF2
    except ImportError:
        pass

    try:
        # Crear directorio si no existe
        output_path = Path(nombre_archivo)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generando PDF: {output_path.resolve()}")

        # Buscar fuente Unicode en el sistema
        fuente_unicode = _buscar_fuente_unicode()
        if fuente_unicode:
            logger.debug(f"Fuente Unicode encontrada: {fuente_unicode}")
        else:
            logger.debug("No se encontro fuente Unicode, se usara fuente por defecto")

        # Limpiar caracteres nulos del texto
        texto_limpio = texto.replace('\x00', '')

        if reportlab:
            _generar_pdf_reportlab(texto_limpio, str(output_path), fuente_unicode)

        elif fpdf2_mod:
            _generar_pdf_fpdf2(texto_limpio, str(output_path), fuente_unicode, fpdf2_mod)

        else:
            _generar_pdf_fpdf(texto_limpio, str(output_path))

        logger.info(f"PDF generado exitosamente: {output_path.resolve()}")
        return True

    except Exception as e:
        error_msg = f"Error al generar el PDF {nombre_archivo}: {e}"
        logger.error(error_msg)
        raise PDFGenerationError(error_msg)


def _generar_pdf_reportlab(texto: str, output_path: str, fuente_unicode: str) -> None:
    """Genera PDF usando reportlab con soporte Unicode."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)

    styles = getSampleStyleSheet()

    nombre_fuente = 'Helvetica'
    if fuente_unicode:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        try:
            pdfmetrics.registerFont(TTFont('FuenteUnicode', fuente_unicode))
            nombre_fuente = 'FuenteUnicode'
        except Exception:
            pass

    style = ParagraphStyle(
        'Informe',
        fontName=nombre_fuente,
        fontSize=11,
        leading=15,
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    story = []
    for parrafo in texto.split('\n\n'):
        if parrafo.strip():
            story.append(Paragraph(parrafo.strip(), style))

    doc.build(story)


def _generar_pdf_fpdf2(texto: str, output_path: str, fuente_unicode: str, fpdf2_class) -> None:
    """Genera PDF usando fpdf2 con soporte Unicode."""
    pdf = fpdf2_class()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    if fuente_unicode:
        try:
            pdf.add_font('FuenteUnicode', '', fuente_unicode, uni=True)
            pdf.set_font('FuenteUnicode', size=11)
        except Exception:
            pdf.set_font("Helvetica", size=11)
    else:
        pdf.set_font("Helvetica", size=11)

    pdf.multi_cell(0, 6, text=texto)
    pdf.output(str(output_path))


def _generar_pdf_fpdf(texto: str, output_path: str) -> None:
    """Genera PDF usando fpdf original (sin Unicode)."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=11)

    texto_normalizado = _normalizar_texto_latin1(texto)

    for linea in texto_normalizado.split('\n'):
        if linea.strip():
            pdf.multi_cell(0, 6, txt=linea)

    pdf.output(str(output_path))


def _normalizar_texto_latin1(texto: str) -> str:
    """
    Normaliza texto para PDF legacy (Latin-1).
    Convierte caracteres Unicode comunes a equivalentes Latin-1.
    """
    import unicodedata

    # Normalizar Unicode (NFD separa acentos, NFC los combina)
    texto = unicodedata.normalize('NFC', texto)

    # Eliminar caracteres de control (excepto \n, \t, \r)
    texto = ''.join(
        char for char in texto
        if unicodedata.category(char) != 'Cc' or char in '\n\t\r'
    )

    MAPA_UNICODE = {
        '\u2018': "'", '\u2019': "'",  # comillas simples curvas
        '\u201c': '"', '\u201d': '"',  # comillas dobles curvas
        '\u2013': '-', '\u2014': '-',  # guiones
        '\u2026': '...',                # puntos suspensivos
        '\u2022': '-',                  # bullet
        '\u20AC': chr(164),             # Euro -> ¤
        '\u2122': '(TM)',              # Trademark
        '\u00A0': ' ',                  # non-breaking space
        '\u00AD': '',                  # soft hyphen
    }

    resultado = []
    for char in texto:
        codigo = ord(char)
        if codigo <= 255:
            resultado.append(char)
        elif char in MAPA_UNICODE:
            resultado.append(MAPA_UNICODE[char])
        else:
            # Decomposition fallback: ej. ñ -> n + ~
            descomp = unicodedata.decomposition(char)
            if descomp:
                base = descomp.split()[0] if descomp else ''
                try:
                    base_char = chr(int(base, 16)) if base else '?'
                    if ord(base_char) <= 255:
                        resultado.append(base_char)
                    else:
                        resultado.append('?')
                except (ValueError, IndexError):
                    resultado.append('?')
            else:
                resultado.append('?')

    return ''.join(resultado)

def generar_json_desde_informe(
    informe: str,
    prompt_json_extractor: str,
    modelo: str = 'gpt-oss:120b-cloud'
) -> str:
    """
    Genera un JSON a partir de un informe usando Ollama.

    Args:
        informe: Texto del informe
        prompt_json_extractor: Prompt para extraer JSON del informe
        modelo: Modelo de Ollama a utilizar

    Returns:
        JSON generado por el modelo

    Raises:
        JSONGenerationError: Si ocurre un error al generar el JSON
    """
    if ollama is None:
        raise JSONGenerationError("La libreria ollama no esta instalada. "
                                "Instalala con: pip install ollama")

    try:
        logger.info("Generando JSON desde informe")

        respuesta_json = ollama.chat(
            model=modelo,
            format='json',
            messages=[
                {'role': 'system', 'content': prompt_json_extractor},
                {'role': 'user', 'content': f"Transforma el siguiente informe en un objeto JSON: {informe}"}
            ]
        )

        return respuesta_json['message']['content']

    except Exception as e:
        error_msg = f"Error al generar JSON: {e}"
        logger.error(error_msg)
        raise JSONGenerationError(error_msg)

def guardar_json(json_data: str, nombre_archivo: str) -> None:
    """
    Guarda datos JSON en un archivo.

    Args:
        json_data: Datos JSON a guardar
        nombre_archivo: Nombre del archivo JSON de salida

    Raises:
        JSONGenerationError: Si ocurre un error al guardar el JSON
    """
    try:
        # Crear directorio si no existe
        output_path = Path(nombre_archivo)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Guardando JSON: {output_path.resolve()}")

        with open(output_path, "w", encoding='utf-8') as f:
            f.write(json_data)

        logger.info(f"JSON guardado exitosamente: {output_path.resolve()}")

    except Exception as e:
        error_msg = f"Error al guardar JSON {nombre_archivo}: {e}"
        logger.error(error_msg)
        raise JSONGenerationError(error_msg)

def generar_informe_completo(config) -> None:
    """
    Genera un informe completo utilizando la configuracion proporcionada.

    Args:
        config: Objeto de configuracion

    Raises:
        DataValidationError: Si la configuracion es invalida
        PDFExtractionError: Si ocurre un error al extraer texto de PDFs
        OllamaGenerationError: Si ocurre un error al generar el informe
        PDFGenerationError: Si ocurre un error al generar el PDF
        JSONGenerationError: Si ocurre un error al generar o guardar el JSON
    """
    try:
        # Validar configuracion
        validate_config(config.to_dict())
        logger.info("Configuracion validada correctamente")
    except DataValidationError as e:
        logger.error(f"Configuracion invalida: {e}")
        raise

    logger.info("Iniciando generacion de informe completo")

    # Verificar disponibilidad de Ollama antes de continuar
    modelo = config.get("ollama_model")
    if not verificar_ollama(modelo):
        logger.warning("Ollama puede no estar disponible. Continuando de todos modos...")

    try:
        # Extraer texto de los PDFs de entrada
        info_texto = extraer_texto_pdf(config.get("input_pdf"))
        mi_prompt = extraer_texto_pdf(config.get("prompt_pdf"))
        mis_instrucciones = extraer_texto_pdf(config.get("structure_pdf"))
        prompt_json_extractor = extraer_texto_pdf(config.get("json_prompt_pdf"))

        # Diagnosticar texto extrado
        logger.info("--- COMPROBANDO LECTURA DE PDFs ---")
        logger.info(f"Caracteres extrados de {config.get('input_pdf')}: {len(info_texto)}")
        logger.info(f"Caracteres extrados de {config.get('prompt_pdf')}: {len(mi_prompt)}")
        logger.info(f"Caracteres extrados de {config.get('structure_pdf')}: {len(mis_instrucciones)}")

        if len(info_texto) < 20 or len(mi_prompt) < 20:
            logger.warning("ATENCION! PyMuPDF apenas leyo texto. "
                          "Tu PDF esta vacio o es una imagen escaneada.")
            logger.warning("Por eso la IA se lo inventa: no esta recibiendo ninguna informacion.")

        # Generar datos temporales
        json_cronograma = generar_datos_temporales()
        logger.info("--- DATOS TEMPORALES SIMULADOS ---")
        logger.debug(f"Datos temporales: {json_cronograma[:300]}...")

        # Generar informe pedagógico narrativo y JSON
        logger.info("[1/2] Generando Informe Pedagogico Narrativo y JSON...")

        modelo = config.get("ollama_model")
        opts = config.get("ollama_options")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Enviar ambas tareas en paralelo
            futuro_texto = executor.submit(
                generar_texto_estructurado,
                info_texto, mi_prompt, mis_instrucciones, json_cronograma, modelo, opts
            )
            # Preparar datos para JSON (se genera después del texto)
            futuro_json = None

            # Primero obtener el texto
            texto_final = futuro_texto.result()

            logger.info("=== RESULTADO GENERADO ===")
            logger.debug(f"Texto generado: {texto_final[:500]}...")

            # Una vez tenemos el texto, lanzar extracción JSON en paralelo
            if texto_final and not texto_final.startswith("Error"):
                futuro_json = executor.submit(
                    generar_json_desde_informe,
                    texto_final, prompt_json_extractor, modelo
                )

                # Guardar resultado en PDF
                guardar_resultado_en_pdf(
                    texto_final,
                    nombre_archivo=config.get("output_pdf")
                )

                # Obtener JSON y guardar
                respuesta_json = futuro_json.result()
                guardar_json(respuesta_json, config.get("output_json"))

        logger.info("-- GENERACION FINALIZADA --")

    except Exception as e:
        logger.error(f"Error en la generacion del informe: {e}", exc_info=True)
        raise
