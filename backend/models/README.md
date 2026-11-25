# Modelo para la explicabilidad SHAP

Copia aquí tu `modelo_ganador.joblib` (o apunta a otra ruta con `MODELO_PATH` en `.env`).

- Es un archivo de **confianza**: joblib/pickle ejecuta código al cargarlo. Despliégalo tú; nunca aceptes uno subido por usuarios.
- No lo subas a Git (ya está en `.gitignore`).
- Si tu modelo no es binario con la clase de riesgo = `1`, define `MODELO_CLASE_RIESGO` en `.env`.
- Si tu entrenamiento transformó las variables de otra forma, adapta `app/services/features.py`.
