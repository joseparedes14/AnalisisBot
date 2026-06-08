"""
Punto de entrada principal para el generador de informes pedagógicos.

Uso:
    python main.py                    # Ejecutar con configuración por defecto
    python main.py --help            # Ver todas las opciones disponibles
    python main.py -i entrada.pdf     # Especificar archivo de entrada
"""

import sys
from src.main import main

if __name__ == "__main__":
    sys.exit(main())