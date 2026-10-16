# Fase 7B — Publicación de evidencia MLflow en DagsHub

Fecha de cierre: 15/10/2026 23:42:39 -05:00, America/Lima.

**Estado final: PUBLICADO Y VERIFICADO.** Los 31 runs históricos se transfirieron y validaron sin reentrenar el champion ni recalcular resultados. Se comprobó lectura sin credenciales de los 31 runs y de los 145 artifacts históricos saneados, comparando sus hashes descargados.

## 1. Cuenta y repositorio DagsHub

Cuenta verificada mediante API autenticada: **elverl**, ID **42361**. Repositorio: [elverl/fraud-detection-ml-monitoring](https://dagshub.com/elverl/fraud-detection-ml-monitoring), ID **125058**, `private=false`, permisos `admin=true`, `push=true`, `pull=true`. La identidad y los permisos se volvieron a comprobar antes de transferir y al finalizar.

Esta identidad DagsHub es independiente de GitHub, donde el proyecto pertenece a `elverluiszuniga-netizen`. No se utilizó la cuenta GitHub anterior ni se hizo ninguna escritura en GitHub durante esta fase.

La credencial se leyó exclusivamente de `DAGSHUB_TOKEN` y se mantuvo en memoria/entorno del proceso. No se imprimió, incluyó en URLs, escribió en manifiestos ni subió como artifact.

## 2. Experimentos y runs

| Evidencia | Local | DagsHub |
|---|---:|---:|
| Runs históricos | 31 | 31 |
| Estado FINISHED | 31 | 31 |
| Experimento con runs | 1 | 1 |
| Parámetros | 477 | 477, idénticos |
| Registros de métricas | 617 | 617, idénticos |
| Relaciones padre-hijo | 22 | 22, reconstruidas |
| Artifacts históricos | 145 | 145, hashes verificados |
| Artifacts adicionales de procedencia | 0 | 2 |

Experimento: **fraud-detection-hyperparameter-optimization**. ID local `1` → ID remoto `0`. El experimento local `Default` (ID `0`) estaba vacío y no se migró; no se confundió su ID con el ID remoto del experimento publicado.

Antes de transferir, la consulta autenticada no encontró experimentos remotos. Después se verificaron exactamente 31 IDs locales únicos en las etiquetas remotas, sin duplicados. Nombres de runs, status, tiempos históricos de inicio/fin y parámetros de evaluación se conservaron.

## 3. URLs verificadas para el profesor

- [Experimento MLflow: los 31 runs](https://dagshub.com/elverl/fraud-detection-ml-monitoring.mlflow/#/experiments/0).
- [Run del champion XGBoost](https://dagshub.com/elverl/fraud-detection-ml-monitoring.mlflow/#/experiments/0/runs/2adae7bc49f14c12a24fb18c2c87b60a).
- [Descarga del champion nativo XGBoost.ubj](https://dagshub.com/elverl/fraud-detection-ml-monitoring.mlflow/api/2.0/mlflow-artifacts/artifacts/b933bccddbcf403b8fc54a9adcc4a888/2adae7bc49f14c12a24fb18c2c87b60a/artifacts/model/XGBoost.ubj).
- [Manifiesto público de IDs y estado de migración](https://dagshub.com/elverl/fraud-detection-ml-monitoring.mlflow/api/2.0/mlflow-artifacts/artifacts/b933bccddbcf403b8fc54a9adcc4a888/2adae7bc49f14c12a24fb18c2c87b60a/artifacts/publication/migration_manifest.json).
- [Manifiesto público de artifacts y hashes originales/publicables](https://dagshub.com/elverl/fraud-detection-ml-monitoring.mlflow/api/2.0/mlflow-artifacts/artifacts/b933bccddbcf403b8fc54a9adcc4a888/2adae7bc49f14c12a24fb18c2c87b60a/artifacts/publication/artifact_manifest.json).

Se utilizó una sesión HTTP nueva sin Authorization, cookies, netrc ni credenciales heredadas: consulta de los 31 runs HTTP 200, parámetros y últimas métricas coincidentes, UI MLflow HTTP 200, descarga y SHA256 correctos de los 145 artifacts históricos y los dos manifiestos adicionales. El champion, su manifiesto y lista de features también se descargaron y contrastaron sin autenticación.

**Limitación de navegación:** en este entorno, las páginas generales del repositorio y `/experiments` de DagsHub redirigieron al login y la API general anónima devolvió 403. En cambio, los enlaces directos al tracking `.mlflow` y a sus artifacts fueron accesibles sin token. Para evaluar la evidencia, usar el enlace directo al experimento anterior. Se verificó HTTP/API y descarga real; no se ejecutó una nueva revisión visual en un navegador del profesor.

## 4. Método y compatibilidad

Cliente instalado **MLflow 3.16.1**, servidor remoto **MLflow 3.5.1**, comprobado mediante `/version`. Se usaron APIs estándar de `MlflowClient` con tracking URI explícito `https://dagshub.com/elverl/fraud-detection-ml-monitoring.mlflow`: crear experimento/run, `log_batch`, artifacts, historias de métricas y terminación. No se instaló un exportador, cambió el lock ni modificaron dependencias. La compatibilidad se comprobó con operaciones y lecturas reales, no solo por número de versión.

El origen se leyó directamente con SQLite `mode=ro` y `query_only=ON`; no se conectó un cliente MLflow al store local para evitar migraciones automáticas del esquema. El tracking global del proyecto no se cambió. No se ejecutaron productores de entrenamiento, tuning o monitoring.

Referencias técnicas consultadas: [integración MLflow de DagsHub](https://dagshub.com/docs/integration_guide/mlflow_tracking/), [API/autenticación de DagsHub](https://dagshub.com/docs/api/) y [MlflowClient](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.client.html).

## 5. Validación de métricas, parámetros y linaje

Los 477 pares nombre/valor de parámetros coinciden exactamente por run. Se compararon los 617 registros completos de métricas como multiconjuntos de **nombre, valor, timestamp y step**, antes/después de la transferencia; también se verificaron las últimas métricas y su lectura anónima. Cada clave local tenía un único punto de historia en este store, pero el migrador compara la historia completa y evita duplicarla al reanudar.

Las 22 etiquetas `mlflow.parentRunId` apuntan a los nuevos padres remotos. El ID padre original queda en `migration.source_parent_run_id`. La referencia de metadata `source_model_run_id` también se reconstruyó hacia el champion remoto, conservando el original en `migration.source_model_run_id`.

Las referencias a IDs locales dentro de artifacts históricos se conservan como evidencia; su resolución al destino está en el manifiesto. Los tags de procedencia se escanearon y ninguno necesitó saneamiento de rutas.

## 6. Artifacts publicados y saneamiento

Se inventariaron 145 archivos originales, **15,987,563 bytes**. Se publicaron copias por **15,985,708 bytes**, manteniendo su estructura relativa por run. **135 archivos permanecen idénticos byte a byte y 10 tienen exclusivamente el prefijo absoluto del checkout sustituido por punto.** Se preservaron números, resultados, métricas y modelos.

Copias transformadas:

- `8102e98114514566a47f68945f260aa4/presentation/03_hyperparameter_optimization.ipynb`
- `8102e98114514566a47f68945f260aa4/presentation/PHASE_3_OPTIMIZATION_MLFLOW_REPORT.md`
- `4823399689d0480eac371aa8de02016b/interpretability_summary.json`
- `4823399689d0480eac371aa8de02016b/presentation/04_interpretability.ipynb`
- `4823399689d0480eac371aa8de02016b/presentation/model_interpretability.md`
- `4823399689d0480eac371aa8de02016b/presentation/PHASE_4_INTERPRETABILITY_REPORT.md`
- `c8f4505245614c4e97bd931fb75f4749/monitoring_summary.json`
- `c8f4505245614c4e97bd931fb75f4749/presentation_and_source/05_monitoring.ipynb`
- `c8f4505245614c4e97bd931fb75f4749/presentation_and_source/PHASE_5_MONITORING_REPORT.md`
- `c8f4505245614c4e97bd931fb75f4749/production_monitoring_freeze.json`

`PHASE_7B_DAGSHUB_ARTIFACT_MANIFEST.json` registra para cada archivo ID local, ruta relativa, tamaño/hash original, tamaño/hash publicable y si fue saneado. Se comparó SHA256 tras descarga de los 145 artifacts remotos y nuevamente en acceso anónimo. Los originales locales siguen intactos.

Se añadieron al run del champion `publication/migration_manifest.json` y `publication/artifact_manifest.json`: **147 artifacts remotos en total**, sin crear runs adicionales. Se listó recursivamente cada run y no existen archivos remotos ajenos a esos 145 más los dos manifiestos.

Se publicaron configuraciones, comparaciones, métricas resumidas, listas de features, modelos nativos, informes Markdown/HTML, notebooks de presentación, código histórico, figuras y pequeños CSV de evidencia. No se copiaron el CSV raw de aproximadamente 500 MB, bases MLflow/Optuna, matrices procesadas, secretos ni el entorno virtual. No se incluyeron logs locales de transferencia.

## 7. Champion XGBoost

ID local: `1d353308f1e3427094a221667f3da9de`.

ID remoto: `2adae7bc49f14c12a24fb18c2c87b60a`.

Artifact: `model/XGBoost.ubj`; URI reproducible `runs:/2adae7bc49f14c12a24fb18c2c87b60a/model/XGBoost.ubj`.

SHA256 confirmado por descarga remota anónima: **`44a20bc0e2abbd276ae94790db404248d2ab2c5d01025b00b2e4f935b6f220e4`**. Coincide con el modelo original y la copia GitHub; 77,796 bytes, **14 features, 24 rondas efectivas y threshold 0.5**, sin cambios. Se verificó la carga de la copia nativa sin inferencia sobre Production.

La lista ordenada de features y `model_manifest.json` están junto al modelo y son descargables. También se preservó el modelo LightGBM nativo y su hash mediante la verificación de artifacts.

El origen contiene modelos nativos, no un flavor MLflow con `MLmodel` ni un registro de modelos. Se mantuvo esa representación: **no se creó Model Registry ni deployment**. Para recuperar el champion usar `MlflowClient(tracking_uri=...).download_artifacts(remote_run_id, 'model/XGBoost.ubj', destino)` y después `XGBClassifier.load_model` sobre el archivo descargado. No interpretar el URI `runs:/...` como un paquete flavor inexistente.

## 8. Trazabilidad y reanudación

Manifiesto local duradero: `PHASE_7B_DAGSHUB_RUN_MAPPING.json`; copia pública enlazada arriba. Incluye IDs locales/remotos de experimento y run, padres, estado de verificación y hashes de uploads. El mapeo completo es:

| Run local | Run remoto | Nombre histórico |
|---|---|---|
| `7fa24d6ea79f4b6d8f62a07236a351f9` | `d4f3816369ce4007bdb1f3dbe5c8a35b` | LogisticRegression_baseline_phase2_reference |
| `33845df18b4a48288e116b0027e6b946` | `9afc8a03548b44fc91f9d1d04623ea2b` | RandomForest_baseline_phase2_reference |
| `ac0682a9e54a4f75a3b63cd052a1fdc6` | `db3dbdff9e4c4bfea81f0a777f98a27d` | XGBoost_baseline_phase2_reference |
| `e5b6ee1abaca488095f18010663e5166` | `bd3e9c4ade6a48a69a2b6d76ec6820ff` | LightGBM_baseline_phase2_reference |
| `d18fbdce26b74ebf97073b110eca54c2` | `878a3434d066496b99434ae4fdbc53dd` | XGBoost_optimization |
| `c59c39c3a2c94ac09c84ab4910a6971b` | `75c93c3832ea42d9bc02b2b909470783` | XGBoost_trial_00 |
| `e2ed011b3ba047e7bded7d278c8b0115` | `10be600c8d5a4a8d9f0f1c12b8257caf` | XGBoost_trial_01 |
| `ec2c94b13a2f4c8b9d28731222d400a7` | `52af1a87d7aa48b287b81835a1a6e1b5` | XGBoost_trial_02 |
| `dfeb3a494f8d46a184212798089f23ec` | `0252f4072b4049a189cba11f6a1d8c6b` | XGBoost_trial_03 |
| `023cd1c3521a4affbf7912a1ce58fe09` | `e16762cb7561431a957bf71ee77832d0` | XGBoost_trial_04 |
| `cdeaeffbe978456a93bbf642eeb10b8d` | `e18431d65d944895ae5094dab6f84434` | XGBoost_trial_05 |
| `41f73af9dba14a7d97371b548fa1e4b8` | `45561e60e203423a826c7e2295482f99` | XGBoost_trial_06 |
| `1fbb627a70de438b8aefa60154a1f57d` | `e110513de519433990954d86ddc2f98a` | XGBoost_trial_07 |
| `c11529857b7c4030b5589c588f94008a` | `a8d6705d5e604a5c848da30db6149bcc` | XGBoost_trial_08 |
| `3ee468511a6c4f6fb78bfa8693c82928` | `d2adea6b9a6543fdabced2b8180e9a90` | XGBoost_trial_09 |
| `1d353308f1e3427094a221667f3da9de` | `2adae7bc49f14c12a24fb18c2c87b60a` | XGBoost_best_trial |
| `4e71a938811f4a86a71292cb6adeb669` | `d5ead656455c4357a4a13b62cd637bf7` | LightGBM_optimization |
| `17155e8a4c2449c9a8930b67e397e336` | `5a02b90a33bb45b293626b5ac26a0e19` | LightGBM_trial_00 |
| `54ea51eb9ac44e85af481111bd904cdd` | `b38326c126fc4126af4aae3e9acb146d` | LightGBM_trial_01 |
| `3f5e3df5e3fe418ebff49133ceb1d51d` | `95bb56ae370e47e392758fec1f5345b8` | LightGBM_trial_02 |
| `78eabe4bbf1048c482a7cafd7508b3e9` | `35df3d887fd640c7ab0caac4c6dc1940` | LightGBM_trial_03 |
| `e936815afc094268bf71234ef023100c` | `07b1db054e3946479fd684598ce27688` | LightGBM_trial_04 |
| `d742fd989af24bf3a71a4c0c60b8bba7` | `f045f85059dd4ca2b4eba4c7aa5fbab2` | LightGBM_trial_05 |
| `dbaf47c49bb54324b1028450609ce4d8` | `2b5a1adacd4d431a9a376ec9c9a70fd2` | LightGBM_trial_06 |
| `92a5ca187d1b4fcf92d9c89ffbaa72ad` | `91c0a256f5c5405780d2f2d1db47edbe` | LightGBM_trial_07 |
| `b4afceed25ca464e9ef3c828cc9baf9a` | `02ada6ab586d42829fc1f72d83905d7e` | LightGBM_trial_08 |
| `c17e19d3d4904ab38316ac9e21395984` | `7bcd89754f1c421a8109b7bcad438388` | LightGBM_trial_09 |
| `0b450b60eded4bdab40160bd9d4ce3b1` | `a5eb9dd273a644eb81ee5d163d6e62d8` | LightGBM_best_trial |
| `8102e98114514566a47f68945f260aa4` | `c2c1c8b9980545109145e0bac69282b1` | phase3_comparison_and_provisional_champion |
| `4823399689d0480eac371aa8de02016b` | `23096b117e7c4dda88ec9317091e29e0` | phase4_XGBoost_interpretability |
| `c8f4505245614c4e97bd931fb75f4749` | `361a332f41a44e679ebd70d7ea476603` | phase5_frozen_XGBoost_production_monitoring |

Cada run remoto se creó con `migration.source_run_id`, ID de experimento original y SHA256 del store fuente, permitiendo recuperarlo aunque se perdiera una respuesta. Antes de crear se buscan los IDs existentes; una coincidencia se reutiliza, más de una provoca detención. Un lock local evita dos importadores simultáneos. El manifiesto se guarda mediante reemplazo atómico después de cada operación completada.

Los reintentos automáticos de creación se desactivaron. Parámetros ya presentes deben coincidir; solo se agregan puntos de métricas ausentes según nombre/valor/timestamp/step; los archivos ya registrados se reutilizan y su descarga se valida. Se comprobaron exactamente 31 runs únicos después de reanudar.

## 9. Problemas y diferencias respecto al origen

1. **Consola Windows:** después de terminar el primer run remoto, MLflow intentó imprimir un emoji y produjo `UnicodeEncodeError` en cp1252. Se reanudó con `PYTHONIOENCODING=utf-8`, recuperando los mismos 31 IDs. No hubo duplicación de runs ni métricas; las comprobaciones finales fueron satisfactorias.
2. **IDs nuevos:** experimento `1` local → `0` remoto; los 31 IDs de run cambiaron. Se conservaron IDs originales como tags/manifiestos y se reconstruyeron relaciones.
3. **Metadata del servidor:** tiempo de creación del experimento/objetos e IDs pertenecen a la importación. Los tiempos históricos de cada run, parámetros, valores y timestamps/steps de métricas se conservaron.
4. **Rutas saneadas:** diez copias de artifacts tienen SHA256 distintos por privacidad. Los hashes originales documentados en freezes siguen siendo históricos; usar el manifiesto para distinguir original/copia pública. No se editó la evidencia original para fingir hashes coincidentes.
5. **Acceso web general:** puede requerir sesión DagsHub, aunque tracking y artifacts directos se verificaron anónimamente.
6. **Modelo nativo:** artifact descargable y reproducible, sin flavor/Registry ni servicio desplegado.

## 10. Integridad local y cierre

SHA256 de `mlruns/mlflow.db` antes y después: **`291d310831b6aa3e01f532a386bab62fd0f3b6cc651e5db0de9b853ba32b865d`**. Se comprobó también que los 145 artifacts originales mantienen sus hashes. No se alteraron runs locales, modelos, thresholds, features ni resultados. No se modificó `credit-risk-ml`.

Los archivos de trabajo, scripts reanudables y comprobaciones están en `tmp/dagshub-publication/`, ignorado por Git. Se conservaron fuera de ese temporal el presente informe y ambos manifiestos duraderos. No se hizo commit/push en GitHub, PR, merge, tag o release.

**PUBLICACIÓN DAGSHUB COMPLETADA: 31/31 RUNS VERIFICADOS, 477 PARÁMETROS, 617 MÉTRICAS Y 145 ARTIFACTS HISTÓRICOS MÁS DOS MANIFIESTOS. DETENIDO.**
