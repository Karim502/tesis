import os
import joblib
import pandas as pd

# Rutas a los modelos guardados (asegúrate de que la carpeta ml_models esté en la raíz del backend)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PREPROCESADOR_PATH = os.path.join(BASE_DIR, "ml_models", "preprocesador.joblib")
MODELO_PATH = os.path.join(BASE_DIR, "ml_models", "modelo_ganador.joblib") # Tu LightGBM

# Cargar los artefactos al iniciar el servidor (para que sea rápido)
try:
    preprocesador = joblib.load(PREPROCESADOR_PATH)
    modelo = joblib.load(MODELO_PATH)
except Exception as e:
    print(f"Advertencia: No se pudieron cargar los modelos ML. Error: {e}")
    preprocesador, modelo = None, None

def predecir_riesgo(respuestas: dict) -> dict:
    """
    Recibe el diccionario de 14 respuestas en texto del frontend, las mapea 
    a las 16 variables numéricas/categóricas exactas que espera el LightGBM, 
    y devuelve la predicción.
    """
    
    # 1. MAPEOS DE CATEGÓRICAS (De texto a las clases de Colab)
    map_tipo = {
        "Persona Natural con Negocio": "Persona_Natural_Negocio",
        "Persona Jurídica (SAC, SRL, SA, etc.)": "Persona_Juridica",
        "Ninguna / Negocio no registrado formalmente (Sin RUC)": "No_Registrado"
    }
    
    map_sector = {
        "Comercio de alimentos, bebidas y abarrotes.": "Abarrotes_Alimentos",
        "Comercio de textiles, prendas de vestir y calzado.": "Textil_Calzado",
        "Comercio de artículos de ferretería, hogar y materiales.": "Ferreteria_Hogar",
        "Comercio de equipos, tecnología, celulares y repuestos vehiculares.": "Tecnologia_Repuestos",
        "Comercio no especializado / Bazar, regalos y librerías.": "Bazar_VentaVar",
        "Otro sub-sector comercial": "Bazar_VentaVar"
    }

    map_auditoria = {
        "Nunca ha sido auditado o no aplica por no estar registrado.": "Nunca_Auditado",
        "Ha sido auditado en el pasado, sin hallazgos relevantes ni sanciones.": "Auditado_Sin_Hallazgos",
        "Ha sido auditado y se le determinaron reparos, inconsistencias o multas.": "Auditado_Con_Hallazgos"
    }

    # 2. MAPEOS NUMÉRICOS (De rangos de texto a puntos medios matemáticos)
    map_antiguedad = {
        "Menos de 1 año": 0.5, "De 1 a 3 años": 2, "De 4 a 5 años": 4.5, "De 6 a 10 años": 8, "Más de 10 años": 15
    }
    map_trabajadores = {
        "0 trabajadores (Solo labora el titular, familiares o no se cuenta con planilla formal)": 0,
        "De 1 a 5 trabajadores": 3, "De 6 a 10 trabajadores": 8, "De 11 a 50 trabajadores": 30, "Más de 50 trabajadores": 60
    }
    map_dinero = {
        "No aplica / No declaro ingresos a la autoridad tributaria": -1,
        "No aplica / No declaro gastos a la autoridad tributaria": -1,
        "Menos de S/ 50,000": 25000, "De S/ 50,001 a S/ 150,000": 100000, 
        "De S/ 150,001 a S/ 300,000": 225000, "De S/ 300,001 a S/ 800,000": 550000, "Más de S/ 800,000": 1200000
    }
    map_porcentajes = {
        "0% a 5%": 2.5, "0% a 10%": 5, "0% a 20%": 10, "6% a 15%": 10.5, 
        "11% a 30%": 20.5, "16% a 30%": 23, "21% a 50%": 35.5, "31% a 60%": 45.5, 
        "51% a 80%": 65.5, "61% a 100%": 80.5, "81% a 100%": 90.5, "Más del 30%": 45, "Más del 60%": 80,
        "No aplica / No emito comprobantes formales": -1
    }
    map_cantidades = {
        "No aplica / No emito comprobantes de pago formales": -1, "No aplica / No estoy inscrito para presentar declaraciones": -1,
        "No aplica / No presento declaraciones formales": -1,
        "0 (Ninguno)": 0, "0 días": 0, "0 rectificatorias": 0,
        "De 1 a 10 comprobantes": 5, "De 11 a 50 comprobantes": 30, "De 51 a 100 comprobantes": 75, "Más de 100 comprobantes": 150,
        "De 1 a 5 días acumulados": 3, "De 6 a 15 días acumulados": 10, "De 16 a 30 días acumulados": 23, "Más de 30 días acumulados": 45,
        "1 a 2 rectificatorias": 1.5, "3 a 5 rectificatorias": 4, "Más de 5 rectificatorias": 7
    }

    # 3. EXTRACCIÓN DE VALORES BASE
    tipo_contribuyente = map_tipo.get(respuestas.get("var_1_personeria_juridica", ""), "No_Registrado")
    es_informal = (tipo_contribuyente == "No_Registrado")

    # Si es informal, forzamos valores según la lógica de tu Colab
    ingresos = -1 if es_informal else map_dinero.get(respuestas.get("var_5_ingresos_brutos"), 0)
    gastos = -1 if es_informal else map_dinero.get(respuestas.get("var_6_costos_gastos"), 0)
    
    # 4. CÁLCULO DE LAS 2 VARIABLES FALTANTES (DIMENSIÓN 2)
    if ingresos > 0 and gastos >= 0 and not es_informal:
        ratio_gastos_ingresos = gastos / ingresos
        margen_utilidad_declarado = (ingresos - gastos) / ingresos
    else:
        ratio_gastos_ingresos = -1.0
        margen_utilidad_declarado = -1.0

    # 5. CONSTRUIR DICCIONARIO DE 16 VARIABLES EXACTAS
    datos_modelo = {
        'tipo_contribuyente': tipo_contribuyente,
        'sector_economico': map_sector.get(respuestas.get("var_2_subsector_comercial"), "Bazar_VentaVar"),
        'antiguedad_anos': map_antiguedad.get(respuestas.get("var_3_antiguedad"), 0),
        'numero_empleados_formales': 0 if es_informal else map_trabajadores.get(respuestas.get("var_4_trabajadores"), 0),
        
        'ingresos_declarados': ingresos,
        'gastos_deducibles': gastos,
        'ratio_gastos_ingresos': ratio_gastos_ingresos,
        'porcentaje_efectivo': 100.0 if es_informal else map_porcentajes.get(respuestas.get("var_7_porcentaje_efectivo"), 0),
        'margen_utilidad_declarado': margen_utilidad_declarado,
        
        'facturas_anuladas': -1 if es_informal else map_cantidades.get(respuestas.get("var_8_comprobantes_anulados"), 0),
        'porcentaje_notas_credito': -1 if es_informal else map_porcentajes.get(respuestas.get("var_9_notas_credito"), 0),
        'compras_proveedores_nuevos_pct': map_porcentajes.get(respuestas.get("var_10_proveedores_nuevos"), 0),
        'concentracion_cliente_principal': map_porcentajes.get(respuestas.get("var_11_cliente_principal"), 0),
        
        'historial_auditoria': "No_Aplica_Informal" if es_informal else map_auditoria.get(respuestas.get("var_12_resultado_auditoria"), "Nunca_Auditado"),
        'retraso_declaracion_dias': -1 if es_informal else map_cantidades.get(respuestas.get("var_13_dias_mora"), 0),
        'declaraciones_rectificatorias': -1 if es_informal else map_cantidades.get(respuestas.get("var_14_rectificatorias"), 0)
    }

    # 6. PREDICCIÓN ML
    # Si no cargó el modelo por error de ruta, devolvemos simulación para no colgar la app
    if preprocesador is None or modelo is None:
        return {"probabilidad": 0.5, "nivel_riesgo": "Medio", "score": 50, "recomendaciones": []}

    df_entrada = pd.DataFrame([datos_modelo])
    
    # Aplicar StandardScaler y OneHotEncoder
    X_procesado = preprocesador.transform(df_entrada)
    
    # Predecir probabilidad con LightGBM (usualmente [:, 1] para clase positiva)
    prob_evasion = float(modelo.predict_proba(X_procesado)[0, 1])
    score_final = int(prob_evasion * 100)

    # Definir Nivel de Riesgo
    if score_final < 33:
        nivel_riesgo = "Bajo"
    elif score_final < 66:
        nivel_riesgo = "Medio"
    else:
        nivel_riesgo = "Alto"

    # Generar recomendaciones dinámicas (Requerido por la respuesta del frontend)
    recomendaciones = []
    if ratio_gastos_ingresos > 0.90:
        recomendaciones.append({"id": "rec_1", "titulo": "Revisión de Gastos", "detalle": "Sus gastos declarados son muy cercanos a sus ingresos, lo cual es un foco rojo para auditorías.", "prioridad": "alta", "completada": False})
    if es_informal:
        recomendaciones.append({"id": "rec_2", "titulo": "Formalización Tributaria", "detalle": "No cuenta con RUC activo. Regularice su inscripción para evitar multas severas.", "prioridad": "alta", "completada": False})
    if len(recomendaciones) == 0:
        recomendaciones.append({"id": "rec_3", "titulo": "Mantener buen cumplimiento", "detalle": "Sus indicadores son estables. Continúe declarando a tiempo.", "prioridad": "baja", "completada": False})

    return {
        "probabilidad": prob_evasion,
        "nivel_riesgo": nivel_riesgo,
        "score": score_final,
        "recomendaciones": recomendaciones
    }

# --- AGREGAR ESTO AL FINAL DEL ARCHIVO PARA COMPATIBILIDAD ---
from typing import TypedDict, List

class Prediccion(TypedDict):
    probabilidad: float
    nivel_riesgo: str
    score: int
    recomendaciones: List[dict]

def excede_limite_regimen(respuestas: dict) -> bool:
    """
    Función de compatibilidad para el generador de recomendaciones.
    Verifica si los ingresos superan límites de ciertos regímenes.
    """
    ingresos = str(respuestas.get("var_5_ingresos_brutos", ""))
    return "Más de S/ 800,000" in ingresos