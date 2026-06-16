"""
Modulo principal para la generacion de informes pedagogicos con Ollama.

Este modulo proporciona las funciones principales para:
- Extraer texto de archivos PDF
- Generar informes estructurados con Ollama
- Guardar resultados en PDF y JSON
"""

import json
import os
import importlib
import concurrent.futures
from typing import Optional, Dict, Any, Union, List
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
from .input_processor import procesar_json_transcripcion

# Configurar logger
logger = get_logger(__name__)

def listar_modelos_ollama() -> List[str]:
    """Devuelve la lista de modelos disponibles en Ollama."""
    if ollama is None:
        return []
    try:
        modelos = ollama.list()
        return [m['model'] for m in modelos.get('models', [])]
    except (ConnectionError, TimeoutError):
        return []

def verificar_ollama(modelo: str = 'llama3.2:latest') -> bool:
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

    except (ConnectionError, TimeoutError) as e:
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

    except (fitz.FileDataError, RuntimeError) as e:
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
    modelo: str = 'llama3.2:latest',
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

    if options is None:
        options = {}

    # 1. Cargar System Prompt desde archivo externo
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "system_prompt.txt"
    system_prompt_template = prompt_path.read_text(encoding="utf-8")
    mensaje_sistema = system_prompt_template.format(instrucciones_estructura=instrucciones_estructura)

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
        except (ValueError, TypeError) as e:
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

    except (KeyError, TypeError, ConnectionError) as e:
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
    _has_reportlab = importlib.util.find_spec("reportlab") is not None

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

        if _has_reportlab:
            _generar_pdf_reportlab(texto_limpio, str(output_path), fuente_unicode)

        elif fpdf2_mod:
            _generar_pdf_fpdf2(texto_limpio, str(output_path), fuente_unicode, fpdf2_mod)

        else:
            _generar_pdf_fpdf(texto_limpio, str(output_path))

        logger.info(f"PDF generado exitosamente: {output_path.resolve()}")
        return True

    except (IOError, OSError, RuntimeError) as e:
        error_msg = f"Error al generar el PDF {nombre_archivo}: {e}"
        logger.error(error_msg)
        raise PDFGenerationError(error_msg)


