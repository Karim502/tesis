import os
import json
import joblib
import pandas as pd
from typing import TypedDict, List

# Rutas a los modelos guardados
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PREPROCESADOR_PATH = os.path.join(BASE_DIR, "ml_models", "preprocesador.joblib")
MODELO_PATH = os.path.join(BASE_DIR, "ml_models", "modelo_ganador.joblib")

# Cargar los artefactos
try:
    preprocesador = joblib.load(PREPROCESADOR_PATH)
    modelo = joblib.load(MODELO_PATH)
except Exception as e:
    print(f"Advertencia: No se pudieron cargar los modelos ML. Error: {e}")
    preprocesador, modelo = None, None

def _asegurar_diccionario(datos) -> dict:
    if not datos: return {}
    if isinstance(datos, str):
        try: return json.loads(datos)
        except json.JSONDecodeError: return {}
    return datos

def predecir_riesgo(respuestas) -> dict:
    respuestas = _asegurar_diccionario(respuestas)
    
    # --- CHIVATO 1: Ver qué manda realmente el frontend ---
    # print("\n--- DATOS CRUDOS RECIBIDOS DEL FRONTEND ---")
    # print(json.dumps(respuestas, indent=2, ensure_ascii=False))
    
    # Función auxiliar para buscar valores ignorando el nombre exacto de la llave
    def buscar_valor(palabra_clave, valor_por_defecto=""):
        for key, value in respuestas.items():
            if palabra_clave in key.lower():
                return str(value).strip()
        return valor_por_defecto

    # 1. PARSEO SÚPER FLEXIBLE (Busca fragmentos de la llave y del valor)
    tipo_str = buscar_valor("personeria").lower()
    if "ninguna" in tipo_str or "sin ruc" in tipo_str: tipo_contribuyente = "No_Registrado"
    elif "jurídica" in tipo_str or "sac" in tipo_str or "srl" in tipo_str: tipo_contribuyente = "Persona_Juridica"
    else: tipo_contribuyente = "Persona_Natural_Negocio"

    sector_str = buscar_valor("comercial").lower()
    if "abarrotes" in sector_str or "alimentos" in sector_str: sector = "Abarrotes_Alimentos"
    elif "textil" in sector_str or "vestir" in sector_str: sector = "Textil_Calzado"
    elif "ferreter" in sector_str or "hogar" in sector_str: sector = "Ferreteria_Hogar"
    elif "tecnolog" in sector_str or "equipos" in sector_str: sector = "Tecnologia_Repuestos"
    else: sector = "Bazar_VentaVar"

    hist_str = buscar_valor("auditoria").lower()
    if "reparos" in hist_str or "multas" in hist_str: historial = "Auditado_Con_Hallazgos"
    elif "sin hallazgos" in hist_str: historial = "Auditado_Sin_Hallazgos"
    else: historial = "Nunca_Auditado"

    def parse_dinero(val):
        if not val or "aplica" in val.lower(): return -1
        if "menos de" in val.lower(): return 25000
        if "50,001" in val: return 100000
        if "150,001" in val: return 225000
        if "300,001" in val: return 550000
        if "más de" in val.lower(): return 1000000
        return -1

    def parse_antiguedad(val):
        if not val: return 1
        if "menos de 1" in val.lower(): return 0.5
        if "1 a 3" in val: return 2
        if "4 a 5" in val: return 4.5
        if "6 a 10" in val: return 8
        if "más de 10" in val.lower(): return 15
        return 1

    def parse_empleados(val):
        if not val or val == "0" or "0 " in val: return 0
        if "1 a 5" in val: return 3
        if "6 a 10" in val: return 8
        if "11 a 50" in val: return 30
        if "más de 50" in val.lower(): return 60
        return 0

    def parse_porcentaje(val):
        if not val or "aplica" in val.lower(): return -1.0
        if "0% a 5%" in val: return 2.5
        if "0% a 10%" in val or "0% a 20%" in val: return 10.0
        if "6% a 15%" in val: return 10.5
        if "11% a 30%" in val: return 20.0
        if "16% a 30%" in val: return 23.0
        if "21% a 50%" in val: return 35.0
        if "31% a 60%" in val: return 45.0
        if "51% a 80%" in val: return 65.0
        if "61% a 100%" in val or "81% a 100%" in val: return 90.0
        if "más del 30%" in val.lower(): return 40.0
        if "más del 60%" in val.lower(): return 75.0
        return 0.0

    def parse_conteo(val):
        if not val or "aplica" in val.lower() or val == "0" or "0 " in val: return 0
        if "1 a 2" in val: return 1
        if "1 a 5" in val or "3 a 5" in val: return 4
        if "6 a 15" in val or "1 a 10" in val: return 10
        if "11 a 50" in val or "16 a 30" in val: return 25
        if "51 a 100" in val: return 75
        if "más de" in val.lower(): return 120
        return 0

    # 2. CONSTRUCCIÓN DEL DICCIONARIO
    datos_modelo = {}
    datos_modelo["tipo_contribuyente"] = tipo_contribuyente
    datos_modelo["sector_economico"] = sector
    datos_modelo["historial_auditoria"] = historial if tipo_contribuyente != "No_Registrado" else "No_Aplica_Informal"
    datos_modelo["antiguedad_anos"] = parse_antiguedad(buscar_valor("antiguedad"))
    datos_modelo["numero_empleados_formales"] = parse_empleados(buscar_valor("trabajadores"))
    
    ingresos = parse_dinero(buscar_valor("ingresos"))
    gastos = parse_dinero(buscar_valor("gastos"))
    datos_modelo["ingresos_declarados"] = ingresos
    datos_modelo["gastos_deducibles"] = gastos

    datos_modelo["porcentaje_efectivo"] = parse_porcentaje(buscar_valor("efectivo"))
    datos_modelo["facturas_anuladas"] = parse_conteo(buscar_valor("anulados"))
    datos_modelo["porcentaje_notas_credito"] = parse_porcentaje(buscar_valor("notas"))
    datos_modelo["compras_proveedores_nuevos_pct"] = parse_porcentaje(buscar_valor("proveedores"))
    datos_modelo["concentracion_cliente_principal"] = parse_porcentaje(buscar_valor("cliente"))
    datos_modelo["retraso_declaracion_dias"] = parse_conteo(buscar_valor("mora"))
    datos_modelo["declaraciones_rectificatorias"] = parse_conteo(buscar_valor("rectificatorias"))

    # 3. DERIVADAS
    if datos_modelo["tipo_contribuyente"] == "No_Registrado" or ingresos <= 0:
        datos_modelo["ratio_gastos_ingresos"] = -1.0
        datos_modelo["margen_utilidad_declarado"] = -1.0
    else:
        datos_modelo["ratio_gastos_ingresos"] = gastos / ingresos
        datos_modelo["margen_utilidad_declarado"] = (ingresos - gastos) / ingresos

    # --- CHIVATO 2: Ver cómo quedó el diccionario procesado antes de entrar al modelo ---
    # print("\n--- DATOS PROCESADOS LISTOS PARA EL MODELO ---")
    # print(json.dumps(datos_modelo, indent=2, ensure_ascii=False))

    if preprocesador is None or modelo is None:
        return {"probabilidad": 0.5, "nivel_riesgo": "Medio", "score": 50, "recomendaciones": [], "datos_procesados": datos_modelo}

    # 4. CREACIÓN DEL DATAFRAME
    try:
        columnas_esperadas = preprocesador.feature_names_in_
        df_entrada = pd.DataFrame([datos_modelo], columns=columnas_esperadas)
    except AttributeError:
        df_entrada = pd.DataFrame([datos_modelo])

    for col in df_entrada.columns:
        df_entrada[col] = pd.to_numeric(df_entrada[col], errors='ignore')
    
    # 5. PREDICCIÓN
    X_procesado = preprocesador.transform(df_entrada)
    prob_evasion = float(modelo.predict_proba(X_procesado)[0, 1])
    score_final = int(prob_evasion * 100)

    if score_final < 33: nivel_riesgo = "Bajo"
    elif score_final < 66: nivel_riesgo = "Medio"
    else: nivel_riesgo = "Alto"

    return {
        "probabilidad": prob_evasion,
        "nivel_riesgo": nivel_riesgo,
        "score": score_final,
        "recomendaciones": [],
        "datos_procesados": datos_modelo 
    }