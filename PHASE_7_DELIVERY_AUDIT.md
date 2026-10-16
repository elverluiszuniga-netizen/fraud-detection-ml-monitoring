# Fase 7: auditoría integral de cumplimiento y preparación de entrega

Fecha: 12 de octubre de 2026 (America/Lima). Proyecto: `fraud-detection-ml-monitoring`.

## Estado posterior a Fase 7A

**Preparación actual: 90.0%** (26 CUMPLE, 2 PARCIAL, 2 PENDIENTE; `(26 + 2 × 0.5)/30`). Validación local: 59 tests, cinco notebooks, cinco vistas Streamlit, modelo y resultados intactos. Publicación, enlace externo MLflow, PR y release siguen pendientes. [Reporte de remediación](PHASE_7A_REMEDIATION_REPORT.md). La matriz siguiente muestra el estado actual; las secciones de evidencia originales conservan el diagnóstico histórico del 12/10 previo a remediación.

## Diagnóstico ejecutivo original (antes de Fase 7A)

**No está listo para publicar v1.0.0.** La implementación local de entrenamiento, optimización, interpretabilidad y monitoreo tiene evidencia sólida, pero faltan entregables documentales y de publicación obligatorios. El cumplimiento estimado de la lista de control es **66.7%**: 14 CUMPLE, 12 PARCIAL y 4 PENDIENTE, sobre 30 controles. Se asigna 1 a CUMPLE, 0.5 a PARCIAL y 0 a PENDIENTE: `(14 + 12 × 0.5) / 30`. Es una estimación de preparación, **no una nota del curso**; los controles no tienen el mismo peso que los componentes académicos.

Bloqueantes: notebook de preprocesamiento ausente; README final incompleto; evidencia MLflow sin enlace accesible externo; ausencia de repositorio GitHub, PR exitosa y release; estrategia Git sin documentar; reproducción portable del modelo/datos sin resolver. Los avances de fases 2–6 permanecen mayormente sin versionar.

Fuente normativa: `Proyecto Final - Curso MLE3.pdf`, leído completo (cinco páginas). Fecha máxima: **domingo 18 de octubre de 2026**. Exige GitHub versión 1.0.0, README con siete apartados (Model Card opcional), cuatro notebooks, carpeta de datos CSV, app de monitoreo, enlace de experimentos con métricas/parámetros/artifacts y modelo productivo, release con notas, main/development y al menos una PR cerrada exitosamente, documentación Git y HTML/web. DagsHub es sugerido; **el enlace accesible de evidencia sí es obligatorio**. Para reutilizar el repositorio del curso I indica 3.0.0; este proyecto independiente se audita para 1.0.0.

## Alcance y límites de la auditoría

Se revisaron la consigna, `INITIAL_DATA_AUDIT.md` (Fase 1), los cinco reportes PHASE_2 a PHASE_6, README, documentación, notebooks, scripts, módulos, tests, app, cinco HTML, artifacts JSON/CSV, SQLite MLflow y Git. No se identificó un `AGENTS.md` dentro del proyecto mediante el inventario realizado.

No se modificaron código, modelos, thresholds, resultados persistidos ni notebooks. No se ejecutaron pipelines de entrenamiento, optimización, interpretación o evaluación Production. Los tests existentes sí ajustan modelos diminutos con datos sintéticos para probar serialización/SHAP: no reentrenan los modelos del proyecto. La reejecución de notebooks fue en memoria, leyendo artifacts y sin guardar outputs. Se usaron temporales de verificación bajo `tmp/`, excluido de Git. El único entregable nuevo es este diagnóstico.

No hubo push, remoto nuevo, PR, merge, commit, tag, release ni acceso al repositorio `credit-risk-ml`. No se conectaron servicios externos ni se inspeccionaron valores de credenciales de entorno.

## Matriz de cumplimiento

Los números del requisito remiten a la consigna. CUMPLE significa evidencia suficiente en el working tree local; no implica que ya esté publicada. PARCIAL indica evidencia incompleta, dispersa o pendiente de portabilidad/acceso. PENDIENTE significa entregable ausente.

