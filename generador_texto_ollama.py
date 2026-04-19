import ollama
import fitz  # PyMuPDF
import os
from simulador import generar_datos_temporales

def generar_texto_estructurado(informacion, prompt_tarea, instrucciones_estructura, datos_temporales_json=None, modelo="llama3.2"):
    """
    Genera un texto usando Ollama basándose en información previa, 
    una tarea a realizar, instrucciones de formato y datos temporales (JSON).
    """
    
    # 1. Mensaje de Sistema (System Prompt)
    # Fortalecemos el prompt para que RAZONE y EXTIENDA la información, pero sin inventarla.
    mensaje_sistema = f"""Eres un experto analista y consultor profesional. 
Tu objetivo es redactar informes PROFUNDOS, DETALLADOS y BIEN RAZONADOS, aportando un alto nivel de análisis académico, pero anclándote exclusivamente en los hechos proporcionados.

REGLAS DE GENERACIÓN:
1. FIDELIDAD: Los datos cuantitativos provendrán ÚNICAMENTE de la INFORMACIÓN DE CONTEXTO. No inventes métricas ni números.
2. PROFUNDIDAD Y PENSAMIENTO CRÍTICO (MUY IMPORTANTE): Ve más allá de lo descriptivo. Para cada métrica o hallazgo clave, realiza una EVALUACIÓN CRÍTICA EXHAUSTIVA: explora el "por qué" detrás de los números, formula hipótesis lógicas de por qué ocurrieron, cruza la información de distintas variables (correlaciones), prevé riesgos y plantea recomendaciones estratégicas a nivel macro.
3. ESTILO: Escribe con un tono sumamente prolijo, formal, complejo y altamente argumentativo, digno de una auditoría de alto nivel o tesis.
4. ESTRUCTURA: Encaja esta narrativa extensa dentro de los encabezados solicitados. No añadas saludos ni comentarios extra fuera de la estructura.
5. NO REPETICIÓN: Genera CADA SECCIÓN EXACTAMENTE UNA VEZ. Cuando llegues al final de la estructura solicitada, DEBES DETENERTE de inmediato. JAMÁS repitas bloques, cierres o recomendaciones.
6. EJECUCIÓN ESTRICTA DE LAS 8 VARIABLES GLOBALES: En "Métricas Globales y Comparativas", TIENES LA OBLIGACIÓN IRRENUNCIABLE de listar y analizar las OCHO (8) VARIABLES: PSR, APSUD, ALD, SR, TTC, MR, VSUR y PSUR. Si omites ALD, SR, TTC, MR o VSUR o generas menos de 8 viñetas habrás fallado gravemente. Para cada viñeta "* **[NOMBRE DE VARIABLE]**: [Análisis]" redacta una evaluación experta, profunda e hipotética, cruzando datos para diagnosticar el impacto y el estilo. PROHIBIDA la superficialidad o limitarse a repetir qué significa el número matemático.
7. AGRUPACIÓN EN BLOQUES IRREGULARES CON DATOS REALES: Rompe la sesión en bloques temporales asimétricos (ej. 0-14, 14-37, etc.) garantizando siempre un mínimo de 10 min por bloque. Jamás cortes matemáticamente de 10 en 10. Dentro de cada bloque analiza SÓLO "Protagonismo" y "Dinámica Discursiva". FUNDAMENTAL: Observa la tabla de datos temporal REAL provista, deduce a partir de sus variaciones por qué elegiste ese bloque y explica con profundidad pedagógica qué estaba haciendo el docente apoyándote en ESOS números reales.
8. PROHIBICIÓN DE TABLAS DE BLOQUES AL CIERRE: Es crítico que al final NO introduzcas tablas de resumen por bloque ni enumeraciones que no estén dictadas específicamente por las instrucciones formales.
9. PARTICIPACIÓN ESTUDIANTIL CON DATOS REALES: En "Análisis de la participación estudiantil", DEBES extraer y utilizar obligatoriamente los datos de las intervenciones (ej. "Number of distinct students", "Number of significant interventions", etc.) que se provean en el contexto de entrada. Asegúrate de diagnosticar en base a esos números si la participación es concentrada (pocas voces) o distribuida.
10. NO REALICES LA TABLA DE SÍNTESIS FINAL

INSTRUCCIONES DE ESTRUCTURA A SEGUIR:
{instrucciones_estructura}
"""

    # 2. Mensaje del Usuario (User Prompt)
    # Aquí le pasamos los DATOS (información) y lo que queremos que HAGA con ellos (tarea).
    
    bloque_temporal_str = ""
    if datos_temporales_json:
        try:
            import json
            # Parseamos el JSON si es un string
            datos = json.loads(datos_temporales_json) if isinstance(datos_temporales_json, str) else datos_temporales_json
            
            # Verificamos si es una lista de diccionarios (el formato ideal para una tabla)
            if isinstance(datos, list) and len(datos) > 0 and isinstance(datos[0], dict):
                # Extraemos las claves directamente para hacerlas encabezados sin filtros
                claves = list(datos[0].keys())
                
                # Construimos la tabla Markdown de la manera más sencilla posible
                encabezado = "| " + " | ".join(claves) + " |"
                separador = "| " + " | ".join(["---"] * len(claves)) + " |"
                
                filas = ["| " + " | ".join(str(item.get(k, "")) for k in claves) + " |" for item in datos]
                tabla_md = "\n".join([encabezado, separador] + filas)
                
                bloque_temporal_str = f"\nDATOS TEMPORALES DEL DESARROLLO (EN FORMATO TABLA):\n\n{tabla_md}\n\n"
            else:
                # Si no es lista de dicts, lo dejamos como JSON
                bloque_temporal_str = f"\nDATOS TEMPORALES DEL DESARROLLO (JSON):\n\"\"\"\n{datos_temporales_json}\n\"\"\"\n"
        except Exception:
            # En caso de error al parsear, usamos el valor original
            bloque_temporal_str = f"\nDATOS TEMPORALES DEL DESARROLLO (JSON):\n\"\"\"\n{datos_temporales_json}\n\"\"\"\n"

    mensaje_usuario = f"""INFORMACIÓN DE CONTEXTO:
\"\"\"
{informacion}
\"\"\"{bloque_temporal_str}

TAREA A REALIZAR CON LA INFORMACIÓN (PROMPT):
{prompt_tarea}
"""

    try:
        # 3. Llamada al modelo local usando la librería de Ollama
        respuesta = ollama.chat(
            model=modelo,
            messages=[
                {'role': 'system', 'content': mensaje_sistema},
                {'role': 'user', 'content': mensaje_usuario}
            ],
            options={
                "temperature": 0.2, # Disminuido drásticamente para mayor obediencia a las reglas y evitar alucinaciones
                "top_p": 0.9, 
                "num_ctx": 8192, # Suficiente memoria para procesar la tabla y contextos sin truncarlos
                "repeat_penalty": 1.05 # Bajado para evitar que la IA se niegue a escribir las siglas de las métricas (PSR etc) pensando que está repitiéndose
            }
        )
        return respuesta['message']['content']
        
    except Exception as e:
        return f"Error al generar texto con Ollama: {e}\n(Verifica que Ollama esté abierto y tengas el modelo '{modelo}' instalado)."
