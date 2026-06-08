"""
Interfaz gráfica para el Generador de Informes Pedagógicos.
Ejecutar con: streamlit run app.py
"""

import streamlit as st
import json
import os
import tempfile
from pathlib import Path

# Configuración de la página
st.set_page_config(
    page_title="Generador de Informes Pedagógicos",
    page_icon="📚",
    layout="wide"
)

# Título y descripción
st.title("📚 Generador de Informes Pedagógicos")
st.markdown("""
*Herramienta de análisis pedagógico que genera informes estructurados usando modelos de lenguaje locales (Ollama).*
""")

# Sidebar con configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Verificar Ollama
    try:
        import ollama
        modelos = [m['model'] for m in ollama.list().get('models', [])]
        if modelos:
            st.success(f"✅ Ollama conectado ({len(modelos)} modelos)")
            modelo_seleccionado = st.selectbox(
                "Modelo a utilizar",
                modelos,
                index=0
            )
        else:
            st.error("❌ No hay modelos instalados")
            modelo_seleccionado = None
    except Exception as e:
        st.error(f"❌ Error al conectar con Ollama: {e}")
        modelo_seleccionado = None
    
    st.divider()
    
    # Opciones de generación
    st.subheader("Parámetros de generación")
    temperatura = st.slider("Temperatura", 0.0, 1.0, 0.1, 0.05)
    top_p = st.slider("Top-p", 0.0, 1.0, 0.8, 0.05)
    num_ctx = st.number_input("Contexto máximo", 1024, 32768, 8192, 1024)
    
    st.divider()
    st.markdown("""
    **Instrucciones:**
    1. Sube los 4 PDFs de entrada
    2. Selecciona el modelo
    3. Haz clic en "Generar Informe"
    """)

# Contenido principal
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📄 Archivos de entrada")
    
    # Subir PDFs
    input_pdf = st.file_uploader(
        "PDF de contexto (PruebaInforme.pdf)",
        type=['pdf'],
        key='input'
    )
    
    prompt_pdf = st.file_uploader(
        "PDF de prompt (PROMPTMEJORADO.pdf)",
        type=['pdf'],
        key='prompt'
    )
    
    structure_pdf = st.file_uploader(
        "PDF de estructura (FORMATO_SALIDA.pdf)",
        type=['pdf'],
        key='structure'
    )
    
    json_prompt_pdf = st.file_uploader(
        "PDF de prompt JSON (PROMPT_JSON.pdf)",
        type=['pdf'],
        key='json_prompt'
    )

with col2:
    st.header("📊 Resultados")
    
    # Botón de generación
    generar = st.button(
        "🚀 Generar Informe",
        type="primary",
        disabled=(modelo_seleccionado is None)
    )
    
    # Placeholder para resultados
    resultado_placeholder = st.empty()
    progress_bar = st.empty()