| ID | Requisito / control | Estado | Evidencia concreta | Acción necesaria |
|---|---|---|---|---|
| 01 | Repositorio GitHub entregable (1/2/envío) | PENDIENTE | `git remote -v` vacío; solo repositorio local | Tras autorización, publicar en GitHub y verificar acceso del evaluador |
| 02 | README: problema supervisado y clasificación (1a) | CUMPLE | README problema/objetivo/instante de scoring completos | Mantener formulación académica |
| 03 | README: diagrama de flujo (1a) | CUMPLE | Diagrama Mermaid en README, desde raw hasta dashboard | Verificar render en GitHub tras publicación |
| 04 | README: dataset y diccionario (1b) | CUMPLE | README diccionario semántico de 11 variables; data/README y manifest de adquisición/hash | Descarga manual si no se dispone del raw |
| 05 | README: optimización (1c) | CUMPLE | README TPE, objetivo AP, budgets/early stopping y enlaces al protocolo | Sin reentrenar para publicar |
| 06 | README: resultados offline y online simulados (1e) | CUMPLE | README tablas generadas de CSV verificados, Validation/Production y soporte | Conservar cifras y alcance retrospectivo |
| 07 | README: interpretabilidad global/local (1f) | CUMPLE | README síntesis SHAP global/local, FN y límites | Conservar análisis histórico |
| 08 | README: conclusiones (1g) | CUMPLE | README conclusiones y límites consolidados | Mantener distinción simulación/tiempo real |
| 09 | Notebook de preprocesamiento (2ai) | CUMPLE | 01_preprocessing.ipynb con 5 celdas ejecutadas, calidad/split/features y EDA histórica | Revisar notebook entregado |
| 10 | Notebook de entrenamiento (2aii) | CUMPLE | `02_ml_training.ipynb`: 6/6 celdas ejecutadas, sin errores; reproducción en memoria OK | Mantener enlace y aclarar que los cálculos pesados se ejecutan mediante scripts |
| 11 | Notebook de interpretabilidad (2aiii) | CUMPLE | `04_interpretability.ipynb`: 5/5 celdas; gráficos globales/locales y SHAP; reproducción OK | Conservar artifacts y referencias |
| 12 | Notebook de monitoreo (2aiv) | CUMPLE | `05_monitoring.ipynb`: 6/6 celdas; data/output/performance drift y discusión concept drift; reproducción OK | Mantener explícita la incertidumbre de concept drift |
| 13 | Carpeta de datos CSV (2b) | CUMPLE | Raw intacto en data/raw, ignorado; fuente verificada y manifest SHA256; adquisición documentada | No subir raw; evaluador descarga manualmente |
| 14 | App de monitoreo (2c) | CUMPLE | `app/main.py`, `app/data_access.py`, cinco vistas, seis capturas previas y 11 tests de datos | Conservar guía y alcance offline; confirmar ejecución funcional final antes de release |
| 15 | Optimización avanzada registrada | CUMPLE | Optuna TPE; 20 trials totales y 29 runs Fase 3; búsqueda, parámetros, métricas y comparación | Preservar evidencia sin repetir entrenamiento |
| 16 | Interpretabilidad local/global del algoritmo final | CUMPLE | SHAP exacto en 24 rondas efectivas; plots y CSV; run Fase 4 | Identificar el mismo modelo congelado como modelo de la entrega |
| 17 | MLflow: parámetros y métricas (3a) | CUMPLE | 31 runs FINISHED; trials con 19 params/22 métricas; best runs con 18/22; monitoring con 8/28 | Verificar equivalencia si se trasladan al tracking externo |
| 18 | MLflow: artifacts y modelos (3) | CUMPLE | 145 archivos; todos los runs tienen directorio artifacts; XGBoost.ubj y LightGBM.txt | Conservar modelos nativos, manifests y documentación de carga |
| 19 | Enlace accesible de experimentos (3) | PARCIAL | UI local documentada; DagsHub no conectado; no enlace externo | Tras autorización, transferir evidencia existente y verificar enlace/permisos; DagsHub no es la única opción |
| 20 | Modelo productivo de la simulación (3) | CUMPLE | Champion idéntico de 77,796 bytes en models/ y manifiesto; recuperación/carga portable validada | Publicar copia segura con proyecto tras autorización; enlace MLflow sigue control 19 |
| 21 | Release 1.0.0 y notas (4) | PENDIENTE | Sin tags, remoto o release; metadata pyproject 0.1.0 | Preparar notas/versionado y, solo con autorización, crear release sobre commit final |
| 22 | Ramas main y development (5) | CUMPLE | Ambas locales en `4ea3a5f`; activa development | Tras cierre, publicar ambas ramas respetando estrategia |
| 23 | Al menos una PR cerrada exitosamente (5) | PARCIAL | Ramas existen, pero sin divergencia comprometida, remoto ni evidencia de PR | Commits revisables, PR documentada development → main y merge exitoso autorizado |
| 24 | Documentación estrategia Git (6) | CUMPLE | docs/git_strategy.md y notas de release preparadas; commits locales por alcance | Ejecutar integración/publicación solo en Fase 7B autorizada |
| 25 | Report HTML o web (7) | CUMPLE | Cinco HTML existentes, legibles estructuralmente; tres custom sin recursos remotos de carga | Mantener rutas e instrucciones y verificar apertura visual final |
| 26 | Separación temporal obligatoria | CUMPLE | Train 1–320; Validation 321–400; Production 401–743; tests de límites y filtros | Mantener diseño y modelos actuales |
| 27 | Métricas/drift interpretados correctamente | CUMPLE | AP, ROC, ranking, errores, KS/TV/Holm y PSI; limitaciones y concept drift no concluyente documentados | Trasladar resumen al README sin afirmar ausencia total de drift |
| 28 | Suite completa de tests | CUMPLE | Ejecución final: 57 passed, 4 warnings, 56.19s, fuera del sandbox | Documentar directorio temporal accesible y repetir sobre commit final |
| 29 | Reproducibilidad portable e instrucciones | CUMPLE | paths.py, verificador, descarga raw, modelo versionable; lock/notebooks y copia limpia validables | Instalación nueva/entrenamiento pesado no certificados ni necesarios para revisar entrega |
| 30 | Seguridad e higiene de entrega | CUMPLE | Patrones de secretos sin candidatos; exclusiones probadas; ningún archivo versionable >10 MiB | Repetir scanner y revisión del conjunto final antes de push; no constituye garantía criptográfica |

