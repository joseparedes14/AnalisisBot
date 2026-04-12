import ollama
import fitz  # PyMuPDF
import os

def generar_texto_estructurado(informacion, prompt_tarea, instrucciones_estructura, modelo="llama3.2"):
    """
    Genera un texto usando Ollama basándose en información previa, 
    una tarea a realizar y unas instrucciones estrictas de formato.
    """
    
    # 1. Mensaje de Sistema (System Prompt)
    # Fortalecemos el prompt para que RAZONE y EXTIENDA la información, pero sin inventarla.
    mensaje_sistema = f"""Eres un experto analista y consultor profesional. 
Tu objetivo es redactar informes PROFUNDOS, DETALLADOS y BIEN RAZONADOS, aportando un alto nivel de análisis académico, pero anclándote exclusivamente en los hechos proporcionados.

REGLAS DE GENERACIÓN:
1. FIDELIDAD: Los datos, números, porcentajes y nombres provendrán ÚNICAMENTE de la INFORMACIÓN DE CONTEXTO. Si un dato no existe, indica "No especificado", no te lo inventes.
2. PROFUNDIDAD DE ANÁLISIS (MUY IMPORTANTE): No te limites a copiar y pegar los datos de forma simple. Debes DESARROLLAR párrafos completos, extensos y bien argumentados explicando las implicaciones de lo observado. Si un dato es negativo o positivo, razona las causas, aporta una reflexión madura y ofrece sugerencias extensas.
3. ESTILO: Escribe con un tono formal, rico en vocabulario y altamente argumentativo.
4. ESTRUCTURA: Encaja esta narrativa extensa dentro de los encabezados solicitados. No añadas saludos ni comentarios extra fuera de la estructura.
5. NO REPETICIÓN: Genera CADA SECCIÓN EXACTAMENTE UNA VEZ. Cuando llegues al final de la estructura solicitada, DEBES DETENERTE de inmediato. JAMÁS repitas bloques, cierres o recomendaciones.
6. DEBES ANALIZAR TODAS ESTAS VARIABLES SIN EXCEPCION: (PSR, APSUD, ALD, SR, TTC, MR, VSUR, PSUR). DANDO UNA APRECIACIÓN SUBJETIVA PERO FUNDAMENTADA EN LA PARTE DE MÉTRICA GLOBAL.

INSTRUCCIONES DE ESTRUCTURA A SEGUIR:
{instrucciones_estructura}
"""

    # 2. Mensaje del Usuario (User Prompt)
    # Aquí le pasamos los DATOS (información) y lo que queremos que HAGA con ellos (tarea).
    mensaje_usuario = f"""INFORMACIÓN DE CONTEXTO:
\"\"\"
{informacion}
\"\"\"

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
                "temperature": 0.4, # Subimos la T a 0.4 para que pueda redactar y razonar con mejor vocabulario
                "top_p": 0.6, # Permite construir respuestas más elaboradas
                "num_ctx": 8192, # Importante para la cantidad de texto a procesar
                "repeat_penalty": 1.15 
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

        
    texto_final = generar_texto_estructurado(
        informacion=info_texto,
        prompt_tarea=mi_prompt,
        instrucciones_estructura=mis_instrucciones,
        modelo="llama3.1" 
        )
        
    print("=== RESULTADO GENERADO ===\n")
    print(texto_final)
    
   
    if not texto_final.startswith("Error"):
        guardar_resultado_en_pdf(texto_final, nombre_archivo="Respuesta_Agente_Ollama.pdf")
