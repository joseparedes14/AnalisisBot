<div align="center">

# 📚 Análisis Pedagógico con Ollama

**Generador de informes pedagógicos estructurados usando modelos de lenguaje locales**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-0.4%2B-000?style=flat&logo=ollama&logoColor=white)](https://ollama.ai)
[![Pydantic](https://img.shields.io/badge/Pydantic-2.0%2B-E92063?style=flat&logo=pydantic&logoColor=white)](https://pydantic.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)](LICENSE)

</div>

---

## Descripción

Herramienta profesional para el análisis pedagógico de aulas que procesa documentos PDF de observación y genera informes estructurados y profundos utilizando modelos de lenguaje locales ejecutados con **Ollama**.

### Características principales

- **Análisis automático** de documentos PDF de observación de aula
- **Informes narrativos** con análisis crítico y recomendaciones estratégicas
- **Datos estructurados en JSON** para procesamiento posterior e integración con sistemas externos
- **Métricas temporales simuladas** que modelan el comportamiento real del aula durante 61 minutos
- **Procesamiento paralelo** para generación eficiente de informes
- **Sistema de logging** completo para auditoría y debugging
- **Validación de datos** con Pydantic para garantizar integridad

---

## Flux de Trabajo

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PDFs de       │    │   Extracción    │    │   Generación    │    │   Resultados    │
│   Entrada       │───►│   con PyMuPDF   │───►│   con Ollama    │───►│   PDF + JSON    │
│                 │    │                 │    │                 │    │                 │
│ • Contexto      │    │ • Texto extraído│    │ • Informe       │    │ • Informe       │
│ • Prompt        │    │ • Validación    │    │ • JSON          │    │ • Datos         │
│ • Estructura    │    │                 │    │                 │    │                 │
│ • Prompt JSON   │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                               │                       │
                               ▼                       ▼
                        ┌─────────────────┐    ┌─────────────────┐
                        │   Datos         │    │   Validación    │
                        │   Temporales    │    │   de Esquemas   │
                        │   Simulados     │    │   con Pydantic  │
                        │   (61 min)      │    │                 │
                        └─────────────────┘    └─────────────────┘
```

---

## Requisitos

| Componente | Versión mínima | Descripción |
|------------|----------------|-------------|
| **Python** | 3.10+ | Lenguaje de programación |
| **Ollama** | 0.4+ | Runtime para modelos de lenguaje locales |
| **Modelo LLM** | Recomendado: `llama3.2:latest` | Modelo de lenguaje para generación |

### Modelos recomendados

| Modelo | Tamaño | Velocidad | Calidad |
|--------|--------|-----------|---------|
| `llama3.2:latest` | 2GB | Rápida | ✅ Buena |
| `llama3:latest` | 4.7GB | Media | ✅ Muy buena |
| `gemma3:1b` | 815MB | Muy rápida | ⚠️ Básica |

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/maria-celdrannoguera/chatbot_classroom_speech_analysis.git
cd chatbot_classroom_speech_analysis
```

### 2. Crear entorno virtual (recomendado)

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
# Usando pyproject.toml (recomendado)
pip install -e .

# O con requirements.txt
pip install -r requirements.txt
```

### 4. Instalar y configurar Ollama

```bash
# Instalar Ollama (macOS)
brew install ollama

# Iniciar servicio
ollama serve

# Descargar modelo recomendado
ollama pull llama3.2:latest
```

### 5. Verificar instalación

```bash
# Verificar que Ollama está funcionando
ollama list

# Verificar dependencias de Python
python -c "import ollama, fitz, pydantic; print('✅ Todas las dependencias OK')"
```

---

## Uso

### Ejecución básica

```bash
python main.py
```

Esto ejecutará el pipeline completo usando la configuración por defecto:
- Lee los PDFs de la carpeta actual
- Genera el informe con `llama3.2:latest`
- Guarda el resultado en `Respuesta_Agente_Ollama.pdf` y `data_auditoria.json`

### Con argumentos de línea de comandos

```bash
python main.py \
    --input PruebaInforme.pdf \
    --prompt PROMPTMEJORADO.pdf \
    --structure FORMATO_SALIDA.pdf \
    --json-prompt PROMPT_JSON.pdf \
    --output-pdf mi_informe.pdf \
    --output-json mis_datos.json \
    --model llama3.2:latest \
    --temperature 0.1 \
    --top-p 0.8 \
    --log-level DEBUG
```

### Con archivo de configuración

```bash
# 1. Copiar el ejemplo
cp config/config.example.json config/config.json

# 2. Editar con tus valores
nano config/config.json

# 3. Ejecutar
python main.py --config config/config.json
```

### Variables de entorno

```bash
# macOS / Linux
export GENERADOR_INPUT_PDF=PruebaInforme.pdf
export GENERADOR_OLLAMA_MODEL=llama3.2:latest
export GENERADOR_OLLAMA_OPTIONS='{"temperature": 0.2, "top_p": 0.9}'
python main.py

# Windows
set GENERADOR_INPUT_PDF=PruebaInforme.pdf
set GENERADOR_OLLAMA_MODEL=llama3.2:latest
python main.py
```

---

## Archivos de Entrada Requeridos

El sistema requiere **4 archivos PDF** de entrada:

| Archivo | Propósito | Ejemplo |
|---------|-----------|---------|
| `input_pdf` | Información/contexto de la observación | `PruebaInforme.pdf` |
| `prompt_pdf` | Instrucciones para el análisis | `PROMPTMEJORADO.pdf` |
| `structure_pdf` | Estructura del informe de salida | `FORMATO_SALIDA.pdf` |
| `json_prompt_pdf` | Prompt para extracción de datos JSON | `PROMPT_JSON.pdf` |

> ⚠️ **Importante**: Los PDFs deben contener texto seleccionable. Los PDFs escaneados (imágenes) no funcionarán correctamente.

---

## Estructura del Proyecto

```
chatbot_classroom_speech_analysis/
│
├── main.py                          # Punto de entrada principal
├── src/
│   ├── __init__.py
│   ├── main.py                      # Orquestador del pipeline
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                # Configuración multi-fuente (CLI/env/file)
│   │   ├── errors.py                # Excepciones personalizadas y logging
│   │   ├── generador_texto_ollama.py # Pipeline principal de generación
│   │   └── validators.py            # Validación de datos con Pydantic
│   └── utils/
│       ├── __init__.py
│       └── simulador.py             # Generación de datos temporales simulados
│
├── config/
│   └── config.example.json          # Ejemplo de configuración
│
├── tests/
│   ├── __init__.py
│   ├── test_config.py               # Tests de configuración (12 tests)
│   ├── test_simulador.py            # Tests del simulador (9 tests)
│   └── test_validators.py           # Tests de validación (14 tests)
│
├── docs/                            # Documentación adicional
├── requirements.txt                 # Dependencias (legacy)
├── pyproject.toml                   # Configuración moderna de proyecto
├── .gitignore                       # Archivos excluidos de git
└── README.md                        # Este archivo
```

---

## Métricas Temporales Simuladas

El sistema genera datos simulados que modelan el comportamiento real del aula durante una sesión de 61 minutos:

| Métrica | Nombre completo | Rango | Descripción |
|---------|-----------------|-------|-------------|
| **PSR** | Puntuación de Ritmo de la Sesión | 1.0 - 5.0 | Ritmo general de la clase |
| **APSUD** | Atención Promedio de los Estudiantes | 0% - 100% | Nivel de atención del alumnado |
| **PSU** | Participación del Estudiante | 0% - 100% | Frecuencia de intervenciones |
| **PSUR** | Participación Significativa del Estudiante | 0% - 100% | Calidad de las intervenciones |
| **MR** | Movimiento Relativo | 0% - 100% | Nivel de actividad física |

### Fases modeladas

```
Minuto 0-5    │ INICIO     │ Atención baja (40-55%), movimiento alto (50-80%)
Minuto 5-25   │ DESARROLLO │ Atención alta (80-95%), movimiento bajo (15-35%)
Minuto 25-35  │ VALLE      │ Bajón de atención (50-70%), movimiento medio (40-60%)
Minuto 35-55  │ DESARROLLO │ Atención alta (80-95%), movimiento bajo (15-35%)
Minuto 55-60  │ CIERRE     │ Fatiga (30-45%), movimiento alto (60-85%)
```

---

## Configuración

### Parámetros de Ollama

| Parámetro | Tipo | Rango | Descripción |
|-----------|------|-------|-------------|
| `temperature` | float | 0.0 - 1.0 | Aleatoriedad en la generación (menor = más determinista) |
| `top_p` | float | 0.0 - 1.0 | Núcleo de muestreo (menor = más conservador) |
| `num_ctx` | int | 1024 - 32768 | Tamaño del contexto máximo |
| `repeat_penalty` | float | 0.0+ | Penalización por repetición |

### Configuración por defecto

```json
{
  "ollama_model": "llama3.2:latest",
  "ollama_options": {
    "temperature": 0.1,
    "top_p": 0.8,
    "num_ctx": 8192,
    "repeat_penalty": 1.1
  }
}
```

---

## Testing

### Ejecutar todos los tests

```bash
pytest tests/ -v
```

### Ejecutar tests específicos

```bash
# Tests de configuración
pytest tests/test_config.py -v

# Tests del simulador
pytest tests/test_simulador.py -v

# Tests de validación
pytest tests/test_validators.py -v

# Con cobertura
pytest tests/ --cov=src --cov-report=html
```

### Tests disponibles

| Archivo | Tests | Cobertura |
|---------|-------|-----------|
| `test_config.py` | 12 | Configuración multi-fuente |
| `test_simulador.py` | 9 | Generación de datos temporales |
| `test_validators.py` | 14 | Validación Pydantic |
| **Total** | **35** | Core del sistema |

---

## Manejo de Errores

### Excepciones personalizadas

| Excepción | Descripción | Solución |
|-----------|-------------|----------|
| `PDFExtractionError` | Error al extraer texto de PDF | Verificar que el PDF tiene texto seleccionable |
| `OllamaGenerationError` | Error al generar con Ollama | Verificar que Ollama está corriendo y el modelo existe |
| `PDFGenerationError` | Error al generar PDF de salida | Verificar permisos de escritura en la carpeta |
| `JSONGenerationError` | Error al generar JSON | Revisar el log para más detalles |
| `DataValidationError` | Error de validación de datos | Verificar formato de datos de entrada |
| `ConfigurationError` | Error en configuración | Revisar archivo de configuración o variables de entorno |

### Sistema de logs

Los logs se guardan en `generador.log` con el siguiente formato:

```
2026-06-08 21:00:57 - main - INFO - Iniciando generación de informe
2026-06-08 21:00:57 - src.core.generador_texto_ollama - INFO - Modelo 'llama3.2:latest' encontrado
```

Niveles disponibles: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

---

## Rendimiento

### Tiempos estimados (con `llama3.2:latest` en CPU)

| Fase | Tiempo aproximado |
|------|-------------------|
| Extracción de PDFs | < 1 segundo |
| Generación de datos temporales | < 1 segundo |
| Generación de informe | 2-5 minutos |
| Generación de JSON | 30-60 segundos |
| **Total** | **3-6 minutos** |

### Optimizaciones

- **Procesamiento paralelo**: PDF y JSON se generan en threads separados
- **Validación temprana**: Los PDFs se verifican antes de procesar
- **Timeouts configurables**: Se puede limitar el tiempo de generación

---

## Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Haz commit de tus cambios (`git commit -m 'Add nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-ffuncionalidad`)
5. Abre un Pull Request

### Convenciones de commits

```
feat: añadir nueva funcionalidad
fix: corregir bug en...
docs: actualizar documentación
test: añadir tests para...
refactor: refactorizar código...
```

---

## Changelog

### v1.0.0 (2026-06-08)

- ✅ Pipeline completo de generación de informes
- ✅ Soporte para múltiples modelos Ollama
- ✅ Configuración multi-fuente (CLI, env, file)
- ✅ Validación de datos con Pydantic
- ✅ 35 tests unitarios
- ✅ Sistema de logging completo
- ✅ Manejo robusto de excepciones

---

## Licencia

MIT License - ver [LICENSE](LICENSE) para más detalles.

---

## Contacto

**María Celdrán Noguera**
- GitHub: [@maria-celdrannoguera](https://github.com/maria-celdrannoguera)

**José Paredes Salcedo**
- GitHub: [@joseparedes14](https://github.com/joseparedes14)

---

<div align="center">

**¿Necesitas ayuda?** [Abre un issue](https://github.com/maria-celdrannoguera/chatbot_classroom_speech_analysis/issues)

</div>