Model Card, AutoML, tiempo real y despliegue cloud no se cuentan como pendientes obligatorios. `.gitignore`, requirements e instrucciones aparecen como opcionales en la consigna; se auditan también porque afectan una entrega usable. El lockfile existente hace innecesario añadir requirements.txt por defecto.

## Peso académico: interpretación prudente

La rúbrica pesa GitHub 10%, técnicas avanzadas 50%, monitoreo 30% y documentación 10%. No subdivide esos porcentajes por cada evidencia, de modo que no es riguroso presentar 66.7% como calificación ponderada. Técnicas avanzadas y monitoreo están ampliamente implementados localmente; GitHub/publicación están pendientes y documentación está incompleta. Falta de enlace de experimentos o release puede impedir una entrega válida aunque los algoritmos funcionen.

## Evidencia de ejecución y reproducibilidad

### Tests y dependencias

1. `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider`: 45 passed / 12 failed inicialmente (95.14s); los fallos implicaban permisos del TEMP del sandbox. Una segunda invocación con el mismo TEMP reprodujo el problema (22.04s).
2. Con `TEMP` y `TMP` apuntando a `<repo>/tmp`: 55 passed / 2 failed (71.04s). Ambos fallos: XGBoost `weakly_canonical: Access is denied` al cargar un `.ubj` de prueba; tests `test_native_shap_additivity_structure_and_best_round_limit` y `test_fit_early_stopping_and_native_serialization`.
3. Mismo comando fuera del sandbox, con temporales del proyecto: **57 passed, 4 warnings, 56.19s**. El código no fue cambiado. Las cuatro advertencias son tres deprecaciones de SHAP y una de SQLAlchemy/MLflow.
4. `uv sync --locked --offline --dry-run` falló dentro del sandbox al consultar el intérprete (acceso denegado). Fuera del sandbox: **Resolved 200 packages; Checked 165 packages; Would make no changes**. No se instalaron dependencias ni se modificó el lockfile.
5. Python local 3.14.5 coincide con `.python-version`. Sintaxis AST de módulos/scripts/app/tests revisada sin errores. El launcher emite dentro del sandbox una advertencia sobre ubicación real del intérprete; aun así permite las inspecciones Python. No es evidencia de dependencia faltante.

