"""
PUNTO DE INTEGRACIÓN CON TU MODELO ENTRENADO.

`construir_features` convierte las respuestas guardadas de una evaluación en la fila que espera el modelo.
Debe reproducir EXACTAMENTE el preprocesamiento del entrenamiento. La versión por defecto cubre los dos casos
más comunes; si tu entrenamiento hizo otra cosa (codificación ordinal manual, ratios derivados, escalado...),
adapta SOLO esta función y el resto del endpoint SHAP no cambia:

  - Estimador de árboles entrenado con un DataFrame de pandas (columnas de texto como `category`):
      las respuestas de texto se pasan como `category`; LightGBM/XGBoost reasignan las categorías con las que
      se entrenó. Es el caso por defecto (`como_categoria=True`).
  - sklearn Pipeline (ColumnTransformer + árbol): se pasan los textos tal cual (`como_categoria=False`)
      y el propio Pipeline hace la codificación.
"""


class FeaturesFaltantes(Exception):
    """La evaluación no tiene respuestas para alguna columna que el modelo necesita."""

    def __init__(self, faltantes: list[str]):
        super().__init__(", ".join(faltantes))
        self.faltantes = faltantes


def construir_features(respuestas: dict, columnas: list[str], como_categoria: bool = True):
    import pandas as pd

    # 1. DICCIONARIOS DE TRADUCCIÓN (De opciones del Frontend a valores del Modelo)
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
    map_historial = {
        "Nunca ha sido auditado o no aplica por no estar registrado.": "Nunca_Auditado",
        "Ha sido auditado en el pasado, sin hallazgos relevantes ni sanciones.": "Auditado_Sin_Hallazgos",
        "Ha sido auditado y se le determinaron reparos, inconsistencias o multas.": "Auditado_Con_Hallazgos"
    }

    # Funciones auxiliares para convertir rangos de texto a valores numéricos aproximados
    def parse_antiguedad(val):
        if not val: return 1
        if "Menos de 1" in val: return 0.5
        if "1 a 3" in val: return 2
        if "4 a 5" in val: return 4.5
        if "6 a 10" in val: return 8
        if "Más de 10" in val: return 15
        return 1

    def parse_empleados(val):
        if not val or "0 " in val: return 0
        if "1 a 5" in val: return 3
        if "6 a 10" in val: return 8
        if "11 a 50" in val: return 30
        if "Más de 50" in val: return 60
        return 0

    def parse_dinero(val):
        if not val or "No aplica" in val: return -1
        if "Menos de" in val: return 25000
        if "50,001 a S/ 150,000" in val: return 100000
        if "150,001 a S/ 300,000" in val: return 225000
        if "300,001 a S/ 800,000" in val: return 550000
        if "Más de" in val: return 1000000
        return -1

    def parse_porcentaje(val):
        if not val or "No aplica" in val: return -1.0
        if "0% a 5%" in val: return 2.5
        if "0% a 10%" in val or "0% a 20%" in val: return 10.0
        if "6% a 15%" in val: return 10.5
        if "11% a 30%" in val: return 20.0
        if "16% a 30%" in val: return 23.0
        if "21% a 50%" in val: return 35.0
        if "31% a 60%" in val: return 45.0
        if "51% a 80%" in val: return 65.0
        if "61% a 100%" in val or "81% a 100%" in val: return 90.0
        if "Más del 30%" in val: return 40.0
        if "Más del 60%" in val: return 75.0
        return 0.0

    def parse_conteo(val):
        if not val or "No aplica" in val or "0 " in val: return 0
        if "1 a 2" in val: return 1
        if "1 a 5" in val or "3 a 5" in val: return 4
        if "6 a 15" in val or "1 a 10" in val: return 10
        if "11 a 50" in val or "16 a 30" in val: return 25
        if "51 a 100" in val: return 75
        if "Más de" in val: return 120
        return 0

    # 2. CONSTRUCCIÓN DEL DICCIONARIO PARA EL MODELO
    respuestas_modelo = {}
    
    # Textos a Categorías exactas
    respuestas_modelo["tipo_contribuyente"] = map_tipo.get(respuestas.get("var_1_personeria_juridica"), "No_Registrado")
    respuestas_modelo["sector_economico"] = map_sector.get(respuestas.get("var_2_subsector_comercial"), "Bazar_VentaVar")
    respuestas_modelo["historial_auditoria"] = map_historial.get(respuestas.get("var_12_resultado_auditoria"), "No_Aplica_Informal")

    # Textos a Números
    respuestas_modelo["antiguedad_anos"] = parse_antiguedad(respuestas.get("var_3_antiguedad"))
    respuestas_modelo["numero_empleados_formales"] = parse_empleados(respuestas.get("var_4_trabajadores"))
    
    ingresos = parse_dinero(respuestas.get("var_5_ingresos_brutos"))
    gastos = parse_dinero(respuestas.get("var_6_costos_gastos"))
    respuestas_modelo["ingresos_declarados"] = ingresos
    respuestas_modelo["gastos_deducibles"] = gastos

    respuestas_modelo["porcentaje_efectivo"] = parse_porcentaje(respuestas.get("var_7_porcentaje_efectivo"))
    respuestas_modelo["facturas_anuladas"] = parse_conteo(respuestas.get("var_8_comprobantes_anulados"))
    respuestas_modelo["porcentaje_notas_credito"] = parse_porcentaje(respuestas.get("var_9_notas_credito"))
    respuestas_modelo["compras_proveedores_nuevos_pct"] = parse_porcentaje(respuestas.get("var_10_proveedores_nuevos"))
    respuestas_modelo["concentracion_cliente_principal"] = parse_porcentaje(respuestas.get("var_11_cliente_principal"))
    respuestas_modelo["retraso_declaracion_dias"] = parse_conteo(respuestas.get("var_13_dias_mora"))
    respuestas_modelo["declaraciones_rectificatorias"] = parse_conteo(respuestas.get("var_14_rectificatorias"))

    # 3. CÁLCULO DE VARIABLES DERIVADAS (Completando las 16 variables)
    # Replicamos la lógica de informales del Notebook (-1 si no declaran)
    if respuestas_modelo["tipo_contribuyente"] == "No_Registrado" or ingresos <= 0:
        respuestas_modelo["ratio_gastos_ingresos"] = -1.0
        respuestas_modelo["margen_utilidad_declarado"] = -1.0
        respuestas_modelo["historial_auditoria"] = "No_Aplica_Informal"
    else:
        respuestas_modelo["ratio_gastos_ingresos"] = gastos / ingresos
        respuestas_modelo["margen_utilidad_declarado"] = (ingresos - gastos) / ingresos

    # 4. VALIDACIÓN ORIGINAL Y CREACIÓN DEL DATAFRAME
    faltantes = [c for c in columnas if respuestas_modelo.get(c) is None]
    if faltantes:
        raise FeaturesFaltantes(faltantes)

    df = pd.DataFrame([{c: respuestas_modelo[c] for c in columnas}], columns=columnas)
    
    if como_categoria:
        for c in columnas:
            if not pd.api.types.is_numeric_dtype(df[c]):
                df[c] = df[c].astype("category")
    return df