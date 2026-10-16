# Recuperación del champion congelado

Modelo académico de producción simulada: el mismo XGBoost seleccionado en Fase 3 y congelado antes de Production. Archivo entregado: `models/XGBoost.ubj`, 77,796 bytes, SHA256 `44a20bc0e2abbd276ae94790db404248d2ab2c5d01025b00b2e4f935b6f220e4`. No es un nuevo modelo ni un deployment real. No necesita Git LFS por su tamaño.

`models/manifest.json` contiene run fuente, parámetros históricos, orden de 14 features, threshold 0.5 y 24 rondas efectivas. La copia original local en `data/processed/phase3_models/` sigue intacta y excluida. Resolver usa primero `models/`, luego el artifact local. Se verifica hash antes de usarlo en monitoring; no se usa el `model_path` absoluto del freeze histórico como configuración.

```powershell
uv run python scripts/verify_delivery.py
Get-FileHash models/XGBoost.ubj -Algorithm SHA256
```

Carga nativa, sin entrenamiento:

```python
from pathlib import Path
from xgboost import XGBClassifier
model = XGBClassifier()
model.load_model(Path('models/XGBoost.ubj'))  # ejecutar desde raíz
assert model.best_iteration + 1 == 24
# predict_proba de sklearn respeta best_iteration; no usar las 44 rondas guardadas.
```

Construir features solo con `engineer_features` y `MODEL_COLUMNS` existentes. Las probabilidades ponderadas no están calibradas. El dashboard usa resultados persistidos y no necesita cargar el modelo. LightGBM permanece recuperable en artifacts MLflow locales, pero no es el champion de entrega.

Si faltara la copia del repositorio, recuperar el `.ubj` del best run `1d353308f1e3427094a221667f3da9de` en el store original `mlartifacts/<run>/artifacts/model/`, verificar hash y restaurarlo en `models/`. No reentrenar como sustitución. Si un modelo futuro excede límites de Git, acordar un release asset o store autorizado con manifiesto/hash y procedimiento de descarga; no hay enlace externo creado para ello.
