# Fase 7A: remediación y preparación local de publicación

Fecha: 12/10/2026, America/Lima. Estado: **PHASE 7A: COMPLETE**. Sin publicación ni modificación de main. Preparación estimada **90.0%**, no nota académica.

## 1. Pendientes originales

Auditoría inicial: 66.7%, 14 CUMPLE / 12 PARCIAL / 4 PENDIENTE. Faltaban preprocesamiento en notebook, README consolidado, procedimiento de datos/modelos portables, estrategia Git y commits del trabajo acumulado; además GitHub, enlace externo MLflow, PR y release. Se leyó íntegramente la auditoría y se revisaron los reportes de fases 1–6, estructura, scripts, notebooks, tests y Git antes de editar.

## 2. Correcciones realizadas

Se cerraron los pendientes locales de documentación, notebook y distribución del champion. Se preservan los resultados de fases anteriores. Los scripts resuelven inputs respecto de la raíz o configuración explícita; no usan las rutas absolutas históricas como configuración activa. La matriz actual está en `PHASE_7_DELIVERY_AUDIT.md`; el diagnóstico original permanece identificado como histórico.

## 3. Notebook nuevo

`notebooks/01_preprocessing.ipynb`: cinco celdas code ejecutadas y outputs persistidos. Describe PaySim/diccionario, calidad, desbalance, EDA por períodos/tipo/monto, split 320/400, engineering y leakage. Lee auditoría y artifacts históricos; reutiliza `engineer_features` y `temporal_masks` en una demostración sintética explícita. No lee raw completo, genera matrices ni entrena. No hay duplicación de pipeline. Los cuatro notebooks previos permanecen byte a byte idénticos.

## 4. README completado

Incluye problema/negocio, diagrama Mermaid, dataset/diccionario de 11 variables, splits, 14 features/leakage, cinco baselines, Optuna y early stopping, tablas generadas de CSV verificados, tracking/modelo, SHAP, data/prediction/performance monitoring, dashboard/HTML, instalación PowerShell, estructura/Git, límites y conclusiones. Explica AP=1/recall=0 del LightGBM tuned a 0.5, Production con 13 FN, cambio de prevalencia y que no existe tiempo real. No se inventaron métricas, enlaces o resultados.

## 5. Cambios de portabilidad

Nuevo `src/fraud_detection/paths.py`: raw mediante `--input`/`FRAUD_DATA_PATH`, `data/raw/` y fallback legacy; overrides inexistentes fallan. Modelo mediante `models/` y fallback original. SQLite actual se resuelve bajo raíz, no por URI del run histórico.

Adaptados audit, baselines, sanity, interpretability, freeze, monitoring y generadores 3/4/5 solo para resolución de rutas. Features, modeling y optimization permanecen intactos. No se invocaron estos productores. El freeze existente no se reescribió; futuras creaciones registrarían ruta relativa. Se mantiene el hash check del modelo y evidencia previa.

Raw trasladado dentro del proyecto a `data/raw/PS_20174392719_1491204439457_log.csv`: 493,534,783 bytes, SHA256 `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`, verificado tras traslado. Fuente pública PaySim verificada; descarga manual y manifest en `data/README.md` y `data/dataset_manifest.json`. No se descargó ni conectó una cuenta. Raw permanece ignorado.

`.gitattributes` desactiva conversión de saltos de línea para preservar hashes de evidencia entre sistemas. Reportes/JSON/notebooks históricos conservan rutas absolutas como procedencia autenticada; no se reemplazan para evitar invalidar resultados. Son metadatos, no dependencias activas del dashboard o verificador.

## 6. Estrategia de recuperación del modelo

`models/XGBoost.ubj`: copia exacta del champion local y del artifact del best run, 77,796 bytes, hash `44a20bc0e2abbd276ae94790db404248d2ab2c5d01025b00b2e4f935b6f220e4`. `models/manifest.json` conserva threshold 0.5, 14 features y 24 rondas efectivas (44 guardadas). Se versiona porque es pequeño; no se requiere LFS ni almacenamiento externo. No se sustituyó/reentrenó ni se volvió a seleccionar modelo con Production.

`docs/model_recovery.md` explica carga nativa, límites de rondas, identidad y recuperación alternativa del artifact local. LightGBM sigue en MLflow local. No hay Registry ni flavor MLflow. Para modelos futuros grandes se describe alternativa autorizada de release asset/store con manifiesto, sin inventar un enlace existente.

## 7. Archivos versionados y excluidos

Se revisó todo el conjunto tracked/untracked no ignorado y el staging. Se versionan código/tests, notebooks, artifacts pequeños, cinco HTML, figuras/capturas, reports de fases, documentos y champion pequeño. Historial acumulado de fases 2–6 queda comprometido localmente.

Se excluyen raw (~470.67 MiB), ZIP, matrices, modelos locales redundantes en data/processed, stores MLflow/Optuna, caches, `.venv`, secretos y temporales. PDF de consigna se conserva local e ignorado, no un entregable del código. No se agregan datasets sintéticos como si fueran resultados reales.

Scanner heurístico sin candidatos en textos versionables: AWS keys, tokens GitHub, private keys y asignaciones literales de secretos. No se imprimieron credenciales. Ningún candidato a Git supera 10 MiB; el modelo entregado es ~76 KiB. Los dos HTML Evidently rondan 3.9/3.6 MiB. La revisión no equivale a auditoría de vulnerabilidades de dependencias ni garantiza detectar cualquier secreto posible.

## 8. Tests ejecutados

