# Guía de usuario del dashboard de monitoreo

## Instalación y ejecución local en PowerShell

Desde la raíz de fraud-detection-ml-monitoring:

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.uv-cache'
uv sync --locked
uv run streamlit run app/main.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Abra http://127.0.0.1:8501 en el navegador de este mismo equipo. Mantenga la terminal abierta; Ctrl+C detiene la aplicación. Si el puerto ya está ocupado, use otro con --server.port y abra esa dirección. No hay despliegue cloud ni servicio público. La primera sincronización necesita conexión si las dependencias no están cacheadas; las siguientes pueden usar uv sync --locked --offline.

## Navegación

- Resumen ejecutivo: volumen, fraudes, prevalencia, AP, Precision, Recall y alertas; comparación global Validation/Production, perfil temporal y hallazgos de drift.
- Desempeño del modelo: matriz de confusión, F1/F2, AP/ROC, ventanas, Top-K observado, máximo teórico y falsos negativos. Threshold 0.5 es referencia congelada, no threshold final.
- Datos y drift: variables, magnitudes, p-values ajustados, estado estadístico y criterios conjuntos. Detalle por variable y diagnósticos dentro de cada tipo de transacción.
- Scores y alertas: figura de distribución persistida, percentiles interactivos y tasas de alerta globales; evolución de alertas/fraudes por step para la selección.
- Investigación de casos: índices anónimos de casos exportados por Fase 5; selección de período, categoría y transacción. SHAP de Validation se consulta aparte y no se atribuye a Production.

Los gráficos Plotly permiten hover, zoom y descarga de figura. Las tablas permiten búsqueda, ocultar columnas y descarga CSV mediante sus controles. Es preferible un navegador de escritorio ancho para las tablas; en pantallas pequeñas colapse la barra lateral y use desplazamiento horizontal cuando corresponda.

## Filtros temporales y alcance de las métricas

La barra lateral selecciona ventanas completas de Production. La selección inicial abarca todo el período; no es una selección arbitraria de horas parciales. Pueden elegirse ventanas no contiguas. Las curvas por step no conectan los tramos omitidos.

Los conteos y la matriz de confusión se suman exactamente. Prevalencia, alert rate, Precision, Recall, F1 y F2 se derivan de esos conteos, no de medias simples de las métricas de ventanas. Si hay una sola ventana, AP/ROC y Top-K vienen de su fila persistida; si se seleccionan todas, vienen del resultado global Production. Para un subconjunto de varias ventanas no se conservan scores individuales para calcular ranking combinado: AP, ROC y Top-K observado se muestran como No disponible. La capacidad máxima teórica sí se calcula a partir del volumen y fraudes seleccionados. No se inventan resultados ni se hace scoring para llenar esas celdas.

Drift, percentiles/distribución global de scores, comparaciones globales Validation/Production e informes HTML NO cambian con el filtro temporal: cada vista lo señala expresamente. Validation de investigación de casos tampoco usa el filtro de Production. El número de casos mostrado cuenta las filas exportadas de la categoría, no todos los fraudes del dataset; una transacción puede aparecer en varias categorías.

## Fuentes de cada KPI y figura

| Resultado mostrado | Fuente persistida |
|---|---|
| AP, ROC, Precision, Recall, F1, F2, TP/FP/TN/FN de períodos completos | artifacts/production_model_comparison.csv |
| Volumen, fraudes, prevalencia y alert rate global | comparison CSV y artifacts/monitoring_summary.json, verificados entre sí |
| Métricas de ventana y agregación por selección | artifacts/monitoring_windows.csv; derivación solo desde conteos |
| Top-K observado y capacidad revisada | comparison CSV o fila individual de ventana |
| Máximo teórico de recall a Top-K | min(1, ceil(volumen * fracción) / fraudes), usando fracciones de artifacts/production_monitoring_freeze.json |
| Drift por variable, p-values y magnitud | artifacts/data_drift_features.csv |
| Diagnóstico dentro de tipo | artifacts/type_conditioned_drift.csv |
| Percentiles y scores globales | artifacts/monitoring_scores.csv |
| Figura de distribución de scores | reports/figures/monitoring/score_distributions.png |
| Volumen, alertas y fraudes por step | artifacts/production_step_profile.csv |
| Casos anónimos y valores reales | artifacts/monitoring_atypical_cases.csv |
| SHAP existente de Validation | artifacts/local_explanations.csv y waterfalls de reports/figures/interpretability/ |
| Identidad, configuración y alcance del modelo | artifacts/production_monitoring_freeze.json y monitoring_summary.json |

