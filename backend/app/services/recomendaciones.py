def generar_recomendaciones(respuestas: dict, pred) -> list:
    """
    Genera un Plan de Acción (checklist) dinámico basado en las 14 variables 
    del formulario actual.
    """
    recomendaciones = []
    
    # 1. Alerta de Informalidad (var_1)
    personeria = respuestas.get("var_1_personeria_juridica", "")
    if "Ninguna" in personeria or "Sin RUC" in personeria:
        recomendaciones.append({
            "id": "rec_formalizacion",
            "titulo": "Inicia tu proceso de formalización",
            "detalle": "Actualmente operas sin RUC. Formalizarte evitará sanciones de SUNAT, comisos de mercadería y te permitirá acceder a créditos para crecer.",
            "prioridad": "alta",
            "completada": False
        })

    # 2. Alerta de Auditorías Previas (var_12)
    auditoria = respuestas.get("var_12_resultado_auditoria", "")
    if "reparos, inconsistencias o multas" in auditoria:
        recomendaciones.append({
            "id": "rec_auditoria",
            "titulo": "Asesoría Contable Preventiva",
            "detalle": "Como tuviste multas o hallazgos en auditorías pasadas, estás en la mira para futuras revisiones. Te sugerimos auditorías preventivas internas anuales.",
            "prioridad": "alta",
            "completada": False
        })

    # 3. Alerta por Exceso de Efectivo (var_7)
    efectivo = respuestas.get("var_7_porcentaje_efectivo", "")
    if "61%" in efectivo or "81%" in efectivo or "Más del" in efectivo:
        recomendaciones.append({
            "id": "rec_bancarizacion",
            "titulo": "Bancariza tus cobros",
            "detalle": "Cobrar casi todo en efectivo eleva tu perfil de riesgo fiscal por presunta evasión. Promueve pagos con transferencia, POS o billeteras digitales.",
            "prioridad": "media",
            "completada": False
        })

    # 4. Alerta por Mora en Declaraciones (var_13)
    mora = respuestas.get("var_13_dias_mora", "")
    if "16 a 30" in mora or "Más de 30" in mora:
        recomendaciones.append({
            "id": "rec_calendario",
            "titulo": "Automatiza tu calendario tributario",
            "detalle": "Los retrasos en declaraciones generan multas automáticas e intereses moratorios. Configura alarmas según el último dígito de tu RUC.",
            "prioridad": "alta",
            "completada": False
        })

    # 5. Alerta por Exceso de Rectificatorias (var_14)
    rectificatorias = respuestas.get("var_14_rectificatorias", "")
    if "3 a 5" in rectificatorias or "Más de 5" in rectificatorias:
        recomendaciones.append({
            "id": "rec_rectificatorias",
            "titulo": "Revisión cruzada antes de declarar",
            "detalle": "Presentar muchas modificatorias (rectificatorias) es un indicador de desorden contable. Implementa un doble filtro antes de enviar tu DJ mensual.",
            "prioridad": "media",
            "completada": False
        })

    # 6. Alerta por Proveedores Nuevos/No Habituales (var_10)
    proveedores = respuestas.get("var_10_proveedores_nuevos", "")
    if "51%" in proveedores or "61%" in proveedores or "81%" in proveedores:
        recomendaciones.append({
            "id": "rec_proveedores",
            "titulo": "Verifica el estado de tus proveedores",
            "detalle": "Al comprar constantemente a proveedores nuevos, corres el riesgo de usar facturas de empresas no habidas. Valida su RUC en SUNAT antes de pagar.",
            "prioridad": "media",
            "completada": False
        })

    # Recomendación por defecto si todo está perfecto
    if len(recomendaciones) == 0:
        recomendaciones.append({
            "id": "rec_excelencia",
            "titulo": "Mantén tus buenas prácticas",
            "detalle": "Tus indicadores son muy sólidos. Continúa declarando con transparencia para mantener tu riesgo fiscal al mínimo.",
            "prioridad": "baja",
            "completada": False
        })

    return recomendaciones