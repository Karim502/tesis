import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import cuestionario, modelo_riesgo, recomendaciones


class TestConsistenciaServicios(unittest.TestCase):
    @staticmethod
    def _buscar_opcion(pregunta_id: str, subcadena: str) -> str:
        for pregunta in cuestionario.PREGUNTAS_MYPE:
            if pregunta["id"] == pregunta_id:
                for opcion in pregunta["opciones"]:
                    if subcadena in opcion:
                        return opcion
        raise AssertionError(
            f"No se encontró una opción con '{subcadena}' en '{pregunta_id}'."
        )

    def test_todas_las_opciones_estan_mapeadas_en_modelo(self):
        mapas = [
            valor
            for nombre, valor in vars(modelo_riesgo).items()
            if nombre.startswith("MAPA_") and isinstance(valor, dict)
        ]
        self.assertTrue(mapas, "No se encontraron diccionarios MAPA_* en modelo_riesgo.py.")

        claves_mapeadas = set().union(*mapas)
        faltantes = [
            (pregunta["id"], opcion)
            for pregunta in cuestionario.PREGUNTAS_MYPE
            for opcion in pregunta["opciones"]
            if opcion not in claves_mapeadas
        ]
        self.assertEqual(
            faltantes,
            [],
            f"Opciones de cuestionario.py sin mapear en modelo_riesgo.py ({len(faltantes)}): {faltantes}",
        )

    def test_etiquetas_sector_cubre_todos_los_subsectores(self):
        pregunta_sector = next(
            p for p in cuestionario.PREGUNTAS_MYPE if p["id"] == cuestionario.SECTOR_KEY
        )
        faltantes = [
            op for op in pregunta_sector["opciones"] if op not in cuestionario.ETIQUETAS_SECTOR
        ]
        self.assertEqual(
            faltantes,
            [],
            f"Subsectores sin etiqueta en ETIQUETAS_SECTOR: {faltantes}",
        )

    def test_validar_respuestas_rechaza_espacios_en_blanco(self):
        primera_clave = cuestionario.PREGUNTAS_MYPE[0]["id"]
        with self.assertRaises(cuestionario.RespuestasInvalidas) as ctx:
            cuestionario.validar_respuestas({primera_clave: "   "})
        self.assertEqual(ctx.exception.errores.get(primera_clave), "obligatoria")

    def test_todas_las_reglas_de_recomendaciones_se_disparan(self):
        casos = [
            ("var_1_personeria_juridica", "Sin RUC", "rec_formalizacion"),
            ("var_12_resultado_auditoria", "reparos, inconsistencias o multas", "rec_auditoria"),
            ("var_7_porcentaje_efectivo", "61% a 100%", "rec_bancarizacion"),
            ("var_13_dias_mora", "Más de 30", "rec_calendario"),
            ("var_14_rectificatorias", "Más de 5", "rec_rectificatorias"),
            ("var_10_proveedores_nuevos", "Más del 60%", "rec_proveedores"),
        ]
        for pregunta_id, texto, rec_esperada in casos:
            with self.subTest(pregunta=pregunta_id, esperada=rec_esperada):
                opcion_real = self._buscar_opcion(pregunta_id, texto)
                recs = recomendaciones.generar_recomendaciones(
                    {pregunta_id: opcion_real},
                    {"probabilidad": 0.50},
                )
                ids = [r["id"] for r in recs]
                self.assertIn(rec_esperada, ids)

    def test_umbrales_y_valores_nulos_en_recomendaciones(self):
        respuestas_con_nulos = {
            "var_1_personeria_juridica": None,
            "var_7_porcentaje_efectivo": None,
            "var_10_proveedores_nuevos": None,
        }

        rec_alto = recomendaciones.generar_recomendaciones(respuestas_con_nulos, {"probabilidad": 0.66})
        rec_medio = recomendaciones.generar_recomendaciones(respuestas_con_nulos, {"probabilidad": 0.33})
        rec_bajo = recomendaciones.generar_recomendaciones(respuestas_con_nulos, {"probabilidad": 0.32})
        rec_porcentaje = recomendaciones.generar_recomendaciones({}, 75)

        self.assertEqual(rec_alto[0]["id"], "rec_riesgo_alto_general")
        self.assertEqual(rec_medio[0]["id"], "rec_riesgo_medio_general")
        self.assertEqual(rec_bajo[0]["id"], "rec_excelencia")
        self.assertEqual(rec_porcentaje[0]["id"], "rec_riesgo_alto_general")


if __name__ == "__main__":
    unittest.main(verbosity=2)