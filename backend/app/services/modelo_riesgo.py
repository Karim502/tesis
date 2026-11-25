import json
import logging
import pandas as pd

from app.services.explicabilidad import ModeloNoDisponible, cargar_modelo

log = logging.getLogger(__name__)

MAPA_PERSONERIA = {
    "Persona Natural con Negocio": "Persona_Natural_Negocio",
    "Persona Jurídica (SAC, SRL, SA, etc.)": "Persona_Juridica",
    "Ninguna / Negocio no registrado formalmente (Sin RUC)": "No_Registrado",
}

MAPA_SECTOR = {
    "Comercio de alimentos, bebidas y abarrotes.": "Abarrotes_Alimentos",
    "Comercio de textiles, prendas de vestir y calzado.": "Textil_Calzado",
    "Comercio de artículos de ferretería, hogar y materiales.": "Ferreteria_Hogar",
    "Comercio de equipos, tecnología, celulares y repuestos vehiculares.": "Tecnologia_Repuestos",
    "Comercio no especializado / Bazar, regalos y librerías.": "Bazar_VentaVar",
    "Otro sub-sector comercial": "Bazar_VentaVar",
}

MAPA_ANTIGUEDAD = {
    "Menos de 1 año": 0.5,
    "De 1 a 3 años": 2.0,
    "De 4 a 5 años": 4.5,
    "De 6 a 10 años": 8.0,
    "Más de 10 años": 15.0,
}

MAPA_EMPLEADOS = {
    "0 trabajadores (Solo labora el titular, familiares o no se cuenta con planilla formal)": 0,
    "De 1 a 5 trabajadores": 3,
    "De 6 a 10 trabajadores": 8,
    "De 11 a 50 trabajadores": 30,
    "Más de 50 trabajadores": 60,
}

MAPA_INGRESOS = {
    "No aplica / No declaro ingresos a la autoridad tributaria": -1,
    "Menos de S/ 50,000": 25000,
    "De S/ 50,001 a S/ 150,000": 100000,
    "De S/ 150,001 a S/ 300,000": 225000,
    "De S/ 300,001 a S/ 800,000": 550000,
    "Más de S/ 800,000": 1000000,
}

MAPA_GASTOS = {
    "No aplica / No declaro gastos a la autoridad tributaria": -1,
    "Menos de S/ 50,000": 25000,
    "De S/ 50,001 a S/ 150,000": 100000,
    "De S/ 150,001 a S/ 300,000": 225000,
    "De S/ 300,001 a S/ 800,000": 550000,
    "Más de S/ 800,000": 1000000,
}

MAPA_EFECTIVO = {
    "0% a 10%": 5.0,
    "11% a 30%": 20.0,
    "31% a 60%": 45.0,
    "61% a 100%": 80.0,
}

MAPA_FACTURAS_ANULADAS = {
    "No aplica / No emito comprobantes de pago formales": -1,
    "0 (Ninguno)": 0,
    "De 1 a 10 comprobantes": 5,
    "De 11 a 50 comprobantes": 25,
    "De 51 a 100 comprobantes": 75,
    "Más de 100 comprobantes": 120,
}

MAPA_NOTAS_CREDITO = {
    "No aplica / No emito comprobantes formales": -1.0,
    "0% a 5%": 2.5,
    "6% a 15%": 10.5,
    "16% a 30%": 23.0,
    "Más del 30%": 40.0,
}

MAPA_PROVEEDORES_NUEVOS = {
    "0% a 10%": 5.0,
    "11% a 30%": 20.0,
    "31% a 60%": 45.0,
    "Más del 60%": 75.0,
}

MAPA_CLIENTE_PRINCIPAL = {
    "0% a 20%": 10.0,
    "21% a 50%": 35.0,
    "51% a 80%": 65.0,
    "81% a 100%": 90.0,
}

MAPA_AUDITORIA = {
    "Nunca ha sido auditado o no aplica por no estar registrado.": "Nunca_Auditado",
    "Ha sido auditado en el pasado, sin hallazgos relevantes ni sanciones.": "Auditado_Sin_Hallazgos",
    "Ha sido auditado y se le determinaron reparos, inconsistencias o multas.": "Auditado_Con_Hallazgos",
}

MAPA_DIAS_MORA = {
    "No aplica / No estoy inscrito para presentar declaraciones": -1,
    "0 días": 0,
    "De 1 a 5 días acumulados": 3,
    "De 6 a 15 días acumulados": 10,
    "De 16 a 30 días acumulados": 23,
    "Más de 30 días acumulados": 40,
}

