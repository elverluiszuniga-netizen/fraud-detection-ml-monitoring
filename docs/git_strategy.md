# Estrategia Git y publicación

Flujo de integración con dos ramas: `development` contiene trabajo local revisable; `main` representa la entrega integrada. No se edita main durante preparación. Commits por alcance (modelado/monitoring, dashboard, entrega) con descripciones del comportamiento y validación. No se reescribe el commit inicial ni las evidencias históricas.

En Fase 7A solo commits locales en development. Raw, matrices, stores MLflow/Optuna, caches, secretos y temporales no se agregan. El champion pequeño se entrega en `models/` como copia byte a byte, junto con manifiesto; las métricas quedan en artifacts CSV/JSON, notebooks y HTML. La consigna PDF se conserva localmente y no se distribuye por defecto.

Fase 7B requiere autorización expresa antes de crear/conectar remoto o servicios. Después de verificar acceso, publicar ambas ramas; abrir PR `development → main`, con problema, cambios, evidencias de tests y limitaciones. Revisar diff, archivos grandes, secretos, modelo/hash y enlaces. La PR debe quedar integrada exitosamente (no simplemente cerrada sin merge). Solo entonces crear tag y release `v1.0.0` sobre el commit de main, con notas y enlaces accesibles a experimentos. No usar los comandos de entrenamiento para generar evidencia remota.

La metadata permanece `0.1.0` durante preparación; cambiar a `1.0.0` y sincronizar lock de metadata en el cierre autorizado, antes del commit final/tag. El borrador de notas está en `docs/release_notes_v1.0.0.md`; no es una release existente. Entrega del curso: último commit al 18/10/2026; mantener la versión enviada estable. `credit-risk-ml` no participa.

Identidad: si no hay nombre/email Git configurados, los commits de preparación usan la misma identidad técnica del commit inicial mediante opciones por comando. No se atribuyen a una identidad humana inventada. Antes de publicación, el usuario puede configurar su identidad para futuros commits. No guardar credenciales en Git ni en URLs remotas. Si el entorno reporta dubious ownership, usar una excepción `safe.directory` limitada al repositorio por comando, evitando cambiar configuración global.