Los tests y el dry-run validan el entorno local, no prueban una instalación nueva sin caché ni un entrenamiento end-to-end desde cero. Estos últimos no se ejecutaron por alcance y prohibición de reentrenar. El README requiere red para paquetes no cacheados y varios GB de memoria/disco. `requires-python >=3.10` no implica que todas las dependencias bloqueadas se hayan probado en 3.10: certificar inicialmente 3.14.5 o ajustar posteriormente la declaración documentada.

### Notebooks y scripts

| Notebook | Celdas code | Ejecución guardada | Reejecución en memoria |
|---|---:|---|---|
| 02_ml_training.ipynb | 6 | 6 ejecutadas, 0 errores | OK |
| 03_hyperparameter_optimization.ipynb | 6 | 6 ejecutadas, 0 errores | OK |
| 04_interpretability.ipynb | 5 | 5 ejecutadas, 0 errores | OK |
| 05_monitoring.ipynb | 6 | 6 ejecutadas, 0 errores | OK |

Los notebooks son presentaciones ejecutables de artifacts, no ejecutan el entrenamiento o SHAP completo. Esta arquitectura evita duplicación; deben enlazar inequívocamente a los scripts que producen la evidencia. La reejecución usa `exec` en memoria, no un kernel Jupyter nuevo ni escritura del ipynb. Falta `01_preprocessing.ipynb` o equivalente.

Scripts auditados: auditoría streaming; baselines/preparación; sanity checks; tuning; SHAP; freeze; monitoring y generadores de reportes. Los generadores **no se ejecutaron**, porque algunos actualizan artifacts/notebooks o agregan archivos a runs MLflow. No invocar comandos de reproducción como si fueran inocuos durante el empaquetado de entrega.

### Integridad del modelo y fases previas

`data/processed/phase3_models/XGBoost.ubj` y la copia MLflow del best run tienen el mismo SHA256:

`44a20bc0e2abbd276ae94790db404248d2ab2c5d01025b00b2e4f935b6f220e4`.

Coincide con `production_monitoring_freeze.json`. El SHA256 actual de `features.py` coincide con `73badebaa186e2fc323fd6c46de784b5002c380dca7ac360a70f7a9a32c0f28a`. Las diez huellas `previous_phase_hashes` del freeze coinciden con los archivos actuales. Threshold **0.5**, 14 features, **24 rondas efectivas**; el archivo guarda 44 rondas por early stopping. No se deben usar todas las rondas accidentalmente al cargar/exponer el modelo.

El freeze registra `model_path` absoluto en `.\...`. `run_monitoring.py` usa `Path(freeze['model_path'])`. Esto bloquea reproducción portable en otra ubicación salvo que se preserve esa ruta o se resuelva el manifiesto/ruta posteriormente sin alterar identidad ni resultados. No es necesario reentrenar para corregir portabilidad.

## MLflow y DagsHub

SQLite se consultó en modo lectura (`mode=ro`), sin crear experimento ni run. Experimento 1: `fraud-detection-hyperparameter-optimization`; 31 runs, todos FINISHED: 29 de Fase 3, uno de interpretabilidad y uno de monitoreo.

| Tipo de run | Evidencia |
|---|---|
| Baseline references | 4 runs, 7 parámetros y 23–24 métricas; referencias importadas de Fase 2 |
| Parents de optimización | 2 runs, 8 parámetros y 2 métricas; agrupación de trials |
| Trials | 20 runs, 19 parámetros y 22 métricas cada uno |
| Best models | 2 runs, 18 parámetros y 22 métricas cada uno; modelos nativos |
| Comparación | 1 run, 0 parámetros y 2 métricas; resumen, no ensayo individual |
| Interpretabilidad | `4823399689d0480eac371aa8de02016b`: 9 parámetros y 4 métricas |
| Monitoring | `c8f4505245614c4e97bd931fb75f4749`: 8 parámetros y 28 métricas |

