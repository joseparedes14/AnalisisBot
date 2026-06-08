<div align="center">

# Análisis Pedagógico con Ollama

**Generador de informes pedagógicos estructurados usando modelos de lenguaje locales (Ollama)**

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-0.3%2B-000?style=flat&logo=ollama&logoColor=white)](https://ollama.ai)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)

</div>

---

## Descripción

Herramienta que analiza información extraída de documentos PDF de observación de aula y genera informes pedagógicos profundos y estructurados. Utiliza modelos de lenguaje locales ejecutados con **Ollama** para procesar los datos y producir:

- Informes narrativos detallados con análisis crítico
- Datos estructurados en JSON para procesamiento posterior
- Simulación de métricas temporales de aula (atención, participación, movimiento)
- Bloqueo temporal asimétrico basado en tendencias reales

## Flujo de trabajo

```
PDFs de entrada  ──►  Extracción con PyMuPDF  ──►  Ollama (LLM local)  ──►  Informe PDF + JSON
                        ┌───────────────────┐
                        │ Datos temporales  │
                        │ simulados (61 min)│
                        └───────────────────┘
```

## Requisitos

- **Python** 3.8+
- **Ollama** en ejecución con un modelo descargado ([guía de instalación](https://ollama.ai/download))
- Dependencias Python (ver `requirements.txt`)

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/joseparedes14/AnalisisBot.git
cd AnalisisBot

# Crear entorno virtual (opcional pero recomendado)
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Asegurarse de que Ollama esté ejecutándose
ollama pull llama3.2:latest  # o el modelo que prefieras
```

## Uso

### Ejecución básica

```bash
python main.py
```

### Con argumentos de línea de comandos

```bash
python main.py \
    --input PruebaInforme.pdf \
    --prompt PROMPTMEJORADO.pdf \
    --structure FORMATO_SALIDA.pdf \
    --json-prompt PROMPT_JSON.pdf \
    --output-pdf Respuesta_Agente_Ollama.pdf \
    --output-json data_auditoria.json \
    --model llama3.2:latest
```

### Archivo de configuración

```bash
# Copiar el ejemplo y editarlo
cp config\config.example.json config\config.json
# Ejecutar con config
python main.py --config config\config.json
```

### Variables de entorno

```bash
set GENERADOR_INPUT_PDF=PruebaInforme.pdf
set GENERADOR_OLLAMA_MODEL=llama3.2:latest
set GENERADOR_OLLAMA_OPTIONS={"temperature": 0.2, "top_p": 0.9}
python main.py
```

## Estructura del proyecto

```
AnalisisBot/
│
├── main.py                      # Punto de entrada
├── src/
│   ├── main.py                  # Orquestador del pipeline
│   ├── core/
│   │   ├── config.py            # Configuración multi-fuente
│   │   ├── errors.py            # Excepciones y logging
│   │   ├── generador_texto_ollama.py  # Pipeline de generación
│   │   └── validators.py        # Validación con Pydantic
│   └── utils/
│       └── simulador.py         # Datos temporales simulados
│
├── config/
│   └── config.example.json      # Ejemplo de configuración
├── tests/
│   └── __init__.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Métricas temporales simuladas

| Métrica | Descripción | Rango |
|---------|-------------|-------|
| **PSR** | Puntuación de Ritmo de la Sesión | 1.0 - 5.0 |
| **APSUD** | Atención Promedio de los Estudiantes | 0% - 100% |
| **PSU** | Participación del Estudiante | 0% - 100% |
| **PSUR** | Participación Significativa del Estudiante | 0% - 100% |
| **MR** | Movimiento Relativo | 0% - 100% |

El simulador modela 3 fases típicas de una clase:
- **Inicio (min 0-5)**: atención baja, movimiento alto
- **Valle medio (min 25-35)**: posible bajón de atención
- **Cierre (min 55-60)**: fatiga y pérdida de interés

## Personalización

- **Modelo LLM**: cambia con `--model` o `GENERADOR_OLLAMA_MODEL`
- **Estructura del informe**: modifica el PDF de `--structure`
- **Parámetros de generación**: temperatura, top_p, num_ctx, repeat_penalty
- **Datos temporales**: ajusta los rangos en `src/utils/simulador.py`
- **Logging**: niveles DEBUG a CRITICAL, salida a archivo y consola

## Manejo de errores

| Excepción | Descripción |
|-----------|-------------|
| `PDFExtractionError` | Error al extraer texto de PDF |
| `OllamaGenerationError` | Error al generar texto con Ollama |
| `PDFGenerationError` | Error al generar PDF de salida |
| `JSONGenerationError` | Error al generar o guardar JSON |
| `DataValidationError` | Error de validación de datos |
| `ConfigurationError` | Error en la configuración |

## Notas importantes

- **Ollama debe estar en ejecución**: `ollama serve`
- **Modelo requerido**: las descargas se hacen con `ollama pull <modelo>`
- **PDFs escaneados**: si el PDF es imagen escaneada, PyMuPDF no extraerá texto
- **Sistema de logs**: toda la ejecución queda registrada en `generador.log`

## Licencia

MIT