La capa de acceso valida schemas, períodos, matriz de confusión, derivaciones, consistencia CSV/JSON, Top-K, reconstrucción por ventanas, perfil temporal, estado drift y predicción de casos. Un archivo esencial ausente o inconsistente detiene los KPIs con un mensaje claro; no se sustituye por ceros ni por datos sintéticos. No se abre el modelo ni el CSV raw en la aplicación.

## Informes HTML

El panel al final de cada vista descarga los cinco archivos reales de reports/monitoring: data_drift.html, prediction_drift.html, performance_monitoring.html, evidently_data_drift.html y evidently_prediction_drift.html. Son informes globales de Fase 5, independientes del filtro. Abra el archivo descargado localmente, sin servidor. Los dos de Evidently usan PSI en muestras; no deben confundirse con las decisiones primarias de datos completos. La app no duplica los informes en otra carpeta ni publica archivos a terceros. Cada reporte ausente muestra su aviso específico.

## Actualización y caché

El dashboard es lectura de artifacts, no monitoreo en tiempo real. Al navegar no ejecuta entrenamiento, Optuna, scoring, SHAP, MLflow ni Evidently. st.cache_data almacena lecturas del bundle, HTML y SHAP de Validation; las firmas de tamaño/mtime invalidan la caché ante cambios. Releer artifacts permite limpiar esas lecturas sin ejecutar el pipeline.

Para actualizar resultados se ejecuta explícitamente el pipeline autorizado de Fase 5 fuera de la app, manteniendo modelo/threshold congelados. Los comandos se documentan en PHASE_5_MONITORING_REPORT.md. No necesita repetirse el pipeline para iniciar la aplicación, navegar, aplicar filtros ni generar el reporte de Fase 6. No actualice KPIs manualmente: restaure o regenere exports coherentes si el validador informa una inconsistencia. No se imprimen tokens ni se necesita DagsHub remoto.

## Interpretación y limitaciones

Diferencia estadística no equivale a drift material. Las reglas conjuntas fijadas en Fase 5 combinan Holm p<0.05 con KS D≥0.10 o TV≥0.05. step es separación temporal estructural y queda fuera del conteo de alertas. Cero variables que superan criterios conjuntos NO significa ausencia de cambios; rareza del fraude, carga de alertas y magnitudes pequeñas pueden ser operativamente importantes. PSI usa otra metodología y umbral de revisión 0.20.

Prediction drift no prueba concept drift. El artifact establece: Concept drift not conclusively established. AP depende de prevalencia; Top0.1% puede capturar solo una fracción de fraudes cuando la capacidad de revisión es menor que su cantidad. No se selecciona threshold desde Production, ni se cambia champion, ni se calibran scores.

PaySim es producción simulada offline con relaciones casi determinísticas. Los scores del modelo ponderado no están calibrados; las etiquetas son retrospectivas. No hay incidentes en vivo, timestamps fabricados, alertas inventadas, streaming, servicio de scoring ni conexión a un banco. Las explicaciones SHAP explican contribuciones del modelo, no causalidad. No existen explicaciones SHAP de Production en los exports actuales.

## Verificación

```powershell
uv run python -m pytest -q
```

Las pruebas no lanzan el servidor Streamlit ni cargan el dataset raw. La verificación visual se realiza por separado ejecutando la app local, navegando por las cinco vistas, seleccionando una ventana y ventanas no contiguas y probando descargas. Capturas y resultados están en PHASE_6_DASHBOARD_REPORT.md.

[Streamlit caching](https://docs.streamlit.io/develop/concepts/architecture/caching), [Plotly en Streamlit](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart).

## Entrega portable

Tras obtener el repositorio completo, instalar con `uv sync --locked` y ejecutar desde raíz. No se requiere raw ni store MLflow: artifacts, figuras y cinco HTML están versionados. `python scripts/verify_delivery.py` valida dependencias de presentación. Ver docs/reproduction.md para PowerShell/TEMP. El dashboard es producción simulada retrospectiva, sin servicio online.
