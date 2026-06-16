"""
Interfaz web para el Analisis Pedagogico con Ollama.
Proporciona una experiencia visual para cargar transcripciones,
visualizar metricas y generar informes.
"""

import streamlit as st
import json
import os
import re
import tempfile
import shutil
from datetime import datetime
from typing import Optional

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.core.input_processor import procesar_json_transcripcion
from src.core.generador_texto_ollama import (
    generar_texto_estructurado,
    extraer_texto_pdf,
    verificar_ollama,
    guardar_resultado_en_pdf,
    generar_json_desde_informe,
    listar_modelos_ollama,
)

st.set_page_config(
    page_title="Analisis Pedagogico con Ollama",
    page_icon=":libro:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .metric-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #555;
    }
    .report-container {
        background: #fafafa;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1.5rem;
        max-height: 600px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-family: 'Georgia', serif;
        line-height: 1.6;
    }
    .stButton > button {
        width: 100%;
    }
    .output-banner {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
    }
    .output-banner .path {
        font-family: monospace;
        font-size: 0.9rem;
        word-break: break-all;
    }
    .overlay {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(255,255,255,0.85);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
    }
</style>
""", unsafe_allow_html=True)

st.title("Analisis Pedagogico con Ollama")
st.markdown("Generador de informes pedagogicos a partir de transcripciones de aula usando modelos de lenguaje locales.")

# ─── Session State ──────────────────────────────────────────────
if "metrics" not in st.session_state:
    st.session_state.metrics = None
if "metadata" not in st.session_state:
    st.session_state.metadata = None
if "timeline" not in st.session_state:
    st.session_state.timeline = None
if "report" not in st.session_state:
    st.session_state.report = None
if "report_json" not in st.session_state:
    st.session_state.report_json = None
if "teacher" not in st.session_state:
    st.session_state.teacher = None
if "temp_dir" not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()
if "analysis_running" not in st.session_state:
    st.session_state.analysis_running = False
if "output_dir" not in st.session_state:
    st.session_state.output_dir = os.path.join(os.getcwd(), "output")
if "last_output_path" not in st.session_state:
    st.session_state.last_output_path = None
if "analysis_ok" not in st.session_state:
    st.session_state.analysis_ok = False


def _clean_filename(name: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r'[^\w\.\-]', '_', name)
    return name


def save_uploaded_file(uploaded_file) -> Optional[str]:
    if uploaded_file is None:
        return None
    safe_name = _clean_filename(uploaded_file.name)
    path = os.path.join(st.session_state.temp_dir, safe_name)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path


def cleanup_temp():
    if st.session_state.temp_dir and os.path.exists(st.session_state.temp_dir):
        shutil.rmtree(st.session_state.temp_dir, ignore_errors=True)
    st.session_state.temp_dir = tempfile.mkdtemp()


# ─── Sidebar ────────────────────────────────────────────────────
busy = st.session_state.analysis_running

with st.sidebar:
    st.header("Entrada de Datos")

    uploaded_json = st.file_uploader(
        "Transcripcion JSON (Whisper)",
        type=["json"],
        help="Archivo JSON generado por Whisper con la transcripcion de la clase",
        disabled=busy,
    )

    st.divider()
    st.subheader("PDFs de Configuracion")
    uploaded_prompt = st.file_uploader("Prompt de analisis", type=["pdf"], key="prompt", disabled=busy)
    uploaded_structure = st.file_uploader("Estructura del informe", type=["pdf"], key="structure", disabled=busy)
    uploaded_json_prompt = st.file_uploader("Prompt para JSON", type=["pdf"], key="json_prompt", disabled=busy)

    st.divider()
    st.subheader("Ollama")

    modelos_disponibles = listar_modelos_ollama()
    if modelos_disponibles:
        default_model = "llama3.2:latest"
        model_index = 0
        if default_model in modelos_disponibles:
            model_index = modelos_disponibles.index(default_model)
        elif "llama3.1:latest" in modelos_disponibles:
            model_index = modelos_disponibles.index("llama3.1:latest")
        ollama_model = st.selectbox(
            "Modelo", modelos_disponibles, index=model_index, disabled=busy,
        )
    else:
        ollama_model = st.text_input("Modelo", value="llama3.2:latest", disabled=busy,
                                     help="Ollama no disponible, escribe el nombre manualmente")

    col1, col2 = st.columns(2)
    with col1:
        temperature = st.slider("Temperatura", 0.0, 1.0, 0.1, 0.05, disabled=busy)
    with col2:
        top_p = st.slider("Top-p", 0.0, 1.0, 0.8, 0.05, disabled=busy)
    col3, col4 = st.columns(2)
    with col3:
        num_ctx = st.selectbox("Contexto", [4096, 8192, 16384, 32768], index=1, disabled=busy)
    with col4:
        repeat_penalty = st.slider("Repeat Penalty", 0.0, 2.0, 1.1, 0.05, disabled=busy)

    st.divider()
    st.subheader("Docente")
    teacher_option = st.selectbox("Identificacion del docente", ["auto", "manual"], disabled=busy)
    teacher_speaker = "auto"
    if teacher_option == "manual":
        teacher_speaker = st.text_input("Speaker del docente (ej. SPEAKER_00)", value="SPEAKER_00", disabled=busy)

    st.divider()
    st.subheader("Salida")
    prev_output_dir = st.session_state.output_dir
    new_dir = st.text_input("Directorio de salida", value=prev_output_dir, disabled=busy)
    if new_dir != prev_output_dir:
        st.session_state.output_dir = new_dir

    if st.session_state.last_output_path:
        st.markdown(
            f'<div class="output-banner">'
            f'<strong>Ultimo informe guardado en:</strong><br>'
            f'<span class="path">{st.session_state.last_output_path}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    run_button = st.button(
        "Ejecutar Analisis Completo", type="primary", width="stretch", disabled=busy,
    )

    if st.button("Limpiar datos temporales", width="stretch", disabled=busy):
        for key in ["metrics", "metadata", "timeline", "report", "report_json", "teacher"]:
            st.session_state[key] = None
        st.session_state.last_output_path = None
        st.session_state.analysis_ok = False
        cleanup_temp()
        st.rerun()


# ─── Overlay during analysis ────────────────────────────────────
overlay_placeholder = st.empty()

if busy:
    with overlay_placeholder:
        st.markdown(
            '<div class="overlay">'
            '<h2>Analisis en curso...</h2>'
            '<p>No interactues con la pagina hasta que termine.</p>'
            '</div>',
            unsafe_allow_html=True,
        )


# ─── Run ────────────────────────────────────────────────────────
def run_analysis():
    if st.session_state.analysis_running:
        return

    if not uploaded_json:
        st.error("Debes subir un archivo JSON de transcripcion.")
        return

    st.session_state.analysis_running = True
    st.session_state.analysis_ok = False

    try:
        with st.spinner("Procesando transcripcion y calculando metricas..."):
            json_path = save_uploaded_file(uploaded_json)
            try:
                teacher = teacher_speaker if teacher_option == "manual" else "auto"
                datos = procesar_json_transcripcion(json_path, teacher_speaker=teacher)
                st.session_state.metrics = datos["metricas"]
                st.session_state.metadata = datos["metadata"]
                st.session_state.timeline = datos["timeline"]
                st.session_state.teacher = datos["teacher_speaker"]
                st.success(f"Metricas calculadas. Docente detectado: {datos['teacher_speaker']}")
            except (FileNotFoundError, ValueError) as e:
                st.error(f"Error al procesar JSON: {e}")
                return

        if not (uploaded_prompt and uploaded_structure and uploaded_json_prompt):
            st.warning("Faltan PDFs de configuracion. No se generara el informe con LLM.")
            return

        with st.spinner("Extrayendo texto de PDFs..."):
            try:
                prompt_path = save_uploaded_file(uploaded_prompt)
                structure_path = save_uploaded_file(uploaded_structure)
                json_prompt_path = save_uploaded_file(uploaded_json_prompt)

                prompt_text = extraer_texto_pdf(prompt_path)
                structure_text = extraer_texto_pdf(structure_path)
                json_extractor_text = extraer_texto_pdf(json_prompt_path)
                st.success("PDFs procesados correctamente.")
            except (FileNotFoundError, RuntimeError) as e:
                st.error(f"Error al extraer PDFs: {e}")
                return

        if not verificar_ollama(ollama_model):
            st.error(
                f"Modelo '{ollama_model}' no encontrado. "
                f"Modelos disponibles: {modelos_disponibles if modelos_disponibles else 'Ninguno'}. "
                f"Asegurate de que Ollama este corriendo y el modelo este instalado."
            )
            return

        with st.spinner("Generando informe con IA (esto puede tomar varios minutos)..."):
            try:
                contexto = {
                    "metricas": st.session_state.metrics,
                    "metadata": st.session_state.metadata,
                    "timeline": st.session_state.timeline,
                }
                contexto_json = json.dumps(contexto, indent=2, ensure_ascii=False)
                opts = {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_ctx": num_ctx,
                    "repeat_penalty": repeat_penalty,
                }

                report_text = generar_texto_estructurado(
                    contexto_json,
                    prompt_text,
                    structure_text,
                    None,
                    ollama_model,
                    opts,
                )
                st.session_state.report = report_text
                st.success("Informe generado correctamente.")
            except (RuntimeError, ConnectionError) as e:
                st.error(f"Error al generar informe: {e}")
                return

        with st.spinner("Generando JSON estructurado..."):
            try:
                json_result = generar_json_desde_informe(report_text, json_extractor_text, ollama_model)
                parsed_json = json.loads(json_result) if isinstance(json_result, str) else json_result
                datos_salida = {
                    "metadata": st.session_state.metadata,
                    "metricas": st.session_state.metrics,
                    "timeline": st.session_state.timeline,
                    "analisis_llm": parsed_json,
                }
                st.session_state.report_json = json.dumps(datos_salida, indent=2, ensure_ascii=False)
                st.success("JSON generado correctamente.")
            except (json.JSONDecodeError, RuntimeError) as e:
                st.warning(f"Error al generar JSON: {e}")

        os.makedirs(st.session_state.output_dir, exist_ok=True)
        pdf_path = os.path.join(
            st.session_state.output_dir,
            f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        )
        try:
            guardar_resultado_en_pdf(report_text, pdf_path)
            st.session_state.last_output_path = pdf_path
            st.session_state.analysis_ok = True
            st.success(f"PDF guardado en: {pdf_path}")
        except (IOError, OSError, RuntimeError) as e:
            st.warning(f"No se pudo guardar PDF automaticamente: {e}")

    finally:
        st.session_state.analysis_running = False
        st.rerun()


if run_button and not busy:
    run_analysis()

# ─── Main area (tabs) ───────────────────────────────────────────
tab_metrics, tab_report, tab_data, tab_config = st.tabs(
    ["Metricas", "Informe Generado", "Datos Crudos", "Configuracion"]
)

# ─── Tab: Metricas ──────────────────────────────────────────────
with tab_metrics:
    if st.session_state.metrics is None:
        st.info("Sube un archivo JSON de transcripcion y ejecuta el analisis para ver las metricas.")
    else:
        m = st.session_state.metrics
        meta = st.session_state.metadata

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Duracion", f"{meta['duracion_total_minutos']:.0f} min",
                    f"{meta['total_intervenciones']} intervenciones")
        col2.metric("Estudiantes", str(meta["numero_estudiantes"]))
        col3.metric("Docente", st.session_state.teacher)
        col4.metric("TTC (Cambios de turno)", str(m["TTC"]))

        st.divider()
        st.subheader("Visualizacion de Metricas")

        col_left, col_right = st.columns(2)

        with col_left:
            psr = m["PSR"]
            fig_psr = go.Figure(go.Indicator(
                mode="gauge+number",
                value=psr * 100,
                number={"suffix": "%", "font": {"size": 36}},
                title={"text": "PSR - Ratio de habla del docente"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#1f77b4"},
                    "steps": [
                        {"range": [0, 40], "color": "#d4f5d4", "name": "Participativo"},
                        {"range": [40, 70], "color": "#fff3cd", "name": "Equilibrado"},
                        {"range": [70, 100], "color": "#f8d7da", "name": "Docente domina"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": psr * 100,
                    },
                },
            ))
            fig_psr.update_layout(height=280, margin=dict(l=30, r=30, t=40, b=10))
            st.plotly_chart(fig_psr, width="stretch")

        with col_right:
            sr_teacher = m["SR"]["teacher"] * 100
            sr_students = m["SR"]["students"] * 100
            fig_sr = go.Figure()
            fig_sr.add_trace(go.Bar(
                x=["Docente", "Estudiantes"],
                y=[sr_teacher, sr_students],
                marker_color=["#1f77b4", "#ff7f0e"],
                text=[f"{sr_teacher:.1f}%", f"{sr_students:.1f}%"],
                textposition="outside",
            ))
            fig_sr.update_layout(
                title="SR - Speaking Ratio",
                yaxis_title="% del tiempo total",
                yaxis_range=[0, 100],
                height=280,
                margin=dict(l=30, r=30, t=40, b=10),
            )
            st.plotly_chart(fig_sr, width="stretch")

        col_left, col_right = st.columns(2)

        with col_left:
            apsud_data = pd.DataFrame({
                "Rol": ["Docente", "Estudiantes", "Total"],
                "Duracion (s)": [m["APSUD"]["teacher"], m["APSUD"]["students"], m["APSUD"]["total"]],
            })
            fig_apsud = px.bar(
                apsud_data, x="Rol", y="Duracion (s)",
                color="Rol", text_auto=".2f",
                color_discrete_map={"Docente": "#1f77b4", "Estudiantes": "#ff7f0e", "Total": "#2ca02c"},
            )
            fig_apsud.update_layout(
                title="APSUD - Duracion promedio de intervenciones",
                height=280, margin=dict(l=30, r=30, t=40, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig_apsud, width="stretch")

        with col_right:
            vsur_data = pd.DataFrame({
                "Rol": ["Docente", "Estudiantes"],
                "VSUR": [m["VSUR"]["teacher"] * 100, m["VSUR"]["students"] * 100],
            })
            fig_vsur = px.bar(
                vsur_data, x="Rol", y="VSUR",
                color="Rol", text_auto=".1f",
                color_discrete_map={"Docente": "#1f77b4", "Estudiantes": "#ff7f0e"},
            )
            fig_vsur.update_layout(
                title="VSUR - % Intervenciones muy cortas (<2s)",
                yaxis_title="%", yaxis_range=[0, 100],
                height=280, margin=dict(l=30, r=30, t=40, b=10),
                showlegend=False,
            )
            st.plotly_chart(fig_vsur, width="stretch")

        col_left, col_right = st.columns(2)

        with col_left:
            psur_data = pd.DataFrame({
                "Rol": ["Docente", "Estudiantes"],
                "PSUR": [m["PSUR"]["teacher"] * 100, m["PSUR"]["students"] * 100],
            })
            fig_psur = px.pie(
                psur_data, values="PSUR", names="Rol",
                color="Rol", hole=0.4,
                color_discrete_map={"Docente": "#1f77b4", "Estudiantes": "#ff7f0e"},
            )
            fig_psur.update_layout(
                title="PSUR - Distribucion de turnos de habla",
                height=280, margin=dict(l=30, r=30, t=40, b=10),
            )
            st.plotly_chart(fig_psur, width="stretch")

        with col_right:
            fig_extra = go.Figure()
            fig_extra.add_trace(go.Indicator(
                mode="number",
                value=m["ALD"],
                number={"suffix": " s", "font": {"size": 40}},
                title={"text": "ALD - Pausa promedio"},
            ))
            fig_extra.add_trace(go.Indicator(
                mode="number",
                value=m["MR"] * 100,
                number={"suffix": "%", "font": {"size": 40}},
                title={"text": "MR - Ratio de murmullo"},
                domain={"y": [0, 0.45]},
            ))
            fig_extra.add_trace(go.Indicator(
                mode="number",
                value=m["distinct_students"],
                number={"font": {"size": 40}},
                title={"text": "Estudiantes que participaron"},
                domain={"y": [0.55, 1]},
            ))
            fig_extra.update_layout(height=280, margin=dict(l=30, r=30, t=40, b=10))
            st.plotly_chart(fig_extra, width="stretch")

        if st.session_state.timeline:
            st.divider()
            st.subheader("Timeline por Bloques")
            df_timeline = pd.DataFrame(st.session_state.timeline)
            fig_timeline = px.line(
                df_timeline, x="bloque", y="psr",
                markers=True, text="psr",
                labels={"bloque": "Bloque", "psr": "PSR (docente)"},
                title="Evolucion del PSR durante la sesion",
            )
            fig_timeline.update_traces(textposition="top center")
            fig_timeline.update_layout(height=300, margin=dict(l=30, r=30, t=40, b=10))
            st.plotly_chart(fig_timeline, width="stretch")

# ─── Tab: Informe ───────────────────────────────────────────────
with tab_report:
    if st.session_state.report is None:
        st.info("Ejecuta el analisis completo para ver el informe generado.")
    else:
        st.subheader("Informe Pedagogico")
        st.markdown(f'<div class="report-container">{st.session_state.report}</div>', unsafe_allow_html=True)

        st.divider()
        col1, col2, col3 = st.columns(3)

        with col1:
            output_pdf_path = os.path.join(st.session_state.temp_dir, "informe_pedagogico.pdf")
            try:
                guardar_resultado_en_pdf(st.session_state.report, output_pdf_path)
                with open(output_pdf_path, "rb") as f:
                    st.download_button(
                        "Descargar PDF",
                        data=f,
                        file_name=f"informe_pedagogico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        width="stretch",
                    )
            except (IOError, OSError, RuntimeError) as e:
                st.warning(f"No se pudo generar el PDF: {e}")

        with col2:
            if st.session_state.report_json:
                st.download_button(
                    "Descargar JSON",
                    data=st.session_state.report_json,
                    file_name=f"analisis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    width="stretch",
                )

        with col3:
            if st.session_state.last_output_path and os.path.exists(st.session_state.last_output_path):
                with open(st.session_state.last_output_path, "rb") as f:
                    st.download_button(
                        "Descargar PDF (guardado en disco)",
                        data=f,
                        file_name=os.path.basename(st.session_state.last_output_path),
                        mime="application/pdf",
                        width="stretch",
                    )

# ─── Tab: Datos Crudos ──────────────────────────────────────────
with tab_data:
    if st.session_state.metrics is None:
        st.info("Ejecuta el analisis para ver los datos crudos.")
    else:
        st.subheader("Metadatos de la sesion")
        st.json(st.session_state.metadata)

        st.subheader("Metricas calculadas")
        st.json(st.session_state.metrics)

        if st.session_state.timeline:
            st.subheader("Timeline por bloques")
            st.dataframe(pd.DataFrame(st.session_state.timeline), width="stretch", hide_index=True)

        if st.session_state.report_json:
            st.subheader("JSON completo (metricas + analisis LLM)")
            st.json(json.loads(st.session_state.report_json))

# ─── Tab: Configuracion ─────────────────────────────────────────
with tab_config:
    st.subheader("Configuracion actual")

    config_data = {
        "JSON de transcripcion": uploaded_json.name if uploaded_json else "No subido",
        "PDF Prompt": uploaded_prompt.name if uploaded_prompt else "No subido",
        "PDF Estructura": uploaded_structure.name if uploaded_structure else "No subido",
        "PDF JSON Prompt": uploaded_json_prompt.name if uploaded_json_prompt else "No subido",
        "Modelo Ollama": ollama_model,
        "Temperatura": temperature,
        "Top-p": top_p,
        "Contexto": num_ctx,
        "Repeat Penalty": repeat_penalty,
        "Docente": teacher_speaker if teacher_option == "manual" else "auto-detectado",
        "Directorio salida": st.session_state.output_dir,
        "Ultimo PDF": st.session_state.last_output_path or "Ninguno",
    }
    st.json(config_data)

    st.divider()
    st.subheader("Ayuda")
    st.markdown("""
    - **JSON de transcripcion**: Archivo generado por Whisper con formato estandar (segmentos con speaker, start, end, text)
    - **PDFs de configuracion**: Deben contener texto seleccionable (no escaneados)
    - **Ollama**: Debe estar ejecutandose en segundo plano (`ollama serve`)
    - El analisis completo toma entre 3-6 minutos dependiendo del modelo
    """)

st.divider()
st.caption("(c) 2026 Maria Celdran Noguera, Jose Paredes Salcedo")