def guardar_resultado_en_pdf(texto, nombre_archivo="resultado_agente.pdf"):
    """
    Guarda el texto proporcionado en un archivo PDF.
    Requiere instalada la librería fpdf (pip install fpdf).
    """
    try:
        from fpdf import FPDF
    except ImportError:
        print("\n[-] Error: La librería 'fpdf' no está instalada.")
        print("Por favor, instálala ejecutando en tu terminal: pip install fpdf")
        return False
        
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=11)
        
        # Limpiamos el texto para evitar errores con caracteres especiales en FPDF básico
        texto_limpio = texto.encode('latin-1', 'replace').decode('latin-1')
        
        # multi_cell permite que el texto haga saltos de línea automáticos
        pdf.multi_cell(0, 6, txt=texto_limpio)
        pdf.output(nombre_archivo)
        print(f"\n[+] PDF generado y guardado exitosamente: {nombre_archivo}")
        return True
    except Exception as e:
        print(f"\n[-] Error al generar el PDF: {e}")
        return False

def extraer_texto_pdf(ruta_pdf):
    """
    Lee un archivo PDF y extrae todo su texto página por página.
   
    """
    if not os.path.exists(ruta_pdf):
        return f"[Error: El archivo '{ruta_pdf}' no existe]"
        
    try:
        texto_completo = ""
        doc = fitz.open(ruta_pdf)
        for num_pagina in range(len(doc)):
            pagina = doc.load_page(num_pagina)
            texto_completo += pagina.get_text("text") + "\n"
        return texto_completo.strip()
    except Exception as e:
        return f"[Error al leer el PDF: {e}]"

# ==========================================
# EJEMPLO DE USO (CÓMO LLAMAR A LA FUNCIÓN)
# ==========================================
if __name__ == "__main__":
   

    info_texto = extraer_texto_pdf("PruebaInforme.pdf")
    mi_prompt = extraer_texto_pdf('PROMPTMEJORADO.pdf')
    mis_instrucciones = extraer_texto_pdf('FORMATO_SALIDA.pdf')

    # === DIAGNÓSTICO DE TEXTO EXTRAÍDO ===
    print("\n--- COMPROBANDO LECTURA DE PDFs ---")
    print(f"Caracteres extraídos de PruebaInforme: {len(info_texto)}")
    print(f"Caracteres extraídos de PROMPTMEJORADO: {len(mi_prompt)}")
    print(f"Caracteres extraídos de FORMATO_SALIDA: {len(mis_instrucciones)}")
    
    if len(info_texto) < 20 or len(mi_prompt) < 20:
        print("¡ATENCION! PyMuPDF apenas leyó texto. Tu PDF está vacío o es una imagen escaneada.")
        print("Por eso la IA se lo inventa: no está recibiendo ninguna información.")
    print("-----------------------------------\n")

        
    json_cronograma = generar_datos_temporales()
    print("\n--- DATOS TEMPORALES SIMULADOS ---")
    print(json_cronograma[:300] + "...\n(Acortado para visualización)\n")

    texto_final = generar_texto_estructurado(
        informacion=info_texto,
        prompt_tarea=mi_prompt,
        instrucciones_estructura=mis_instrucciones,
        datos_temporales_json=json_cronograma,
        modelo="llama3.1" 
        )
        
    print("=== RESULTADO GENERADO ===\n")
    print(texto_final)
    
   
    if not texto_final.startswith("Error"):
        guardar_resultado_en_pdf(texto_final, nombre_archivo="Respuesta_Agente_Ollama.pdf")