Todos tienen directorio de artifacts; se inventariaron 145 archivos. Modelos: best XGBoost `1d353308f1e3427094a221667f3da9de`, 77,796 bytes; best LightGBM `0b450b60eded4bdab40160bd9d4ce3b1`, 27,116 bytes. No hay entradas en `registered_models` ni `logged_models`, ni archivo MLmodel: son artifacts nativos con instrucciones de carga, **no modelos empaquetados en flavor MLflow ni Model Registry**. La consigna no obliga Registry; no declarar ese soporte como existente.

`mlruns/`, `mlartifacts/` y modelos locales están ignorados. Un clon de Git por sí solo no tendrá los experimentos ni modelos. `docs/mlflow_dagshub_setup.md` prepara variables de entorno y exige flag de remote tracking, pero **no verifica conexión externa**. `localhost:5000` no permite al evaluador acceder desde su máquina.

El comando documentado para DagsHub ejecuta nuevamente optimización: no debe usarse para cerrar este pendiente con la restricción de no reentrenar. Preparar posteriormente una transferencia de runs/artifacts existentes o un mecanismo equivalente de acceso, verificar permisos y capturar enlace real. No inventar una URL. Mantener historial original local y los modelos congelados; revisar cómo preservar linaje/run IDs o documentar el mapeo si el destino los cambia.

## Dashboard y HTML

La app carga artifacts pequeños, valida schemas/métricas/ventanas y usa caché; no importa MLflow, SHAP, Optuna o modelos para scoring. Cinco vistas: resumen, desempeño, datos/drift, scores/alertas e investigación. Casos SHAP de Validation no se atribuyen a Production. Las métricas AP/ROC/Top-K de múltiples ventanas parciales se muestran no disponibles; no se promedian AUC.

`PHASE_6_DASHBOARD_REPORT.md` aporta QA visual previa con seis capturas reales y descarga HTML comparada byte a byte. En esta auditoría los 11 tests de dashboard están incluidos en los 57 tests. Verificación adicional con `streamlit.testing.v1.AppTest`, fuera del sandbox: arranque y navegación por las cinco opciones del radio lateral, **cero excepciones en todas las vistas**. La primera invocación dentro del sandbox no completó y se interrumpió; la verificación final fuera del sandbox terminó exitosamente. AppTest no sustituye revisión visual en navegador ni descarga real del HTML, y no inicia un servidor público.

| Archivo en reports/monitoring | Bytes | Observación |
|---|---:|---|
| data_drift.html | 11,410 | HTML custom, sin assets remotos de carga |
| prediction_drift.html | 2,112 | HTML custom, sin assets remotos de carga |
| performance_monitoring.html | 94,535 | HTML custom, sin assets remotos de carga |
| evidently_data_drift.html | 4,090,362 | Reporte Evidently, payload local |
| evidently_prediction_drift.html | 3,731,976 | Reporte Evidently, payload local |

Los dos Evidently contienen enlace `https://plotly.com/` (atribución), lo cual no equivale a un recurso remoto necesario para cargar el reporte. Se comprobó estructura/tamaño/rutas, no se hizo una nueva inspección visual exhaustiva de cada HTML. Mantener la distinción custom full-data KS/TV/Holm frente a PSI muestral Evidently (25,000 por período, seed 42).

Ejecución documentada desde raíz:

```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.uv-cache'
uv sync --locked
uv run streamlit run app/main.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Abrir `http://127.0.0.1:8501`. Los cinco HTML se abren localmente o se descargan desde app. La guía explica Ctrl+C y otro puerto si 8501 está ocupado. No se necesita repetir Fase 5 para ver resultados existentes. Online significa aquí evaluación retrospectiva de Production simulada con labels; no servicio en tiempo real.

## Git, archivos grandes y seguridad

Rama activa: `development`. `main` y `development` apuntan a `4ea3a5f` (`Initialize project and complete initial data audit`); diferencia de commits entre ambas: cero. Solo un commit en el historial inspeccionado. No remotos configurados, tags ni evidencia local de PR. No puede descartarse un repositorio externo no conectado, pero no hay evidencia de él y no se afirma su existencia.

