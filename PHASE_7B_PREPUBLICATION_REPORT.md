# Fase 7B — Saneamiento y preparación local

Fecha: 15 de octubre de 2026, America/Lima. Estado: validación local satisfactoria; publicación del historial actual bloqueada por rutas privadas históricas y entrega DagsHub pendiente.

## 1. Cuenta GitHub verificada

`gh auth status` y `gh api user --jq .login` confirmaron exactamente **elverluiszuniga-netizen**, activa y autenticada mediante keyring. CLI localizado en su instalación estándar; no estaba disponible en PATH de esta sesión. La consulta inicial en sandbox falló por red; la consulta autorizada de solo lectura fuera del sandbox fue satisfactoria. No se utilizó la cuenta anterior `elverl`.

El plan de diagnóstico `PHASE_7B_PUBLICATION_PLAN.md` es histórico: sus comandos dirigidos a `elverl` quedan obsoletos y no deben ejecutarse. No se consultaron repositorios remotos ni DagsHub en esta fase.

## 2. Archivos saneados

Exactamente los 15 identificados en el plan:

- `INITIAL_DATA_AUDIT.md`
- `PHASE_3_OPTIMIZATION_MLFLOW_REPORT.md`
- `PHASE_4_INTERPRETABILITY_REPORT.md`
- `PHASE_5_MONITORING_REPORT.md`
- `PHASE_7_DELIVERY_AUDIT.md`
- `artifacts/interpretability_summary.json`
- `artifacts/monitoring_summary.json`
- `artifacts/phase2_run.json`
- `artifacts/phase3_run.json`
- `artifacts/production_monitoring_freeze.json`
- `docs/model_interpretability.md`
- `notebooks/03_hyperparameter_optimization.ipynb`
- `notebooks/04_interpretability.ipynb`
- `notebooks/05_monitoring.ipynb`
- `reports/audit_results.json`

Transformación exclusiva: prefijo absoluto del checkout sustituido por punto, incluidas representaciones escapadas JSON. Se mantienen los demás bytes, valores numéricos, resultados, métricas y modelos. Son copias de presentación de evidencia histórica, no nuevos resultados. Las rutas antiguas de procedencia no se presentan como configuración ejecutable. El runtime ya resuelve sus recursos desde el proyecto; no se añadieron dependencias absolutas.

Se revisaron también HTML, código, documentación y JSON. Los patrones aparentes en JavaScript minificado de Evidently son expresiones regulares, no rutas; ambos HTML se conservaron sin cambios. El scanner se corrigió para distinguir esos casos de las unidades Windows.

## 3. Evidencias históricas preservadas

Los 15 originales completos permanecen en `private_publication_originals/`, ignorado por Git. `publication_sanitization_manifest.json` registra SHA256 original y publicable por archivo. Se comprobaron todos los hashes de respaldo. No borrar esta carpeta sin conservar un respaldo privado.

El freeze mantiene los hashes originales de fases anteriores. `scripts/verify_delivery.py` comprueba el hash publicable y que el hash original declarado coincida con el freeze, en lugar de modificar silenciosamente la cadena histórica. Esto documenta procedencia; el manifiesto no es una firma criptográfica independiente. Los commits históricos permanecen intactos.

Champion: SHA256 `44a20bc0e2abbd276ae94790db404248d2ab2c5d01025b00b2e4f935b6f220e4`, 14 features, 24 rondas efectivas y threshold 0.5. La suite comprobó carga después de relocalización; el verificador confirmó identidad y evidencia congelada. No se reentrenó, afinó ni reevaluó Production.

## 4. Tests

Suite completa: **59 passed, 4 warnings** (SHAP y SQLAlchemy/MLflow; deprecaciones). Ejecución final fuera del sandbox: 50.51 segundos. Otra ejecución en sandbox también terminó con 59 tests satisfactorios.

La primera invocación encontró tests duplicados de una copia antigua en `tmp/phase7a-clean-checkout`. Se corrigió la recolección mediante `testpaths = ["tests"]` y exclusión de temporales, entorno y originales privados en `pyproject.toml`. No se excluyeron tests de la suite del proyecto. No se alteraron dependencias ni lock.

Comandos reproducibles: `python -m pytest -q -p no:cacheprovider`, `python scripts/verify_delivery.py --notebooks --raw` y `python scripts/validate_publication.py` desde el entorno del proyecto. El último usa Git y Streamlit AppTest y crea una copia en `tmp/`.

## 5. Notebooks

