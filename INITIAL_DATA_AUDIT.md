# INITIAL DATA AUDIT



## 1. Executive summary

Auditoría completa de 6,362,620 transacciones; 8,213 fraudes (0.129082%). No se entrenaron modelos ni se realizaron pruebas formales de drift.

## 2. Ubicación y tamaño

`.\PS_20174392719_1491204439457_log.csv` — 493,534,783 bytes (470.67 MiB). Original intacto; única copia. Fecha UTC: 2026-10-04T02:34:30.364593+00:00.

## 3. Dimensiones

6,362,620 filas × 11 columnas. Memoria aproximada de celdas como strings: 3.588 GiB. Suma estimada de objetos string y referencias de celdas; excluye overhead de contenedores. Procesamiento streaming; no es RSS.

## 4. Schema completo

Tipos inferidos sobre todo el archivo, no dtypes de un DataFrame. Nombres exactos:



| Columna | Tipo inferido | Nulos | % nulos |

|---|---|---:|---:|

| step | integer | 0 | 0.000000 |

| type | string | 0 | 0.000000 |

| amount | float | 0 | 0.000000 |

| nameOrig | string | 0 | 0.000000 |

| oldbalanceOrg | float | 0 | 0.000000 |

| newbalanceOrig | float | 0 | 0.000000 |

| nameDest | string | 0 | 0.000000 |

| oldbalanceDest | float | 0 | 0.000000 |

| newbalanceDest | float | 0 | 0.000000 |

| isFraud | integer | 0 | 0.000000 |

| isFlaggedFraud | integer | 0 | 0.000000 |



## 5. Calidad de datos

Columnas faltantes: []. Duplicados exactos: 0. Igualdad exacta de todos los valores de campos CSV (texto decodificado), sin normalización; filas repetidas después de la primera.

Validaciones: `{"target_binary": true, "step_valid": true, "overlap_steps": 0, "exhaustive": true}`. Anomalías básicas: `{}`.

Step global: 1.0–743.0; 743 valores únicos. Entidades únicas exactas: {'origins': 6353307, 'destinations': 2722362}. No se limpió ni transformó el CSV.

## 6. Distribución del target

isFraud: {'0': 6354407, '1': 8213}. isFlaggedFraud: {'0': 6362604, '1': 16}.

## 7. Desbalance de clases

Fraudes: 8,213 (0.129082%); no fraude: 6,354,407 (99.870918%). El desbalance exige evaluar métricas adecuadas en la fase posterior, sin elegir aún umbral ni técnica.

## 8. Distribución por tipo de transacción



| Tipo | Global n (%) | Reference n (%) | Production n (%) |

|---|---:|---:|---:|

| CASH_IN | 1,399,284 (21.9923%) | 1,271,367 (21.9692%) | 127,917 (22.2236%) |

| CASH_OUT | 2,237,500 (35.1663%) | 2,048,096 (35.3911%) | 189,404 (32.9061%) |

| DEBIT | 41,432 (0.6512%) | 37,116 (0.6414%) | 4,316 (0.7498%) |

| PAYMENT | 2,151,495 (33.8146%) | 1,949,011 (33.6790%) | 202,484 (35.1785%) |

| TRANSFER | 532,909 (8.3756%) | 481,440 (8.3193%) | 51,469 (8.9420%) |

## 9. Reference period: step <= 400

Observaciones: 5,787,030; steps: 400; rango: 1.0–400.0; fraudes: 4,477; tasa: 0.077363%.

Amount (desviación estándar muestral): `{"count": 5787030, "min": 0.0, "max": 92445516.64, "mean": 181350.21195315558, "std": 619137.6819139244}`.

## 10. Production period: step >= 401

Observaciones: 575,590; steps: 343; rango: 401.0–743.0; fraudes: 3,736; tasa: 0.649073%.

Amount (desviación estándar muestral): `{"count": 575590, "min": 0.0, "max": 15415938.31, "mean": 164898.32637890833, "std": 420144.2897557277}`.

## 11. Comparación preliminar reference vs production

Cambio observado en tasa de fraude: 0.571710 puntos porcentuales. Las proporciones de type se comparan en la tabla anterior. Amount global: `{"count": 6362620, "min": 0.0, "max": 92445516.64, "mean": 179861.90354912292, "std": 603858.2314629949}`.

Amount medio: reference 181350.21195315558 frente a production 164898.32637890833; desviación estándar: 619137.6819139244 frente a 420144.2897557277; máximos: 92445516.64 frente a 15415938.31. Comparar cambios en mezcla operativa, frecuencia de fraude y dispersión del monto en una fase posterior; los montos extremos requieren revisión de dominio, no eliminación automática.

