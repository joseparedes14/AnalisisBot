"""
Tests unitarios para el módulo simulador de datos temporales.
"""

import json
from src.utils.simulador import generar_datos_temporales


class TestGenerarDatosTemporales:
    """Tests para la función generar_datos_temporales."""

    def test_retorna_string_json(self):
        resultado = generar_datos_temporales()
        assert isinstance(resultado, str)

    def test_json_valido(self):
        resultado = generar_datos_temporales()
        datos = json.loads(resultado)
        assert isinstance(datos, list)

    def test_tiene_61_registros(self):
        """La clase dura 60 minutos + minuto 0 = 61 registros."""
        resultado = generar_datos_temporales()
        datos = json.loads(resultado)
        assert len(datos) == 61

    def test_campos_requeridos(self):
        resultado = generar_datos_temporales()
        datos = json.loads(resultado)
        
        campos_requeridos = ["Minuto_Clase", "PSR", "APSUD", "PSU", "PSUR", "MR"]
        
        for registro in datos:
            for campo in campos_requeridos:
                assert campo in registro, f"Falta campo {campo} en registro"

    def test_minutos_en_rango(self):
        resultado = generar_datos_temporales()
        datos = json.loads(resultado)
        
        for registro in datos:
            assert 0 <= registro["Minuto_Clase"] <= 60

    def test_psr_en_rango(self):
        resultado = generar_datos_temporales()
        datos = json.loads(resultado)
        
        for registro in datos:
            assert 1.0 <= registro["PSR"] <= 5.0

    def test_porcentajes_en_rango(self):
        resultado = generar_datos_temporales()
        datos = json.loads(resultado)
        
        for registro in datos:
            assert 0 <= registro["APSUD"] <= 100
            assert 0 <= registro["PSU"] <= 100
            assert 0 <= registro["PSUR"] <= 100
            assert 0 <= registro["MR"] <= 100

    def test_patrones_temporales(self):
        """Verificar que los patrones de atención son lógicos."""
        resultado = generar_datos_temporales()
        datos = json.loads(resultado)
        
        # Inicio (0-5): atención debería ser baja (40-55)
        for i in range(6):
            assert 40 <= datos[i]["APSUD"] <= 55
        
        # Final (55-60): atención debería ser baja (30-45)
        for i in range(55, 61):
            assert 30 <= datos[i]["APSUD"] <= 45

    def test_formato_tabla(self):
        """Verificar que se puede convertir a tabla markdown."""
        from src.core.generador_texto_ollama import generar_tabla_markdown
        
        resultado = generar_datos_temporales()
        datos = json.loads(resultado)
        tabla = generar_tabla_markdown(datos[:5])
        
        assert "|" in tabla
        assert "---" in tabla