Los cinco ejecutados satisfactoriamente mediante el verificador de entrega: 01 (5 celdas), 02 (6), 03 (6), 04 (5), 05 (6). Se ejecutaron sus celdas Python de presentación de artifacts, sin reescribir outputs ni lanzar entrenamiento. Se repitió la ejecución desde una copia en otra ruta, sin raw, processed ni stores locales. No se afirma ejecución mediante un kernel Jupyter independiente.

## 6. Dashboard y HTML

AppTest: navegación por Resumen ejecutivo, Desempeño del modelo, Datos y drift, Scores y alertas e Investigación de casos; cero excepciones y cero errores Streamlit en las cinco vistas. Verificación final satisfactoria fuera del sandbox. Es validación funcional; no reemplaza revisión visual en navegador.

Los cinco reportes HTML existen y tienen estructura completa. Tamaños: 11,410; 2,112; 94,535; 4,090,362 y 3,731,976 bytes. `load_bundle` validó consistencia de artifacts y las rutas de descarga. No se regeneraron ni modificaron HTML. No se realizó una nueva inspección visual del render de cada reporte.

## 7. Seguridad de archivos y portabilidad

Scanner final del conjunto versionado: cero candidatos de rutas privadas, secretos reconocidos, raw/stores o archivos mayores de 10 MiB. Búsqueda heurística de tokens GitHub, claves AWS y cabeceras de claves privadas; no constituye detección universal de credenciales.

`.gitignore` conserva raw, processed, MLflow, Optuna, entorno y secretos excluidos; se agregaron originales privados y `*.db`. Comprobado `git check-ignore` para CSV original, DB MLflow y respaldo privado. Las DB y el CSV sí pueden existir localmente: se comprobó su exclusión, no se eliminaron. CSV original: 493,534,783 bytes, tamaño y SHA256 contrastados con el manifiesto mediante `--raw`.

Tras el commit de saneamiento: 148 archivos versionados, 16,324,073 bytes. Mayor archivo: HTML Evidently de datos, 4,090,362 bytes. El reporte y plan añadidos posteriormente son texto pequeño.

Auditoría adicional de objetos alcanzables por todas las ramas: 162 blobs, mayor 4,090,362 bytes, cero candidatos de secretos reconocidos y cero raw/stores por nombre. Quince blobs históricos conservan el prefijo del checkout privado; esto confirma el bloqueo de publicación del historial.

Copia en `tmp/publication-portability`: solo contenido versionado y manifiesto, sin raw, matrices procesadas, DB ni stores locales. Validación de artifacts, modelo y cinco notebooks satisfactoria desde esa ruta. Esto prueba entrega de evidencia y presentación; reproducir el entrenamiento completo requiere obtener el dataset documentado.

## 8. Ramas y commits

Trabajo exclusivamente en `development`. Commit de implementación: `c22bd9f` — `Sanitize publication evidence and verify portable artifact copies`. Este reporte y el plan se registran en un segundo commit documental.

`main` permanece exactamente en `4ea3a5fba48b2ba27b7ab4162f82cfbfd9c8baeb`. Sin remotos configurados. No hubo push, creación de repositorio, PR, tag, release, merge ni reescritura de historial.

Git no tenía identidad de autor disponible en este proceso. Se usó exclusivamente para los comandos de commit el identificador verificado `elverluiszuniga-netizen` y su dirección `elverluiszuniga-netizen@users.noreply.github.com`; no se cambió configuración global ni se afirmó verificación del email por GitHub.

`git diff --check` con `core.whitespace=cr-at-eol` satisface la preservación de CRLF de la evidencia, conforme a `.gitattributes`.

## 9. Pendientes de DagsHub

Confirmar cuenta, repositorio y endpoint MLflow reales; vigencia y permisos de credenciales; acceso del evaluador; diseño y prueba del migrador. El diagnóstico histórico documentó 31 runs, 477 parámetros, 617 métricas y 22 relaciones padre-hijo. Estas cantidades no se reauditaron contra DagsHub en esta fase.

La migración debe conservar origen, mapear nuevos IDs, reconstruir relaciones, sanear copias de metadata/artifacts y verificar métricas y hashes descargados. No se instalaron clientes, no se migró ni se utilizaron tokens DagsHub. Faltan URLs reales verificadas para README y entrega.

## 10. Recomendación para publicación

**Conjunto actual saneado y validado localmente; no publicar aún el historial completo.** Los commits previos conservan rutas privadas. Un nuevo commit no las elimina. Antes de cualquier push debe prepararse y autorizarse una estrategia que publique únicamente el snapshot saneado o un historial saneado revisado, preservando los originales privados. Esta fase no reescribe historial ni cambia `main`.

Resolver además DagsHub y acceso del evaluador. Cualquier creación de remoto, push, PR o release requiere una fase expresamente autorizada. Trabajo detenido al finalizar los commits locales y verificaciones de estado.