Antes de crear este informe: 98 entradas de `git status --porcelain` (incluye directorios agrupados), cuatro tracked modificados (`.gitignore`, README, pyproject, lock) y muchos untracked de fases 2–6. Inventario de archivos candidatos a Git: 132, frente a 23 tracked del commit inicial. Ninguno de los 132 superó 10 MiB. Los archivos HTML más grandes son ~3.9 y ~3.6 MiB. El raw 470.67 MiB está excluido, al igual que matrices, modelos, stores MLflow/Optuna y entorno virtual. `git check-ignore` verificó explícitamente raw, `.env`, matrices, stores y artifacts locales.

Se escanearon los archivos de texto tracked y untracked no ignorados con patrones AWS access keys, tokens GitHub, bloques de private key y asignaciones literales largas de password/api_key/secret/access_token: **sin candidatos**. Se evitó imprimir valores. Es una inspección heurística, no garantiza ausencia universal de secretos, no recorre archivos binarios ni dependencias/entornos ignorados, ni constituye auditoría de vulnerabilidades de paquetes. El commit inicial no tiene ficheros sensibles obvios en su inventario. Repetir revisión del staging final y un scanner especializado antes de publicación.

Las reglas `.gitignore` son suficientemente restrictivas; hay duplicación de `mlartifacts/`, inocua. Evitar ampliar excepciones a todos los artifacts/modelos. El PDF académico es untracked: decidir si debe publicarse; no es exigencia entregar la propia consigna. Las rutas absolutas y datos de entorno en reportes son metadatos locales, no credenciales, pero conviene reducirlos en la documentación final cuando no aporten reproducibilidad.

La excepción `safe.directory` se aplicó por comando para lectura, sin modificar configuración global. El problema de propietario Git es del entorno de ejecución. La identidad histórica técnica `Academic project initialization <local@localhost>` está documentada; definir identidad real para futuros commits, sin reescribir el historial por defecto.

## Inconsistencias y riesgos técnicos/metodológicos

1. **README acumulativo desactualizado:** estructura dice carpetas reservadas; Fase 1 afirma biblioteca estándar y Production reservado; Fase 2 dice no tuning/monitoring; Fase 5 dice no dashboard y Fase 6 no iniciado. Son relatos históricos válidos en reportes de fase, pero confusos en el README vigente. `data/README.md` también habla de carpetas reservadas. Pyproject sigue versión 0.1.0 y descripción de inicialización.
2. **Dataset y diccionario:** schema inferido no reemplaza el diccionario semántico requerido. La consigna describe 744 horas, datos observados llegan a 743. No inventar filas/pasos ni nombres con guiones: CSV usa CASH_IN/CASH_OUT. Explicar balances merchants y target/regla existente.
3. **Preprocesamiento no presentado como notebook:** la lógica está implementada y testeada, pero no cumple la forma de entrega exigida. Resolver por presentación reproducible de lógica existente.
4. **Reproducción de evidencia vs pipeline:** notebooks reproducen la lectura de resultados; no prueban reconstrucción desde raw en un clon nuevo. Raw/modelos/store ignorados y sin mecanismo accesible de recuperación. Hashes autenticados y rutas deben conservarse coherentes.
5. **Champion provisional y modelo productivo:** hay modelo académico congelado y evaluación fuera de tiempo, pero la terminología sigue provisional. Aclarar su rol para la entrega sin convertirlo en un modelo bancario aprobado ni cambiar la selección con Production.
6. **Resultados casi perfectos:** regla de vaciado y estructura PaySim dominan. No hay evidencia de leakage directo en pipeline, pero eso no prueba generalización bancaria. Validation reutilizada en tuning/early stopping; resultados tuned no son estimación independiente. Production se usó retrospectivamente y no para escoger otro modelo.
7. **Step como predictor:** incluido en las 14 variables, mientras se excluye del conteo de drift por separación estructural. No es contradicción de código, pero puede confundirse. SHAP registra contribución no nula; extrapolar árboles fuera de Train limita generalización. Documentar sin removerlo ni reentrenar.
8. **Drift:** 12 variables con cambios estadísticos y cero alertas conjuntas bajo criterios predefinidos no significan ausencia de cambios. Tasa de fraude sube de ~0.0774% Reference a ~0.6491% Production y cambia carga de alertas. PSI muestral y pruebas full-data tienen alcances distintos. Concept drift no está establecido; no fabricar una detección para cumplir rúbrica.
9. **Errores y calibración:** Production conserva 13 FN, 12 de monto y saldo origen cero; casos de score 0.499480 siguen por debajo de 0.5. No cambiar threshold para mejorar resultados. Pesos de clase impiden interpretar scores como prevalencia calibrada. AP depende de prevalencia; comparación de AP no prueba superioridad causal.
10. **Disponibilidad operativa:** balances previos y prefijo M asumidos disponibles; saldo posterior/IDs/flag excluidos. Requiere confirmación para deployment real, no cambio del alcance académico.
11. **Publicación y portabilidad:** se perdería casi toda la entrega al compartir solo el commit actual. Datos/modelos/tracking no están en Git; la entrega debe proporcionar referencias verificables sin subir el raw masivo ni secretos. Respaldar los stores existentes antes de cualquier transferencia futura.

