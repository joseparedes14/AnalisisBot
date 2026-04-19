import json
import random

def generar_datos_temporales():
    """
    Genera datos simulados en formato JSON que representan la evolución 
    de métricas durante el desarrollo de una clase o sesión escolar.
    """
    datos = []
    
    # Simularemos una clase de 60 minutos, tomando registros cada minuto
    for minuto in range(0, 61):
        # Simulación basada en comportamientos lógicos durante la clase:
        
        # Inicio (minutos 0 al 5): baja atención al inicio, estudiantes entrando y acomodándose
        if minuto <= 5:
            apsud = random.randint(40, 55)   # Atención dispersa
            mr = random.randint(50, 80)      # Nivel de movimiento al sentarse (alto)
            psu = random.randint(20, 40)
            psur = random.randint(20, 40)
            
        # Final de clase (minutos 55 al 60): fatiga, pérdida de interés, ganas de salir
        elif minuto >= 55:
            apsud = random.randint(30, 45)
            mr = random.randint(60, 85)      # Inquietud y movimiento alto al final
            psu = random.randint(10, 30)
            psur = random.randint(10, 30)
            
        # Valle temporal (minutos 25 al 35): posible bajón a mitad de la sesión
        elif 25 <= minuto <= 35:
            apsud = random.randint(50, 70)
            mr = random.randint(40, 60)      
            psu = random.randint(40, 60)
            psur = random.randint(40, 60)
            
        # Picos de atención y participación (resto de la clase)
        else:
            apsud = random.randint(80, 95)  # Atención muy enfocada
            mr = random.randint(15, 35)     # Movimiento corporal bajo por concentración
            psu = random.randint(70, 95)
            psur = random.randint(70, 95)
            
        bloque = {
            "Minuto_Clase": minuto,
            "PSR": round(random.uniform(1.0, 5.0), 2),
            "APSUD": apsud,
            "PSU": psu,
            "PSUR": psur,
            "MR": mr
        }
        datos.append(bloque)
        
    return json.dumps(datos, indent=4)

if __name__ == "__main__":
    print("Datos temporales generados:")
    print(generar_datos_temporales())
