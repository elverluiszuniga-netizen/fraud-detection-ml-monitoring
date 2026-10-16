# Datos PaySim: adquisición y verificación

Fuente pública verificada: [Synthetic Financial Datasets for Fraud Detection](https://www.kaggle.com/datasets/ealaxi/paysim1), Edgar Lopez-Rojas; la fuente indica CC BY-SA 4.0. Atribución: Lopez-Rojas, Elmir y Axelsson, PaySim, EMSS 2016. No se conectó una cuenta ni se descargaron datos externos durante remediación.

1. Abrir la fuente y obtener `PS_20174392719_1491204439457_log.csv` con Download; Kaggle puede requerir sesión/aceptar condiciones. Descargar manualmente y extraer el ZIP sin reescribir el CSV.
2. Colocar en `data/raw/PS_20174392719_1491204439457_log.csv`. El original local ya se trasladó sin cambiar bytes ni duplicarlo. No versionar raw, ZIP ni matrices.
3. Verificar desde raíz:

```powershell
Get-FileHash data/raw/PS_20174392719_1491204439457_log.csv -Algorithm SHA256
uv run python scripts/verify_delivery.py --raw
```

Esperado: 493,534,783 bytes; SHA256 `16910f90577b0d981bf8ff289714510bb89bc71bff7d3f220f024e287e4eea6b`. Manifest en `data/dataset_manifest.json`. Si difiere, detener reproducción y verificar versión; no actualizar hash automáticamente. Auditoría histórica: 6,362,620 filas, 11 columnas, 8,213 fraudes. Raw excluido por tamaño (~470.67 MiB).

Override opcional: `$env:FRAUD_DATA_PATH = 'data/raw/PS_20174392719_1491204439457_log.csv'` (relativo a raíz), o ruta absoluta. Audit/baselines aceptan `--input`. Input explícito inexistente falla. Fallback legacy en raíz sigue soportado, pero se recomienda data/raw.

Referencia/desarrollo steps 1–400; Train 1–320; Validation 321–400; Production 401–743 observados. Nunca split aleatorio global. CSV pequeños de resultados en `artifacts/` no sustituyen la adquisición original. No se agrega muestra con métricas nuevas.

`data/processed/` contiene matrices locales ignoradas; ver `docs/reproduction.md`. Dashboard/notebooks usan artifacts versionados, no matrices/raw. Champion entregado en `models/`; ver `docs/model_recovery.md`.