## Plan priorizado de cierre (propuesto, no ejecutado)

| Prioridad | Trabajo | Criterio de aceptación | Dependencia / autorización |
|---|---|---|---|
| P0 | Consolidar README y documentación de datos | Siete apartados obligatorios, flujo, diccionario 11 campos, resultados y conclusiones; enlaces relativos válidos; lenguaje de fase vigente | Autorizar cierre documental posterior al diagnóstico |
| P0 | Notebook de preprocesamiento | Ejecutable sin duplicar lógica, split/feature/leakage documentados, outputs verificables; no entrenamiento | Cierre documental/técnico posterior autorizado |
| P0 | Recuperación portable de raw y modelo | Fuente/acceso del CSV y huella; modelo idéntico recuperable con orden de features/24 rondas; rutas independientes de máquina; revisión desde carpeta limpia | Resolver sin cambiar modelos/resultados; acordar distribución de datos/modelo |
| P0 | Evidencia externa MLflow | Runs existentes con métricas/params/artifacts/modelo, enlace real y acceso probado; sin reentrenar; linaje documentado | Autorización separada de conexión/publicación y credenciales del usuario |
| P0 | Estrategia Git y material de release | Documento ramas/commits/PR/release; borrador notas 1.0.0 y checklist; metadata coherente | Preparar localmente tras autorización de cierre |
| P1 | Validación final del conjunto de entrega | Tests pasan, lock válido, notebooks/HTML/app accesibles, enlaces, hashes y scanner revisados sobre contenido final | No pipelines masivos ni cambio de resultados |
| P1 | GitHub, commits y PR | Remoto autorizado; commits incluyen fases completas; main/development publicadas; PR documentada e integrada exitosamente | **Autorización de publicación, push, PR y merge por separado** |
| P1 | Release v1.0.0 | Tag y release sobre main final, notas, evidencias accesibles y enlace Classroom | **Autorización de tag/release/envío** |
| P2 | Limpieza documental limitada | Descripción/versionado, rutas locales innecesarias, advertencias y texto histórico aclarados | No modificar evidencia histórica autenticada sin revisar hashes |

Secuencia: cerrar documentación/notebook → resolver acceso/portabilidad y evidencia MLflow → revisar conjunto final → autorización de publicación → commits/PR/merge → release → entregar enlace. Preparar el cierre antes del 18/10/2026 y evitar cambios posteriores al commit de entrega conforme a consigna. No agregar AutoML, streaming, cloud, Model Card o Registry por defecto.

## Decisión de entrega

**NO PUBLICAR TODAVÍA.** Los pendientes son de formato obligatorio, acceso y empaquetado; no requieren mejorar métricas ni entrenar nuevamente. La implementación local pasó la suite completa de la auditoría. Este cierre describe el estado previo; Fase 7A posterior resolvió pendientes locales según matriz actual, sin publicación.
