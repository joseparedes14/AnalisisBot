import ollama
import fitz  # PyMuPDF
import os

def generar_texto_estructurado(informacion, prompt_tarea, instrucciones_estructura, modelo="llama3.2"):
    """
    Genera un texto usando Ollama basándose en información previa, 
    una tarea a realizar y unas instrucciones estrictas de formato.
    """
    
    # 1. Mensaje de Sistema (System Prompt)
    # Fortalecemos el prompt para prohibir la alucinación
    mensaje_sistema = f"""Eres un asistente altamente disciplinado y un extractor de datos extremadamente preciso.
Tu MISION PRINCIPAL es procesar la información de contexto sin inventar absolutamente nada, y devolver el resultado siguiendo ESTRICTAMENTE las instrucciones de formato.

REGLAS CRÍTICAS (ANTI-ALUCINACIÓN):
1. Basa tus respuestas ÚNICA Y EXCLUSIVAMENTE en el texto proporcionado en la INFORMACIÓN DE CONTEXTO.
2. Si un dato no aparece en el texto, SIEMPRE debes escribir "No especificado en el texto". JAMÁS adivines o inventes datos.
3. No añadas saludos, ni introducciones, ni texto extra ajeno a las instrucciones de estructura.
4. Tu respuesta debe ser una copia fiel de los HECHOS del texto, adaptados a la estructura solicitada.

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
                "temperature": 0.0, # (0.0 elimina la creatividad por completo para tareas de extracción)
                "top_p": 0.1, # Filtra respuestas raras
                "num_ctx": 8192 # Importante para la cantidad de texto a procesar
            }
        )
        return respuesta['message']['content']
        
    except Exception as e:
        return f"Error al generar texto con Ollama: {e}\n(Verifica que Ollama esté abierto y tengas el modelo '{modelo}' instalado)."
def extraer_texto_pdf(ruta_pdf):
    """
    Lee un archivo PDF y extrae todo su texto página por página.
    Requiere tener instalado PyMuPDF (pip install pymupdf).
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
        modelo="llama3.1" # <--- IMPORTANTE: Pon aquí el modelo que tengas descargado (llama3, llama3.1, mistral, phi3...)
        )
        
    print("=== RESULTADO GENERADO ===\n")
    print(texto_final)
