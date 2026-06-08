"""
Interfaz simplificada para docentes.
El docente sube su documento de observación y recibe el análisis automáticamente.
"""

import streamlit as st
import json
import os
import tempfile
from pathlib import Path

# Configuración de la página
st.set_page_config(
    page_title="Análisis Pedagógico",
    page_icon="📚",
    layout="centered"
)

# Título
st.title("📚 Análisis Pedagógico de Aula")
st.markdown("*Sube tu documento de observación y obtén un análisis profesional automáticamente.*")

# Sidebar con configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Verificar Ollama
    try:
        import ollama
        modelos = [m['model'] for m in ollama.list().get('models', [])]
        if modelos:
            st.success(f"✅ Ollama conectado")
            modelo_seleccionado = st.selectbox(
                "Modelo a utilizar",
                modelos,
                index=0
            )
        else:
            st.error("❌ No hay modelos instalados")
            modelo_seleccionado = None
    except Exception as e:
        st.error(f"❌ Error con Ollama")
        modelo_seleccionado = None
    
    st.divider()
    
    # Parámetros básicos
    st.subheader("Parámetros")
    temperatura = st.slider("Temperatura", 0.0, 1.0, 0.1, 0.05)
    
    st.divider()
    st.markdown("""
    **Instrucciones:**
    1. Sube tu PDF de observación
    2. Haz clic en "Analizar"
    3. Descarga el resultado
    """)

# PDFs de configuración que ya están en el proyecto
CONFIG_PDFS = {
    "prompt_pdf": "PROMPTMEJORADO.pdf",
    "structure_pdf": "FORMATO_SALIDA.pdf",
    "json_prompt_pdf": "PROMPT_JSON.pdf"
}

# Verificar que existan los PDFs de configuración
config_ok = all(Path(f).exists() for f in CONFIG_PDFS.values())

if not config_ok:
    st.error("❌ Faltan archivos de configuración en el proyecto. Contacta al administrador.")
    st.stop()

# Contenido principal
st.header("📄 Sube tu documento de observación")

uploaded_file = st.file_uploader(
    "PDF con la observación de aula",
    type=['pdf'],
    help="Sube el PDF que contiene la observación de tu clase"
)

# Botón de análisis
analizar = st.button(
    "🔍 Analizar",
    type="primary",
    disabled=(uploaded_file is None or modelo_seleccionado is None),
    use_container_width=True
)