Suite completa fuera del sandbox con TEMP/TMP bajo repo: **59 passed, 4 warnings in 39.56s**. Incluye 57 previos y dos nuevos tests de portabilidad: override raw falla de forma explícita, relocación del champion verifica hash, carga nativa, 14 features y 24 rondas. Los tests usan fixtures pequeñas, no reentrenan champion. Warnings: tres SHAP y una SQLAlchemy/MLflow, conocidos.

`uv sync --locked --offline --dry-run`: 200 paquetes resueltos, 165 verificados, **Would make no changes**. No se modificaron dependencias/lock por validación. Descripción pyproject actualizada; versión continúa 0.1.0 hasta cierre autorizado de release. AST de Python sin errores.

## 9. Notebooks reproducidos

`scripts/verify_delivery.py --raw --notebooks` completó cinco notebooks: 01=5, 02=6, 03=6, 04=5, 05=6 celdas; total 28. Ejecución en memoria sin reescribir outputs históricos. El notebook nuevo se ejecutó y guardó por separado antes del commit. No se arrancó kernel Jupyter nuevo; la ejecución usa las celdas artifact-presentation en el entorno Python bloqueado.

## 10. Dashboard y copia limpia verificados

AppTest pasó las cinco vistas sin excepciones. HTML/assets/rutas validados por capa de datos y tests; no nueva inspección visual exhaustiva en navegador. Se conservan las seis capturas QA de Fase 6.

Se exportó el primer commit local a `tmp/phase7a-clean-checkout` y se añadieron los documentos/manifest finales en preparación. Sin raw, matrices ni stores, desde directorio externo se ejecutó el verificador y los cinco notebooks, y AppTest validó nuevamente todas las vistas. Se verificaron hashes históricos desde los bytes recuperados de Git: la configuración de saltos de línea es efectiva. La copia usa el entorno instalado existente; no certifica instalación nueva sin caché, entrenamiento end-to-end o recuperación remota de MLflow.

Hash inventory antes/después confirma cero cambios en artifacts, HTML, figuras, cuatro notebooks previos, reportes 1–6, fuentes features/modeling/optimization y SQLite MLflow. Las diez huellas del freeze coinciden. Champion y threshold intactos.

## 11. Estado Git

Trabajado exclusivamente en development. Primer commit local: `22b49c5`, implementación/evidencia/modelo portable. Segundo commit de cierre agrupa README, datos/manifiesto, auditoría actualizada y este reporte; consultar `git log -2 --oneline` para su ID final, sin autorreferencia del propio documento.

Se usó la identidad técnica histórica por comando (`Academic project initialization <local@localhost>`), dado que no había identidad humana configurada. Sin cambiar configuración global. main continúa en `4ea3a5fba48b2ba27b7ab4162f82cfbfd9c8baeb`; sin remoto, tags, push, PR o merge. El cierre requiere working tree versionable limpio; temporales y datos ignorados no son pendientes de commit. `credit-risk-ml` no se tocó.

## 12. Requisitos todavía pendientes

- Repositorio GitHub publicado y accesible al evaluador.
- Enlace externo real a experimentos con parámetros/métricas/artifacts/modelo. Store MLflow local no basta.
- PR development → main integrada exitosamente y ambas ramas remotas.
- Metadata final y release/tag v1.0.0 con notas sobre commit final autorizado.

DagsHub no conectado; es sugerido, no obligatorio como proveedor. El enlace accesible sí es requisito. Registry, Model Card, AutoML, cloud y streaming no son pendientes obligatorios ni se implementaron.

## 13. Porcentaje actualizado

**90.0%**: 26 CUMPLE + 2 PARCIAL × 0.5, sobre 30 controles. Parciales: enlace externo MLflow y PR; pendientes: GitHub y release. Los demás controles tienen evidencia local cerrada. Es preparación de checklist, no calificación con pesos 10/50/30/10. Publicación aún no puede declararse completa.

## 14. Intervención manual o credenciales

Usuario debe autorizar publicación/servicios, elegir GitHub/repositorio y proveedor de tracking, proporcionar acceso mediante mecanismos seguros y verificar visibilidad del evaluador. Descarga raw puede requerir sesión Kaggle; no automatizar credenciales dentro de Git. Definir identidad Git humana para commits futuros si corresponde. No exponer tokens ni copiar bases locales a GitHub para simular un enlace MLflow.

## 15. Plan concreto Fase 7B

1. Obtener autorización separada para GitHub/push/PR/merge y para tracking externo; verificar nombres/URLs reales y acceso.
2. Respaldar stores MLflow originales; preparar transferencia de los 31 runs existentes y artifacts pequeños/modelos, sin raw ni full scores, documentando IDs/linaje. No ejecutar optimización para publicarlos.
3. Verificar parámetros/métricas/artifacts/modelo en destino y obtener enlace accesible; completar enlaces README/notas.
4. Cambiar metadata a 1.0.0, actualizar lock de metadata y verificar contenido final, tests, notebooks, dashboard, seguridad y hashes. Crear commit final en development.
5. Publicar ramas autorizadas, abrir PR documentada, revisar diff e integrar exitosamente en main.
6. Solo tras autorización de tag/release, crear v1.0.0 sobre main final, completar notas y verificar enlace de entrega. Entrega máxima 18/10/2026; mantener commit entregado estable.

No ejecutar estos pasos durante Fase 7A. No hay impedimento material para la preparación local; los pendientes externos quedan explícitamente separados.

PHASE 7A: COMPLETE
