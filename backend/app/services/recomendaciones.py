def _extraer_probabilidad(pred) -> float:
    if isinstance(pred, dict):
        valor = pred.get("probabilidad", 0.0)
    elif hasattr(pred, "probabilidad"):
        valor = pred.probabilidad
    elif isinstance(pred, (int, float)):
        valor = pred
    else:
        valor = 0.0

    try:
        riesgo = float(valor)
    except (TypeError, ValueError):
        return 0.0

    return riesgo / 100.0 if riesgo > 1 else riesgo


def generar_recomendaciones(respuestas: dict, pred) -> list:
    """
    Genera un Plan de Acción fácil de entender para dueños de MYPEs,
    combinando respuestas específicas y la probabilidad global del modelo.
    """
    recomendaciones = []
    riesgo = _extraer_probabilidad(pred)
    respuestas = respuestas or {}

    def _texto(clave: str) -> str:
        return str(respuestas.get(clave) or "")

    # 1. Informalidad (var_1)
    personeria = _texto("var_1_personeria_juridica")
    if "Ninguna" in personeria or "Sin RUC" in personeria:
        recomendaciones.append({
            "id": "rec_formalizacion",
            "titulo": "Saca tu RUC para trabajar tranquilo",
            "detalle": "Si vendes sin estar registrado, la SUNAT te puede multar o decomisar tu mercadería. Además, con RUC podrás pedir préstamos para hacer crecer tu negocio.",
            "prioridad": "alta",
            "completada": False,
        })

    # 2. Problemas con SUNAT en el pasado (var_12)
    auditoria = _texto("var_12_resultado_auditoria")
    if "reparos, inconsistencias o multas" in auditoria:
        recomendaciones.append({
            "id": "rec_auditoria",
            "titulo": "Revisa tus cuentas con un contador de confianza",
            "detalle": "Como en el pasado tuviste multas u observaciones de la SUNAT, es muy probable que vuelvan a revisar tu negocio pronto. Pídele a un contador que revise que todo esté al día.",
            "prioridad": "alta",
            "completada": False,
        })

    # 3. Exceso de cobros en efectivo (var_7)
    efectivo = _texto("var_7_porcentaje_efectivo")
    if "61% a 100%" in efectivo:
        recomendaciones.append({
            "id": "rec_bancarizacion",
            "titulo": "Cobra más por Yape, Plin o tarjeta",
            "detalle": "Cobrar casi todo en efectivo hace sospechar a la SUNAT de que no estás anotando todas tus ventas. Usar transferencias o POS te protegerá de revisiones.",
            "prioridad": "media",
            "completada": False,
        })

    # 4. Retrasos en fechas de pago/declaración (var_13)
    mora = _texto("var_13_dias_mora")
    if "16 a 30" in mora or "Más de 30" in mora:
        recomendaciones.append({
            "id": "rec_calendario",
            "titulo": "Pon alarmas para declarar a tiempo",
            "detalle": "Olvidar presentar tus declaraciones a fin de mes te hace perder dinero en multas e intereses. Pon recordatorios en tu celular unos días antes del vencimiento.",
            "prioridad": "alta",
            "completada": False,
        })

    # 5. Muchas correcciones en declaraciones (var_14)
    rectificatorias = _texto("var_14_rectificatorias")
    if "3 a 5" in rectificatorias or "Más de 5" in rectificatorias:
        recomendaciones.append({
            "id": "rec_rectificatorias",
            "titulo": "Revisa bien tus ventas y compras antes de enviar",
            "detalle": "Corregir tus declaraciones muchas veces seguidas hace pensar a la SUNAT que hay desorden en tu negocio. Pide a tu contador que revise bien las facturas antes de enviarlas.",
            "prioridad": "media",
            "completada": False,
        })

    # 6. Alta dependencia de proveedores nuevos (var_10)
    proveedores = _texto("var_10_proveedores_nuevos")
    if "Más del 60%" in proveedores:
        recomendaciones.append({
            "id": "rec_proveedores",
            "titulo": "Verifica que tus proveedores sean legales",
            "detalle": "Si compras a empresas recién creadas o no formales, la SUNAT podría anular tus compras y cobrarte más impuestos. Consulta si su RUC está activo en la web de SUNAT antes de pagarles.",
            "prioridad": "media",
            "completada": False,
        })

    # 7. Respaldo alineado con los umbrales de modelo_riesgo.py (0.33 / 0.66)
    if not recomendaciones:
        if riesgo >= 0.66:
            recomendaciones.append({
                "id": "rec_riesgo_alto_general",
                "titulo": "Asesórate: Tus gastos e ingresos no guardan equilibrio",
                "detalle": "El sistema detectó que la relación entre lo que gastas y lo que declaras que ganas genera sospechas de evasión ante la SUNAT. Habla con un contador para ordenar tus comprobantes.",
                "prioridad": "alta",
                "completada": False,
            })
        elif riesgo >= 0.33:
            recomendaciones.append({
                "id": "rec_riesgo_medio_general",
                "titulo": "Mantén tus comprobantes al día",
                "detalle": "Tu negocio está en un rango de riesgo moderado. Procura guardar todas las boletas de lo que vendes y las facturas de lo que compras para sustentar tus números.",
                "prioridad": "media",
                "completada": False,
            })
        else:
            recomendaciones.append({
                "id": "rec_excelencia",
                "titulo": "¡Excelente trabajo! Sigue así",
                "detalle": "Tus números se ven muy ordenados y transparentes. Sigue declarando a tiempo para mantener tu negocio libre de multas y problemas con la SUNAT.",
                "prioridad": "baja",
                "completada": False,
            })

    return recomendaciones