def _generar_pdf_reportlab(texto: str, output_path: str, fuente_unicode: str) -> None:
    """Genera PDF usando reportlab con soporte Unicode."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.enums import TA_LEFT

    doc = SimpleDocTemplate(str(output_path), pagesize=A4,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)

    nombre_fuente = 'Helvetica'
    if fuente_unicode:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        try:
            pdfmetrics.registerFont(TTFont('FuenteUnicode', fuente_unicode))
            nombre_fuente = 'FuenteUnicode'
        except (IOError, OSError):
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
        except (IOError, OSError, RuntimeError):
            pdf.set_font("Helvetica", size=11)
    else:
        pdf.set_font("Helvetica", size=11)

    pdf.multi_cell(0, 6, text=texto)
    pdf.output(str(output_path))


def _generar_pdf_fpdf(texto: str, output_path: str) -> None:
    """Genera PDF usando fpdf original (sin Unicode)."""
    from fpdf import FPDF

    pdf = FPDF(core_fonts_encoding="utf-8")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("helvetica", size=11)

    for linea in texto.split('\n'):
        if linea.strip():
            pdf.multi_cell(0, 6, text=linea)  # En fpdf2 se usa 'text', no 'txt'

    pdf.output(str(output_path))



def generar_json_desde_informe(
    informe: str,
    prompt_json_extractor: str,
    modelo: str = 'llama3.2:latest'
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

    except (KeyError, TypeError, ConnectionError) as e:
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

    except (IOError, OSError, json.JSONDecodeError) as e:
        error_msg = f"Error al guardar JSON {nombre_archivo}: {e}"
        logger.error(error_msg)
        raise JSONGenerationError(error_msg)

def generar_informe_completo(config: object) -> None:
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

    # Verificar que el JSON de entrada exista
    input_source = config.get("input_source")
    if not Path(input_source).exists():
        error_msg = f"El archivo JSON de entrada no existe: {input_source}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Verificar que los PDFs de configuración existan
    pdfs_requeridos = {
        "prompt_pdf": config.get("prompt_pdf"),
        "structure_pdf": config.get("structure_pdf"),
        "json_prompt_pdf": config.get("json_prompt_pdf")
    }
    
    pdfs_faltantes = []
    for nombre, ruta in pdfs_requeridos.items():
        if not Path(ruta).exists():
            pdfs_faltantes.append(f"  - {nombre}: {ruta}")
    
    if pdfs_faltantes:
        error_msg = "Faltan los siguientes archivos PDF de configuración:\n" + "\n".join(pdfs_faltantes)
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Verificar disponibilidad de Ollama antes de continuar
    modelo = config.get("ollama_model")
    if not verificar_ollama(modelo):
        logger.warning("Ollama puede no estar disponible. Continuando de todos modos...")

    try:
        # Procesar JSON de transcripción y calcular métricas reales
        logger.info("--- PROCESANDO JSON DE TRANSCRIPCIÓN ---")
        datos_clase = procesar_json_transcripcion(
            input_source,
            teacher_speaker=config.get("teacher_speaker", "auto")
        )
        
        logger.info(f"Metadata: {datos_clase['metadata']}")
        logger.info(f"Métricas calculadas: {list(datos_clase['metricas'].keys())}")

        # Extraer texto de los PDFs de configuración
        mi_prompt = extraer_texto_pdf(config.get("prompt_pdf"))
        mis_instrucciones = extraer_texto_pdf(config.get("structure_pdf"))
        prompt_json_extractor = extraer_texto_pdf(config.get("json_prompt_pdf"))

        logger.info(f"Caracteres extraídos de {config.get('prompt_pdf')}: {len(mi_prompt)}")
        logger.info(f"Caracteres extraídos de {config.get('structure_pdf')}: {len(mis_instrucciones)}")

        # Generar informe pedagógico narrativo y JSON
        logger.info("[1/2] Generando Informe Pedagogico Narrativo y JSON...")

        modelo = config.get("ollama_model")
        opts = config.get("ollama_options")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Enviar generación de texto con métricas reales
            futuro_texto = executor.submit(
                generar_texto_estructurado,
                json.dumps(datos_clase['metricas'], indent=2, ensure_ascii=False),
                mi_prompt,
                mis_instrucciones,
                None,  # No necesitamos datos temporales simulados
                modelo,
                opts
            )

            # Obtener el texto (con manejo de errores)
            try:
                texto_final = futuro_texto.result(timeout=300)
            except concurrent.futures.TimeoutError:
                raise OllamaGenerationError("La generación de texto excedió el tiempo límite (5 min)")
            except (OllamaGenerationError, TimeoutError) as e:
                raise OllamaGenerationError(f"Error al generar texto: {e}")

            logger.info("=== RESULTADO GENERADO ===")
            logger.debug(f"Texto generado: {texto_final[:500]}...")

            # Guardar resultado en PDF (primero, antes del JSON)
            guardar_resultado_en_pdf(
                texto_final,
                nombre_archivo=config.get("output_pdf")
            )

            # Generar y guardar JSON
            if texto_final and not texto_final.startswith("Error"):
                futuro_json = executor.submit(
                    generar_json_desde_informe,
                    texto_final, prompt_json_extractor, modelo
                )
                
                try:
                    respuesta_json = futuro_json.result(timeout=120)
                    
                    # Guardar JSON con métricas reales + análisis del LLM
                    datos_salida = {
                        "metadata": datos_clase['metadata'],
                        "metricas": datos_clase['metricas'],
                        "analisis_llm": respuesta_json
                    }
                    guardar_json(json.dumps(datos_salida, indent=2, ensure_ascii=False), config.get("output_json"))
                    
                except concurrent.futures.TimeoutError:
                    logger.warning("La generación de JSON excedió el tiempo límite. Se omite JSON.")
                except (JSONGenerationError, TimeoutError) as e:
                    logger.warning(f"Error al generar JSON: {e}. Se omite JSON.")

        logger.info("-- GENERACION FINALIZADA --")

    except (DataValidationError, PDFExtractionError, OllamaGenerationError, PDFGenerationError, JSONGenerationError, FileNotFoundError) as e:
        logger.error(f"Error en la generacion del informe: {e}", exc_info=True)
        raise