if generar:
    # Validar que todos los PDFs estén subidos
    if not all([input_pdf, prompt_pdf, structure_pdf, json_prompt_pdf]):
        st.error("❌ Por favor, sube los 4 PDFs de entrada")
    else:
        # Guardar PDFs temporalmente
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Guardar archivos subidos
            input_path = os.path.join(tmp_dir, "PruebaInforme.pdf")
            prompt_path = os.path.join(tmp_dir, "PROMPTMEJORADO.pdf")
            structure_path = os.path.join(tmp_dir, "FORMATO_SALIDA.pdf")
            json_prompt_path = os.path.join(tmp_dir, "PROMPT_JSON.pdf")
            
            with open(input_path, "wb") as f:
                f.write(input_pdf.getbuffer())
            with open(prompt_path, "wb") as f:
                f.write(prompt_pdf.getbuffer())
            with open(structure_path, "wb") as f:
                f.write(structure_pdf.getbuffer())
            with open(json_prompt_path, "wb") as f:
                f.write(json_prompt_pdf.getbuffer())
            
            # Configurar paths de salida
            output_pdf = os.path.join(tmp_dir, "informe_generado.pdf")
            output_json = os.path.join(tmp_dir, "data_auditoria.json")
            
            # Progreso
            progress_bar.progress(0, text="Iniciando generación...")
            
            try:
                # Importar módulos del proyecto
                from src.core.config import Config
                from src.core.generador_texto_ollama import (
                    extraer_texto_pdf,
                    generar_texto_estructurado,
                    generar_json_desde_informe,
                    guardar_resultado_en_pdf,
                    generar_datos_temporales,
                    generar_tabla_markdown
                )
                from src.core.validators import validate_temporal_data
                
                # Crear configuración
                config_data = {
                    "input_pdf": input_path,
                    "prompt_pdf": prompt_path,
                    "structure_pdf": structure_path,
                    "json_prompt_pdf": json_prompt_path,
                    "output_pdf": output_pdf,
                    "output_json": output_json,
                    "ollama_model": modelo_seleccionado,
                    "ollama_options": {
                        "temperature": temperatura,
                        "top_p": top_p,
                        "num_ctx": num_ctx
                    }
                }
                
                config = Config(config_data)
                
                # Paso 1: Extraer textos
                progress_bar.progress(10, text="Extrayendo texto de PDFs...")
                info_texto = extraer_texto_pdf(input_path)
                mi_prompt = extraer_texto_pdf(prompt_path)
                mis_instrucciones = extraer_texto_pdf(structure_path)
                prompt_json_extractor = extraer_texto_pdf(json_prompt_path)
                
                # Paso 2: Generar datos temporales
                progress_bar.progress(30, text="Generando datos temporales...")
                json_cronograma = generar_datos_temporales()
                
                # Paso 3: Generar informe
                progress_bar.progress(50, text=f"Generando informe con {modelo_seleccionado}... (esto puede tardar 2-5 min)")
                texto_final = generar_texto_estructurado(
                    info_texto, mi_prompt, mis_instrucciones,
                    json_cronograma, modelo_seleccionado,
                    config.get("ollama_options")
                )
                
                # Paso 4: Guardar PDF
                progress_bar.progress(80, text="Guardando PDF...")
                guardar_resultado_en_pdf(texto_final, output_pdf)
                
                # Paso 5: Generar JSON
                progress_bar.progress(90, text="Generando JSON...")
                respuesta_json = generar_json_desde_informe(
                    texto_final, prompt_json_extractor, modelo_seleccionado
                )
                
                # Guardar JSON
                with open(output_json, "w", encoding="utf-8") as f:
                    f.write(respuesta_json)
                
                progress_bar.progress(100, text="✅ ¡Generación completada!")
                
                # Mostrar resultados
                with resultado_placeholder.container():
                    st.success("✅ Informe generado exitosamente")
                    
                    # Vista previa del texto
                    with st.expander("📖 Vista previa del informe", expanded=True):
                        st.text_area(
                            "Contenido del informe",
                            texto_final,
                            height=400,
                            disabled=True
                        )
                    
                    # Descargas
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        with open(output_pdf, "rb") as f:
                            st.download_button(
                                "📥 Descargar PDF",
                                f.read(),
                                "informe_pedagogico.pdf",
                                "application/pdf"
                            )
                    
                    with col2:
                        with open(output_json, "rb") as f:
                            st.download_button(
                                "📥 Descargar JSON",
                                f.read(),
                                "data_auditoria.json",
                                "application/json"
                            )
                    
                    # Mostrar JSON formateado
                    with st.expander("📋 Datos JSON"):
                        try:
                            json_data = json.loads(respuesta_json)
                            st.json(json_data)
                        except:
                            st.code(respuesta_json, language="json")
            
            except Exception as e:
                progress_bar.progress(100, text="❌ Error en la generación")
                st.error(f"Error: {str(e)}")
                st.exception(e)

# Footer
st.divider()
st.markdown("""
<small>Generador de Informes Pedagógicos v1.0 | Powered by Ollama + Streamlit</small>
""", unsafe_allow_html=True)
