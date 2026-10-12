# C:\Karim\Tesis_v3\backend\app\services\cuestionario.py

PREGUNTAS_MYPE = [
    {
        "id": "var_1_personeria_juridica",
        "bloque": "BLOQUE I: Perfil y Capacidad Operativa",
        "texto": "¿Cuál es la personería jurídica del contribuyente evaluado?",
        "tipo": "select",
        "opciones": [
            "Persona Natural con Negocio",
            "Persona Jurídica (SAC, SRL, SA, etc.)",
            "Ninguna / Negocio no registrado formalmente (Sin RUC)"
        ]
    },
    {
        "id": "var_2_subsector_comercial",
        "bloque": "BLOQUE I: Perfil y Capacidad Operativa",
        "texto": "¿A qué sub-sector comercial pertenece la actividad principal de la Mype?",
        "tipo": "select",
        "opciones": [
            "Comercio de alimentos, bebidas y abarrotes.",
            "Comercio de textiles, prendas de vestir y calzado.",
            "Comercio de artículos de ferretería, hogar y materiales.",
            "Comercio de equipos, tecnología, celulares y repuestos vehiculares.",
            "Comercio no especializado / Bazar, regalos y librerías.",
            "Otro sub-sector comercial"
        ]
    },
    {
        "id": "var_3_antiguedad",
        "bloque": "BLOQUE I: Perfil y Capacidad Operativa",
        "texto": "¿Cuántos años de antigüedad o funcionamiento continuo tiene la empresa desde su inicio de actividades?",
        "tipo": "select",
        "opciones": [
            "Menos de 1 año",
            "De 1 a 3 años",
            "De 4 a 5 años",
            "De 6 a 10 años",
            "Más de 10 años"
        ]
    },
    {
        "id": "var_4_trabajadores",
        "bloque": "BLOQUE I: Perfil y Capacidad Operativa",
        "texto": "¿Cuántos trabajadores dependientes mantiene registrados formalmente en planilla/nómina?",
        "tipo": "select",
        "opciones": [
            "0 trabajadores (Solo labora el titular, familiares o no se cuenta con planilla formal)",
            "De 1 a 5 trabajadores",
            "De 6 a 10 trabajadores",
            "De 11 a 50 trabajadores",
            "Más de 50 trabajadores"
        ]
    },
    {
        "id": "var_5_ingresos_brutos",
        "bloque": "BLOQUE II: Estructura Financiera y Contable",
        "texto": "¿En qué rango se encuentra el monto total de ingresos brutos declarados en el ejercicio fiscal anual?",
        "tipo": "select",
        "opciones": [
            "No aplica / No declaro ingresos a la autoridad tributaria",
            "Menos de S/ 50,000",
            "De S/ 50,001 a S/ 150,000",
            "De S/ 150,001 a S/ 300,000",
            "De S/ 300,001 a S/ 800,000",
            "Más de S/ 800,000"
        ]
    },
    {
        "id": "var_6_costos_gastos",
        "bloque": "BLOQUE II: Estructura Financiera y Contable",
        "texto": "¿En qué rango se encuentran los costos y gastos deducibles debidamente sustentados en el mismo ejercicio?",
        "tipo": "select",
        "opciones": [
            "No aplica / No declaro gastos a la autoridad tributaria",
            "Menos de S/ 50,000",
            "De S/ 50,001 a S/ 150,000",
            "De S/ 150,001 a S/ 300,000",
            "De S/ 300,001 a S/ 800,000",
            "Más de S/ 800,000"
        ]
    },
    {
        "id": "var_7_porcentaje_efectivo",
        "bloque": "BLOQUE II: Estructura Financiera y Contable",
        "texto": "¿Qué porcentaje estimado de sus ingresos totales se percibe en dinero en efectivo?",
        "tipo": "select",
        "opciones": [
            "0% a 10%",
            "11% a 30%",
            "31% a 60%",
            "61% a 100%"
        ]
    },
    {
        "id": "var_8_comprobantes_anulados",
        "bloque": "BLOQUE III: Comportamiento Transaccional",
        "texto": "¿Qué cantidad de comprobantes de pago (facturas, boletas, etc.) fueron anulados o dados de baja en el sistema durante el año?",
        "tipo": "select",
        "opciones": [
            "No aplica / No emito comprobantes de pago formales",
            "0 (Ninguno)",
            "De 1 a 10 comprobantes",
            "De 11 a 50 comprobantes",
            "De 51 a 100 comprobantes",
            "Más de 100 comprobantes"
        ]
    },
    {
        "id": "var_9_notas_credito",
        "bloque": "BLOQUE III: Comportamiento Transaccional",
        "texto": "¿Qué porcentaje aproximado de su volumen total de ventas fue ajustado o revertido mediante la emisión de Notas de Crédito?",
        "tipo": "select",
        "opciones": [
            "No aplica / No emito comprobantes formales",
            "0% a 5%",
            "6% a 15%",
            "16% a 30%",
            "Más del 30%"
        ]
    },
    {
        "id": "var_10_proveedores_nuevos",
        "bloque": "BLOQUE III: Comportamiento Transaccional",
        "texto": "Del total de sus compras anuales, ¿qué porcentaje proviene de proveedores 'nuevos' (empresas creadas hace menos de 1 año)?",
        "tipo": "select",
        "opciones": [
            "0% a 10%",
            "11% a 30%",
            "31% a 60%",
            "Más del 60%"
        ]
    },
    {
        "id": "var_11_cliente_principal",
        "bloque": "BLOQUE III: Comportamiento Transaccional",
        "texto": "¿Qué porcentaje de sus ingresos totales depende exclusivamente de su cliente principal?",
        "tipo": "select",
        "opciones": [
            "0% a 20%",
            "21% a 50%",
            "51% a 80%",
            "81% a 100%"
        ]
    },
    {
        "id": "var_12_resultado_auditoria",
        "bloque": "BLOQUE IV: Cumplimiento Tributario e Historial de Fiscalización",
        "texto": "¿Cuál ha sido el resultado histórico de sus interacciones de fiscalización o auditoría con la entidad tributaria?",
        "tipo": "select",
        "opciones": [
            "Nunca ha sido auditado o no aplica por no estar registrado.",
            "Ha sido auditado en el pasado, sin hallazgos relevantes ni sanciones.",
            "Ha sido auditado y se le determinaron reparos, inconsistencias o multas."
        ]
    },
    {
        "id": "var_13_dias_mora",
        "bloque": "BLOQUE IV: Cumplimiento Tributario e Historial de Fiscalización",
        "texto": "Durante el último año, ¿cuántos días de mora o retraso acumuló en total para la presentación de sus declaraciones obligatorias?",
        "tipo": "select",
        "opciones": [
            "No aplica / No estoy inscrito para presentar declaraciones",
            "0 días",
            "De 1 a 5 días acumulados",
            "De 6 a 15 días acumulados",
            "De 16 a 30 días acumulados",
            "Más de 30 días acumulados"
        ]
    },
    {
        "id": "var_14_rectificatorias",
        "bloque": "BLOQUE IV: Cumplimiento Tributario e Historial de Fiscalización",
        "texto": "¿Cuántas declaraciones juradas rectificatorias (modificatorias) presentó durante el último ejercicio fiscal?",
        "tipo": "select",
        "opciones": [
            "No aplica / No presento declaraciones formales",
            "0 rectificatorias",
            "1 a 2 rectificatorias",
            "3 a 5 rectificatorias",
            "Más de 5 rectificatorias"
        ]
    },
]

def obtener_cuestionario():
    """
    Retorna la lista de preguntas estructurada por bloques.
    """
    return PREGUNTAS_MYPE

# --- AGREGAR ESTO AL FINAL DEL ARCHIVO ---

# 1. Renombramos la variable para que el router de Claude la encuentre
PREGUNTAS = PREGUNTAS_MYPE

# 2. Excepción personalizada que espera el router
class RespuestasInvalidas(Exception):
    pass

# 3. Función de validación que verifica que lleguen las 15 respuestas
def validar_respuestas(respuestas: dict):
    claves_esperadas = {p["id"] for p in PREGUNTAS}
    claves_recibidas = set(respuestas.keys())
    
    faltantes = claves_esperadas - claves_recibidas
    if faltantes:
        raise RespuestasInvalidas(f"Faltan las siguientes respuestas: {faltantes}")