MAPA_RECTIFICATORIAS = {
    "No aplica / No presento declaraciones formales": -1,
    "0 rectificatorias": 0,
    "1 a 2 rectificatorias": 2,
    "3 a 5 rectificatorias": 4,
    "Más de 5 rectificatorias": 7,
}


def _asegurar_diccionario(datos) -> dict:
    if not datos:
        return {}
    if isinstance(datos, str):
        try:
            return json.loads(datos)
        except json.JSONDecodeError:
            return {}
    return datos


def construir_features_modelo(respuestas) -> dict:
    """Convierte las 14 respuestas validadas del cuestionario a las 16 variables crudas del pipeline."""
    r = _asegurar_diccionario(respuestas)

    tipo_contribuyente = MAPA_PERSONERIA.get(r.get("var_1_personeria_juridica", ""), "Persona_Natural_Negocio")
    sector = MAPA_SECTOR.get(r.get("var_2_subsector_comercial", ""), "Bazar_VentaVar")
    historial_base = MAPA_AUDITORIA.get(r.get("var_12_resultado_auditoria", ""), "Nunca_Auditado")
    historial = "No_Aplica_Informal" if tipo_contribuyente == "No_Registrado" else historial_base

    ingresos = MAPA_INGRESOS.get(r.get("var_5_ingresos_brutos", ""), -1)
    gastos = MAPA_GASTOS.get(r.get("var_6_costos_gastos", ""), -1)

    if tipo_contribuyente == "No_Registrado" or ingresos <= 0 or gastos < 0:
        ratio_gastos_ingresos = -1.0
        margen_utilidad_declarado = -1.0
    else:
        ratio_gastos_ingresos = gastos / ingresos
        margen_utilidad_declarado = (ingresos - gastos) / ingresos

    return {
        "tipo_contribuyente": tipo_contribuyente,
        "sector_economico": sector,
        "historial_auditoria": historial,
        "antiguedad_anos": MAPA_ANTIGUEDAD.get(r.get("var_3_antiguedad", ""), 1.0),
        "numero_empleados_formales": MAPA_EMPLEADOS.get(r.get("var_4_trabajadores", ""), 0),
        "ingresos_declarados": ingresos,
        "gastos_deducibles": gastos,
        "ratio_gastos_ingresos": ratio_gastos_ingresos,
        "margen_utilidad_declarado": margen_utilidad_declarado,
        "porcentaje_efectivo": MAPA_EFECTIVO.get(r.get("var_7_porcentaje_efectivo", ""), 0.0),
        "facturas_anuladas": MAPA_FACTURAS_ANULADAS.get(r.get("var_8_comprobantes_anulados", ""), -1),
        "porcentaje_notas_credito": MAPA_NOTAS_CREDITO.get(r.get("var_9_notas_credito", ""), -1.0),
        "compras_proveedores_nuevos_pct": MAPA_PROVEEDORES_NUEVOS.get(r.get("var_10_proveedores_nuevos", ""), 0.0),
        "concentracion_cliente_principal": MAPA_CLIENTE_PRINCIPAL.get(r.get("var_11_cliente_principal", ""), 0.0),
        "retraso_declaracion_dias": MAPA_DIAS_MORA.get(r.get("var_13_dias_mora", ""), -1),
        "declaraciones_rectificatorias": MAPA_RECTIFICATORIAS.get(r.get("var_14_rectificatorias", ""), -1),
    }


def predecir_riesgo(respuestas) -> dict:
    datos_modelo = construir_features_modelo(respuestas)

    try:
        m = cargar_modelo()
    except ModeloNoDisponible as exc:
        log.error("Modelo no disponible para predicción (%s).", exc.motivo)
        raise

    df_entrada = pd.DataFrame([datos_modelo], columns=list(m.columnas))

    cols_categoricas = {"tipo_contribuyente", "sector_economico", "historial_auditoria"}
    for col in df_entrada.columns:
        if col not in cols_categoricas:
            df_entrada[col] = pd.to_numeric(df_entrada[col], errors="coerce")

    X_procesado = m.preprocesador.transform(df_entrada) if m.preprocesador is not None else df_entrada
    idx = m.idx_clase if m.idx_clase is not None else 1
    prob_evasion = float(m.estimador.predict_proba(X_procesado)[0, idx])

    if prob_evasion < 0.33:
        nivel_riesgo = "Bajo"
    elif prob_evasion < 0.66:
        nivel_riesgo = "Medio"
    else:
        nivel_riesgo = "Alto"

    score_cumplimiento = 100 - round(prob_evasion * 100)

    return {
        "probabilidad": prob_evasion,
        "nivel_riesgo": nivel_riesgo,
        "score": score_cumplimiento,
        "recomendaciones": [],
        "datos_procesados": datos_modelo,
    }