if analizar:
    # Guardar PDF temporalmente
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Guardar archivo subido
        input_path = os.path.join(tmp_dir, "observacion.pdf")
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Rutas de salida
        output_pdf = os.path.join(tmp_dir, "analisis.pdf")
        output_json = os.path.join(tmp_dir, "datos.json")
        
        # Barra de progreso
        progress = st.progress(0, text="Iniciando análisis...")
        
        try:
            # Importar módulos del proyecto
            from src.core.config import Config
            from src.core.generador_texto_ollama import (
                extraer_texto_pdf,
                generar_texto_estructurado,
                generar_json_desde_informe,
                guardar_resultado_en_pdf,
                generar_datos_temporales
            )
            
            # Crear configuración
            config_data = {
                "input_pdf": input_path,
                "prompt_pdf": CONFIG_PDFS["prompt_pdf"],
                "structure_pdf": CONFIG_PDFS["structure_pdf"],
                "json_prompt_pdf": CONFIG_PDFS["json_prompt_pdf"],
                "output_pdf": output_pdf,
                "output_json": output_json,
                "ollama_model": modelo_seleccionado,
                "ollama_options": {
                    "temperature": temperatura,
                    "top_p": 0.8,
                    "num_ctx": 8192
                }
            }
            
            config = Config(config_data)
            
            # Paso 1: Extraer texto
            progress.progress(10, text="Leyendo tu documento...")
            info_texto = extraer_texto_pdf(input_path)
            
            if len(info_texto) < 50:
                st.error("❌ El PDF no contiene suficiente texto. Asegúrate de que no sea una imagen escaneada.")
                st.stop()
            
            # Paso 2: Leer configs
            progress.progress(20, text="Preparando análisis...")
            mi_prompt = extraer_texto_pdf(CONFIG_PDFS["prompt_pdf"])
            mis_instrucciones = extraer_texto_pdf(CONFIG_PDFS["structure_pdf"])
            prompt_json = extraer_texto_pdf(CONFIG_PDFS["json_prompt_pdf"])
            
            # Paso 3: Datos temporales
            progress.progress(30, text="Generando métricas temporales...")
            json_temporal = generar_datos_temporales()
            
            # Paso 4: Generar informe
            progress.progress(40, text=f"Analizando con {modelo_seleccionado}... (esto puede tardar 2-5 min)")
            texto_informe = generar_texto_estructurado(
                info_texto, 
                mi_prompt, 
                mis_instrucciones, 
                json_temporal, 
                modelo_seleccionado,
                config.get("ollama_options")
            )
            
            # Paso 5: Guardar PDF
            progress.progress(75, text="Generando PDF del informe...")
            guardar_resultado_en_pdf(texto_informe, output_pdf)
            
            # Paso 6: Generar JSON
            progress.progress(85, text="Extrayendo datos estructurados...")
            respuesta_json = generar_json_desde_informe(
                texto_informe, 
                prompt_json, 
                modelo_seleccionado
            )
            
            # Guardar JSON
            with open(output_json, "w", encoding="utf-8") as f:
                f.write(respuesta_json)
            
            progress.progress(100, text="✅ ¡Análisis completado!")
            
            # Guardar en session_state para persistir
            st.session_state.analisis_completado = True
            st.session_state.texto_informe = texto_informe
            st.session_state.respuesta_json = respuesta_json
            st.session_state.output_pdf = output_pdf
            st.session_state.output_json = output_json
            st.session_state.nombre_archivo = uploaded_file.name
            
        except Exception as e:
            progress.progress(100, text="❌ Error en el análisis")
            st.error(f"Error: {str(e)}")
            st.exception(e)

# Mostrar resultados si existen en session_state
if 'analisis_completado' in st.session_state and st.session_state.analisis_completado:
    st.divider()
    st.header("📊 Resultados del Análisis")
    
    # Nombre del archivo analizado
    st.info(f"📄 Documento analizado: **{st.session_state.nombre_archivo}**")
    
    # Tabs para ver resultados
    tab1, tab2 = st.tabs(["📋 Informe", "📁 Datos JSON"])
    
    with tab1:
        st.text_area(
            "Informe generado",
            st.session_state.texto_informe,
            height=400,
            disabled=True,
            key="informe_display"
        )
    
    with tab2:
        try:
            json_data = json.loads(st.session_state.respuesta_json)
            st.json(json_data)
        except:
            st.code(st.session_state.respuesta_json, language="json")
    
    # Botones de descarga
    st.divider()
    st.header("📥 Descargar resultados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Descargar PDF
        nombre_base = Path(st.session_state.nombre_archivo).stem
        with open(st.session_state.output_pdf, "rb") as f:
            st.download_button(
                label="📄 Descargar Informe PDF",
                data=f.read(),
                file_name=f"analisis_{nombre_base}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    
    with col2:
        # Descargar JSON
        with open(st.session_state.output_json, "rb") as f:
            st.download_button(
                label="📁 Descargar Datos JSON",
                data=f.read(),
                file_name=f"datos_{nombre_base}.json",
                mime="application/json",
                use_container_width=True
            )
    
    # Botón para nuevo análisis
    if st.button("🔄 Analizar otro documento", use_container_width=True):
        st.session_state.analisis_completado = False
        st.rerun()

# Footer
st.divider()
st.markdown("""
<small>Análisis Pedagógico v1.0 | Powered by Ollama</small>
""", unsafe_allow_html=True)