Los periodos difieren en duración y volumen; comparar proporciones y no solo conteos. Las diferencias descriptivas no demuestran data drift, concept drift ni model drift. No se calcularon tests estadísticos. No se calcularon cuantiles: los estadísticos básicos son conteo, media, desviación estándar, mínimo y máximo.

## 12. Posibles riesgos de leakage

Los balances nuevos corresponden potencialmente a información posterior a la operación. Sus diferencias y cualquier residual no serían utilizables si el scoring ocurre antes de ejecutar la transferencia. Confirmar el instante de scoring y la disponibilidad real antes de incluirlos. Los identificadores pueden favorecer memorización; no asumir capacidad de generalizar a nuevos clientes. isFlaggedFraud representa una regla/alerta existente: excluirlo de los predictores inicialmente hasta conocer su procedencia, disponibilidad y relación con la etiqueta. isFraud se usa únicamente como target. Todo ajuste, codificación o agregación futura debe aprenderse únicamente del periodo de desarrollo; producción queda reservada. Las agregaciones históricas deben usar exclusivamente eventos anteriores.

## 13. Features sugeridas por la consigna (solo diseño)

- oldbalanceOrg - newbalanceOrig: salida neta; evaluar disponibilidad de balance posterior.
- oldbalanceDest - newbalanceDest: signo negativo para incremento neto; mismo riesgo temporal.
- amount / oldbalanceOrg: intensidad; definir manejo de denominador cero sin convertir infinito en valor arbitrario.
- Merchant por prefijo M de nameDest: verificar semántica antes de usar.
- Codificación de type: vocabulario ajustado solo en desarrollo y manejo de categorías nuevas.
- Indicadores CASH_OUT y TRANSFER: evaluarlos por su relación con la operativa; no asumir causalidad.

## 14. Features adicionales propuestas (solo diseño)

- log1p(amount) para escala asimétrica, previa validación de no negativos.
- Indicadores de balance de origen cero y monto superior al balance previo: disponibilidad previa a scoring.
- Frecuencias y sumas históricas por origen: solo pasado, con control de entidades nuevas.
- Residuales contables respecto de amount: candidatos condicionados a disponibilidad de balances posteriores.
No se generó dataset modelado ni se adoptaron decisiones metodológicas definitivas.

## 15. Estructura del repositorio creada

`data/{raw,processed}`, `notebooks`, `src/fraud_detection`, `scripts`, `tests`, `artifacts`, `reports/{figures,monitoring}`, `app`, `docs`. Carpetas futuras vacías con .gitkeep.

## 16. Archivos creados/modificados

README.md, data/README.md, pyproject.toml, uv.lock, .python-version, .gitignore, src/fraud_detection/{__init__,validation}.py, scripts/audit_data.py, tests/test_validation.py, reports/audit_results.json, INITIAL_DATA_AUDIT.md y .gitkeep. El PDF académico preexistente permanece intacto.

## 17. Tests ejecutados y resultado

Ejecutado: uv run --offline python -m unittest discover -s tests -v. Resultado: 5 tests OK; columnas, target binario, límites/valores inválidos de step y auditoría sintética con duplicados, entidades y segmentación, sin leer el CSV grande.

## 18. Estado Git local

Repositorio local preparado con main y development, sin remoto ni push. Dataset excluido explícitamente; sin versionar el raw. Sin identidad Git preconfigurada: el commit inicial utiliza una identidad técnica local solo en ese comando (Academic project initialization <local@localhost>). Se utiliza safe.directory por comando debido a propiedad del directorio distinta entre usuario y entorno ejecutor, sin modificar configuración global.

## 19. Dependencias instaladas/agregadas

Compatibilidad Python >=3.10; ejecución con Python 3.14.5 fijado en .python-version. Biblioteca estándar exclusivamente (csv, sqlite3, unittest, etc.). uv 0.11.16 utilizado para entorno y lockfile; sin dependencias de modelado. UV_CACHE_DIR apunta a .uv-cache dentro del proyecto por permisos del entorno.

## 20. Problemas encontrados

Conteo de duplicados definido por igualdad textual de campos; representaciones numéricas equivalentes con distinto texto se consideran distintas. Nulos reconocidos como campos vacíos o tokens nan/null/na/n/a, sin transformar datos. No se verificaron semánticas externas ni periodicidad real de step. Estadísticos acumulados en coma flotante tienen error de redondeo. Identificadores únicos son exactos, sin interpretación de personas reales.

## 21. Decisiones que requieren aprobación antes de continuar

Autorizar expresamente una siguiente fase de modelado. Antes de esa fase definir instante de scoring, disponibilidad de balances, política sobre isFlaggedFraud, validación temporal dentro de step <= 400 y tratamiento de ratios con cero. No se continúa automáticamente.



INITIAL DATA AUDIT: COMPLETE
