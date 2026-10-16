# Phase 4 Interpretability Report

## Executive summary

SHAP identifica vaciado aproximado como feature dominante; el modelo también detecta 15/16 fraudes fuera de regla. Se explica el único FN y se documenta ausencia de FP. Modelo, matrices y métricas previas preservados. Production reservado.

# Interpretabilidad del modelo XGBoost

## Objetivo modelo y período
Explicar global y localmente el champion provisional XGBoost tuned de Fase 3, sin reentrenar, cambiar features, seleccionar threshold ni leer Production. Solo se abren validation_X.npy y validation_y.npy, correspondientes a steps 321–400: 1,398,242 filas y 868 fraudes. No se abre el CSV raw ni matrices Train. Las métricas recargadas reproducen exactamente Fase 3: AP 0.999918590, TP 867, TN 1,397,374, FN 1, FP 0.

Modelo fuente: `.\data\processed\phase3_models\XGBoost.ubj`; SHA256 `44a20bc0e2abbd276ae94790db404248d2ab2c5d01025b00b2e4f935b6f220e4`; run fuente `1d353308f1e3427094a221667f3da9de`. El archivo tiene 44 rondas, pero sklearn usa best_iteration+1 = 24. Tree SHAP y gain nativo se calculan exclusivamente con esas 24 rondas; no se modifica el archivo ni se explica accidentalmente el ensemble posterior al mejor punto. Features y matrices de Fase 2 permanecen iguales.

## Metodología y muestra
Tree SHAP exacto nativo de XGBoost, pred_contribs=True, approx_contribs=False, iteration_range=(0,24). Se utiliza SHAP para representar Explanation, beeswarm, bar y waterfall. Método tree-path-dependent: las estadísticas de cobertura de entrenamiento ya guardadas en los árboles definen la referencia; no se crea un background nuevo. Las contribuciones y la base se expresan en log-odds. Sigmoid(base + suma SHAP) reconstruye el score. No son puntos de probabilidad aditivos ni probabilidades calibradas.

Muestra de 2,868 filas: todos los 868 fraudes y 2,000 no fraudes, uniformes sin reemplazo, semilla 42. Su prevalencia es 30.26%, frente a 0.062078% real. No debe confundirse esta muestra enriquecida de explicación con la distribución de Validation. La importancia poblacional se estima ponderando las medias por clase con la prevalencia real; es una estimación basada en 2,000 no fraudes, no SHAP exhaustivo de toda Validation. Casos locales extremos se explican por separado y no se añaden a la muestra global.

Errores máximos de reconstrucción: margen 2.62260437e-06; score 2.38418579e-07. Las pruebas también verifican las rondas efectivas y el slicing de matrices memory-mapped.

## Explicación global e importancia nativa
| feature | mean_abs_shap | mean_abs_shap_fraud | mean_abs_shap_nonfraud | mean_abs_shap_prevalence_weighted | mean_signed_shap_fraud | mean_signed_shap_nonfraud | native_gain | native_split_count | shap_sample_rank | shap_population_estimate_rank | native_gain_rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| orig_balance_emptied | 2.177891 | 6.625342 | 0.247694 | 0.251653 | 6.618984 | -0.247694 | 44566.402344 | 18.000000 | 1 | 1 | 1 |
| amount_to_oldbalanceOrg | 0.387300 | 1.187255 | 0.040120 | 0.040833 | 1.186534 | -0.029473 | 3890.905762 | 40.000000 | 2 | 5 | 3 |
| amount | 0.162184 | 0.423262 | 0.048875 | 0.049108 | 0.421858 | -0.018133 | 462.143860 | 58.000000 | 3 | 3 | 8 |
| oldbalanceDest | 0.116012 | 0.251112 | 0.057378 | 0.057498 | 0.240388 | 0.024583 | 793.911926 | 40.000000 | 4 | 2 | 6 |
| oldbalanceOrg | 0.113520 | 0.277040 | 0.042554 | 0.042699 | 0.266731 | -0.023301 | 679.849670 | 43.000000 | 5 | 4 | 7 |
| type_TRANSFER | 0.077945 | 0.212207 | 0.019675 | 0.019795 | 0.203464 | -0.007291 | 903.499939 | 8.000000 | 6 | 7 | 4 |
| type_CASH_OUT | 0.058412 | 0.101460 | 0.039729 | 0.039768 | -0.017859 | -0.020846 | 216.788086 | 31.000000 | 7 | 6 | 9 |
| step | 0.007054 | 0.008164 | 0.006572 | 0.006573 | -0.007374 | -0.006451 | 13.220498 | 47.000000 | 8 | 8 | 12 |
| dest_is_merchant | 0.004891 | 0.010293 | 0.002547 | 0.002552 | 0.010293 | -0.002198 | 4036.976562 | 1.000000 | 9 | 11 | 2 |
| type_CASH_IN | 0.004273 | 0.007900 | 0.002698 | 0.002701 | 0.007900 | -0.002301 | 809.769836 | 3.000000 | 10 | 10 | 5 |
| orig_balance_zero | 0.003664 | 0.002085 | 0.004349 | 0.004347 | -0.001820 | 0.001676 | 106.221573 | 9.000000 | 11 | 9 | 10 |
| type_PAYMENT | 0.002326 | 0.002667 | 0.002178 | 0.002178 | 0.002667 | -0.002001 | 65.239990 | 1.000000 | 12 | 12 | 11 |
| type_DEBIT | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 13 | 13 | 13 |
| type_UNKNOWN | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 13 | 13 | 13 |

La feature dominante es orig_balance_emptied, seguida de amount_to_oldbalanceOrg y amount. En la muestra enriquecida, el vaciado concentra 69.91% de la suma de mean absolute SHAP; esto no representa porcentaje de varianza explicada ni causalidad. La ponderación por prevalencia mantiene vaciado en primer lugar, pero cambia el orden de las demás variables: revisar ambas columnas/rankings.

Gain nativo resume mejora media de la función objetivo en los splits del ensemble efectivo; split count cuenta frecuencia de uso. Mean absolute SHAP resume magnitud de contribuciones sobre una distribución de explicación concreta. Sus rankings pueden diferir por cobertura, ponderación de clases, correlación entre saldo/monto/ratio/vaciado, interacciones y distribución de la muestra. Ambos identifican vaciado como dominante; no implican efectos causales.

## Dirección dependence e interacciones
Beeswarm y tres dependence plots están en reports/figures/interpretability. Monto y ratio muestran relaciones no lineales; no debe imponerse una relación monotónica a todas las transacciones. Las contribuciones del saldo destino tienden a reducirse al aumentar su valor en esta muestra, pero hay contexto e interacciones. Las variables monetarias se presentan como log1p cuando la escala es grande. El color representa ratio o vaciado según el gráfico; es evidencia descriptiva de dependencia, no efecto causal.

| feature | spearman_value_vs_shap |
| --- | --- |
| step | -0.045929 |
| amount | 0.723860 |
| oldbalanceOrg | 0.386254 |
| oldbalanceDest | -0.864863 |
| amount_to_oldbalanceOrg | 0.122317 |
| orig_balance_zero | 0.746878 |
| orig_balance_emptied | 0.791924 |
| dest_is_merchant | -0.747898 |
| type_CASH_IN | -0.631439 |
| type_CASH_OUT | 0.846292 |
| type_DEBIT | nan |
| type_PAYMENT | -0.748434 |
| type_TRANSFER | 0.665540 |
| type_UNKNOWN | nan |

Los coeficientes Spearman son descriptivos de valor versus contribución dentro de la muestra enriquecida; constantes se dejan vacías. En 128 filas elegidas con semilla 42 se calcularon interaction values; el error máximo de sus sumas marginales es 9.53674316e-07. Se reportan componentes simétricos off-diagonal, sin sumar dos veces ambas posiciones ni interpretar causalidad:

| feature_a | feature_b | mean_abs_pair_component |
| --- | --- | --- |
| amount | oldbalanceOrg | 0.169062 |
| amount | orig_balance_emptied | 0.069262 |
| oldbalanceDest | type_TRANSFER | 0.062086 |
| oldbalanceOrg | orig_balance_emptied | 0.058550 |
| amount | amount_to_oldbalanceOrg | 0.053566 |

La interacción de monto y saldo origen destaca, coherente con las features derivadas del mismo par de variables. La muestra de interacción es pequeña y no ofrece conclusiones poblacionales precisas.

## Regla de vaciado
orig_balance_emptied ocupa rank 1 con mean |SHAP| 2.177891. Si vale 1, la contribución media es +6.746533 log-odds y el score medio en la muestra es 0.974467. Si vale 0, la contribución media es -0.247096, con score medio 0.010702. Son medias de subgrupos de una muestra enriquecida; no estiman un efecto de intervención.

El modelo aprende principalmente la regla de vaciado, pero no exclusivamente. Fraudes detectados con vaciado 0 reciben contribuciones fuertes de monto, saldo origen y ratio. Vaciado se definió antes del scoring como saldo origen positivo y abs(monto - saldo previo) <=0.01, calculado en float64 antes del almacenamiento float32.

## Fraudes fuera de la regla
16 de 868 fraudes (1.843318%) tienen vaciado 0. Detectados 15/16 (93.75%) a threshold de referencia 0.5. Scores entre 0.057349406 y 0.974499404. Los 15 correctamente detectados son TRANSFER de monto 10 millones y saldo previo superior al monto. El restante es CASH_OUT con monto y saldo origen cero. Esto es un patrón observado, no una afirmación sobre el mecanismo generador ni una regla causal.

| feature | mean_abs_shap |
| --- | --- |
| amount | 3.861571 |
| oldbalanceOrg | 3.080130 |
| amount_to_oldbalanceOrg | 0.705125 |
| oldbalanceDest | 0.482755 |
| orig_balance_emptied | 0.172451 |

| validation_row_index | step | amount | oldbalanceOrg | amount_to_oldbalanceOrg | score | prediction_05 |
| --- | --- | --- | --- | --- | --- | --- |
| 644394 | 354.000000 | 10000000.000000 | 19299230.000000 | 0.518155 | 0.967110 | 1 |
| 770843 | 357.000000 | 10000000.000000 | 10653152.000000 | 0.938689 | 0.962584 | 1 |
| 790223 | 359.000000 | 10000000.000000 | 12056779.000000 | 0.829409 | 0.962584 | 1 |
| 799030 | 362.000000 | 10000000.000000 | 17677120.000000 | 0.565703 | 0.967110 | 1 |
| 832362 | 370.000000 | 10000000.000000 | 11653144.000000 | 0.858137 | 0.962584 | 1 |
| 1174717 | 386.000000 | 10000000.000000 | 21975272.000000 | 0.455057 | 0.958965 | 1 |
| 1174719 | 386.000000 | 10000000.000000 | 11975272.000000 | 0.835054 | 0.962584 | 1 |
| 1174917 | 387.000000 | 10000000.000000 | 44892192.000000 | 0.222756 | 0.716314 | 1 |
| 1174919 | 387.000000 | 10000000.000000 | 34892192.000000 | 0.286597 | 0.958965 | 1 |
| 1174921 | 387.000000 | 10000000.000000 | 24892194.000000 | 0.401732 | 0.958965 | 1 |
| 1174923 | 387.000000 | 10000000.000000 | 14892193.000000 | 0.671493 | 0.974499 | 1 |
| 1174926 | 387.000000 | 0.000000 | 0.000000 | 0.000000 | 0.057349 | 0 |
| 1174933 | 387.000000 | 10000000.000000 | 29110884.000000 | 0.343514 | 0.958965 | 1 |
| 1174935 | 387.000000 | 10000000.000000 | 19110884.000000 | 0.523262 | 0.967110 | 1 |
| 1335483 | 398.000000 | 10000000.000000 | 25618180.000000 | 0.390348 | 0.958965 | 1 |
| 1335485 | 398.000000 | 10000000.000000 | 15618180.000000 | 0.640279 | 0.974499 | 1 |

## Explicaciones locales
threshold 0.5 = reference threshold, not final production threshold.

Los casos se eligen de forma determinística: TP de máximo score, TN de mínimo score, FN de mínimo score, FP de máximo score si existe, TP sin vaciado de máximo score y observación más próxima a 0.5. Los empates usan el primer índice Validation. Los índices no son IDs de clientes ni números de fila raw. Cada caso muestra todos los valores y contribuciones firmadas; local_explanations.csv conserva su estructura reutilizable.

### A_high_score_TP

Índice Validation cero-based 30299; step 322; label 1; score 0.979055464; predicción @0.5 1.

La transferencia iguala monto y saldo previo. El vaciado aproximado aporta +6.700 log-odds, reforzado por ratio 1 y monto; esto supera el valor base negativo. Explica el score alto, sin demostrar causalidad.

| feature | feature_value | shap_log_odds | absolute_rank |
| --- | --- | --- | --- |
| orig_balance_emptied | 1.000000 | 6.699925 | 1 |
| amount_to_oldbalanceOrg | 1.000000 | 0.834668 | 2 |
| amount | 2533650.000000 | 0.788530 | 3 |
| oldbalanceOrg | 2533650.000000 | 0.376110 | 4 |
| oldbalanceDest | 0.000000 | 0.308940 | 5 |
| type_TRANSFER | 1.000000 | 0.202108 | 6 |
| type_CASH_OUT | 0.000000 | -0.079543 | 7 |
| step | 322.000000 | -0.022306 | 8 |
| dest_is_merchant | 0.000000 | 0.010895 | 9 |
| type_CASH_IN | 0.000000 | 0.006812 | 10 |
| type_PAYMENT | 0.000000 | 0.001213 | 11 |
| orig_balance_zero | 0.000000 | -0.001203 | 12 |
| type_DEBIT | 0.000000 | 0.000000 | 13 |
| type_UNKNOWN | 0.000000 | 0.000000 | 14 |
### B_low_score_TN

Índice Validation cero-based 300; step 321; label 0; score 0.003583667; predicción @0.5 0.

El ratio 1.022 aporta positivamente, pero no basta: ausencia de CASH_OUT, vaciado 0, destino merchant y PAYMENT aportan negativamente. La base negativa y el patrón operativo mantienen el score bajo.

| feature | feature_value | shap_log_odds | absolute_rank |
| --- | --- | --- | --- |
| amount_to_oldbalanceOrg | 1.021692 | 0.727198 | 1 |
| type_CASH_OUT | 0.000000 | -0.423248 | 2 |
| orig_balance_emptied | 0.000000 | -0.247797 | 3 |
| dest_is_merchant | 1.000000 | -0.215375 | 4 |
| type_PAYMENT | 1.000000 | -0.126941 | 5 |
| oldbalanceDest | 0.000000 | 0.066319 | 6 |
| type_TRANSFER | 0.000000 | -0.053699 | 7 |
| oldbalanceOrg | 13962.219727 | -0.043330 | 8 |
| amount | 14265.089844 | -0.026398 | 9 |
| step | 321.000000 | -0.003344 | 10 |
| type_CASH_IN | 0.000000 | 0.002465 | 11 |
| orig_balance_zero | 0.000000 | -0.002191 | 12 |
| type_DEBIT | 0.000000 | 0.000000 | 13 |
| type_UNKNOWN | 0.000000 | 0.000000 | 14 |
### C_false_negative

Índice Validation cero-based 1174926; step 387; label 1; score 0.057349406; predicción @0.5 0.

CASH_OUT con monto 0, saldo origen 0 y ratio 0 (sentinel de división por cero), sin vaciado. La base es -5.281 log-odds. Monto (+1.326) y CASH_OUT (+1.054) elevan el margen, pero no lo suficiente; vaciado 0 (-0.211) y saldo destino (-0.172) lo reducen. El score 0.057349 queda bajo 0.5. El error no se atribuye únicamente a una contribución negativa: faltan las grandes contribuciones positivas de los patrones habituales. Debe revisarse este caso de monto cero y su semántica de simulación.

| feature | feature_value | shap_log_odds | absolute_rank |
| --- | --- | --- | --- |
| amount | 0.000000 | 1.326206 | 1 |
| type_CASH_OUT | 1.000000 | 1.054326 | 2 |
| step | 387.000000 | 0.274508 | 3 |
| orig_balance_emptied | 0.000000 | -0.211178 | 4 |
| oldbalanceDest | 7970766.500000 | -0.171508 | 5 |
| orig_balance_zero | 1.000000 | 0.114849 | 6 |
| oldbalanceOrg | 0.000000 | 0.099787 | 7 |
| type_TRANSFER | 0.000000 | -0.006229 | 8 |
| amount_to_oldbalanceOrg | 0.000000 | 0.000511 | 9 |
| dest_is_merchant | 0.000000 | 0.000254 | 10 |
| type_CASH_IN | 0.000000 | 0.000238 | 11 |
| type_PAYMENT | 0.000000 | 0.000139 | 12 |
| type_DEBIT | 0.000000 | 0.000000 | 13 |
| type_UNKNOWN | 0.000000 | 0.000000 | 14 |
### D_false_positive

No existe False Positive en Validation a threshold 0.5; no se inventa caso ni waterfall.
### E_non_rule_TP

Índice Validation cero-based 1174923; step 387; label 1; score 0.974499404; predicción @0.5 1.

TRANSFER por 10 millones con saldo previo 14.892 millones, ratio 0.67149 y vaciado 0. Monto (+4.170), saldo origen (+3.425) y ratio (+0.906) superan la base negativa y la pequeña penalización por ausencia de vaciado. El modelo también reconoce un patrón multivariable fuera de la regla principal.

| feature | feature_value | shap_log_odds | absolute_rank |
| --- | --- | --- | --- |
| amount | 10000000.000000 | 4.169511 | 1 |
| oldbalanceOrg | 14892193.000000 | 3.424731 | 2 |
| amount_to_oldbalanceOrg | 0.671493 | 0.906230 | 3 |
| oldbalanceDest | 0.000000 | 0.516696 | 4 |
| orig_balance_emptied | 0.000000 | -0.166041 | 5 |
| type_TRANSFER | 1.000000 | 0.157851 | 6 |
| step | 387.000000 | -0.066291 | 7 |
| type_CASH_OUT | 0.000000 | -0.016875 | 8 |
| orig_balance_zero | 0.000000 | -0.001748 | 9 |
| dest_is_merchant | 0.000000 | 0.000271 | 10 |
| type_CASH_IN | 0.000000 | 0.000228 | 11 |
| type_PAYMENT | 0.000000 | 0.000096 | 12 |
| type_DEBIT | 0.000000 | 0.000000 | 13 |
| type_UNKNOWN | 0.000000 | 0.000000 | 14 |
### F_nearest_reference_threshold

Índice Validation cero-based 1174917; step 387; label 1; score 0.716314316; predicción @0.5 1.

El score más cercano a 0.5 es 0.716314, a distancia 0.216314. Es el caso más próximo disponible, pero no una transacción realmente cercana a 0.5; no se inventa un caso ambiguo. Monto y saldo origen elevan el margen, mientras el ratio 0.222756 y vaciado 0 lo reducen.

| feature | feature_value | shap_log_odds | absolute_rank |
| --- | --- | --- | --- |
| amount | 10000000.000000 | 3.732511 | 1 |
| oldbalanceOrg | 44892192.000000 | 2.515368 | 2 |
| oldbalanceDest | 0.000000 | 0.464323 | 3 |
| amount_to_oldbalanceOrg | 0.222756 | -0.312828 | 4 |
| orig_balance_emptied | 0.000000 | -0.183002 | 5 |
| type_TRANSFER | 1.000000 | 0.157851 | 6 |
| step | 387.000000 | -0.148507 | 7 |
| type_CASH_OUT | 0.000000 | -0.016875 | 8 |
| orig_balance_zero | 0.000000 | -0.001748 | 9 |
| dest_is_merchant | 0.000000 | 0.000271 | 10 |
| type_CASH_IN | 0.000000 | 0.000228 | 11 |
| type_PAYMENT | 0.000000 | 0.000096 | 12 |
| type_DEBIT | 0.000000 | 0.000000 | 13 |
| type_UNKNOWN | 0.000000 | 0.000000 | 14 |

## Consistencia y robustez cualitativa
| group | rows | feature | mean_abs_shap | mean_signed_shap |
| --- | --- | --- | --- | --- |
| confident_correct | 2866 | orig_balance_emptied | 2.179274 | 1.831925 |
| confident_correct | 2866 | amount_to_oldbalanceOrg | 0.387461 | 0.338897 |
| confident_correct | 2866 | amount | 0.160532 | 0.113346 |
| fraud | 868 | orig_balance_emptied | 6.625352 | 6.618995 |
| fraud | 868 | amount_to_oldbalanceOrg | 1.187254 | 1.186533 |
| fraud | 868 | amount | 0.423262 | 0.421858 |
| incorrect_or_mid_score | 2 | amount | 2.529359 | 2.529359 |
| incorrect_or_mid_score | 2 | oldbalanceOrg | 1.307578 | 1.307578 |
| incorrect_or_mid_score | 2 | type_CASH_OUT | 0.535601 | 0.518726 |
| non_rule_fraud | 16 | amount | 3.861571 | 3.861571 |
| non_rule_fraud | 16 | oldbalanceOrg | 3.080130 | 3.080130 |
| non_rule_fraud | 16 | amount_to_oldbalanceOrg | 0.705125 | 0.666021 |
| nonfraud | 2000 | orig_balance_emptied | 0.247693 | -0.247693 |
| nonfraud | 2000 | oldbalanceDest | 0.057377 | 0.024583 |
| nonfraud | 2000 | amount | 0.048876 | -0.018133 |

Fraudes fáciles están dominados por vaciado y ratio; no fraudes tienen base baja y contribuciones predominantemente pequeñas. El grupo fuera de regla tiene peso mayor de monto/saldo. El FN combina señales positivas débiles con ausencia de la señal dominante y mantiene margen negativo. Esto es coherencia interna del modelo, no robustez de generalización probada. Los grupos de score <=0.1 o >=0.9 son diagnósticos fijos de explicación, no nuevos thresholds operativos; solo se usa 0.5 para errores comparables.

## Limitaciones y no causalidad
SHAP explica contribuciones del modelo a sus predicciones; SHAP NO demuestra causalidad. Las features correlacionadas/derivadas pueden repartir contribuciones de forma dependiente del método y del modelo. Tree-path-dependent usa estadísticas de cobertura y no una distribución causal ni un background representativo de producción. La base no equivale a prevalencia global y el entrenamiento usó peso positivo 10. Las medias de muestra enriquecida difieren de las poblacionales estimadas. Solo hay 16 fraudes fuera de regla y un FN; no se extrapolan conclusiones a errores futuros. Los resultados casi perfectos reflejan un simulador; balances previos y prefijos requieren confirmación operacional. Validation fue reutilizada para tuning, de modo que no es un test independiente. Float32 puede redondear montos grandes. No se hacen cambios de features, modelo, calibración o threshold como consecuencia de este análisis.

## Reproducción y referencias
Desde la raíz, en PowerShell:
```powershell
$env:UV_CACHE_DIR = Join-Path $PWD '.uv-cache'
uv sync --locked
uv run python -m pytest -q
uv run python scripts/run_interpretability.py
uv run python scripts/build_phase4_report.py
```
El segundo script regenera presentación y evidencia sin repetir SHAP ni crear un nuevo run. El primero crea un solo run de interpretabilidad por ejecución, manteniendo los históricos.

[SHAP TreeExplainer y semántica raw/path-dependent](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html), [XGBoost contribution prediction y iteration_range](https://xgboost.readthedocs.io/en/stable/prediction.html).


## MLflow tests artifacts y Git
Un solo nuevo run de interpretabilidad: `4823399689d0480eac371aa8de02016b`, estado FINISHED, experimento 1. URI local `sqlite:///./mlruns/mlflow.db`. Metadata de los 29 runs históricos de Fase 3 verificada sin cambios. Se registran importance CSV, casos locales, resumen, CSV de direcciones/grupos/fraudes fuera de regla, figuras y configuración/source; no se suben datasets ni matrices SHAP completas.

Suite existente y nueva:
```
......................................                                   [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\shap\plots\colors\_colors.py:47
  .\.venv\Lib\site-packages\shap\plots\colors\_colors.py:47: PendingDeprecationWarning: The set_bad function will be deprecated in a future version. Use cmap.with_extremes(bad=...) or Colormap(bad=...) instead.
    red_blue.set_bad(gray_rgb.tolist(), 1.0)

.venv\Lib\site-packages\shap\plots\colors\_colors.py:48
  .\.venv\Lib\site-packages\shap\plots\colors\_colors.py:48: PendingDeprecationWarning: The set_over function will be deprecated in a future version. Use cmap.with_extremes(over=...) or Colormap(over=...) instead.
    red_blue.set_over(gray_rgb.tolist(), 1.0)

.venv\Lib\site-packages\shap\plots\colors\_colors.py:49
  .\.venv\Lib\site-packages\shap\plots\colors\_colors.py:49: PendingDeprecationWarning: The set_under function will be deprecated in a future version. Use cmap.with_extremes(under=...) or Colormap(under=...) instead.
    red_blue.set_under(gray_rgb.tolist(), 1.0)  # "under" is incorrectly used instead of "bad" in the scatter plot

tests/test_optimization.py::TrackingTests::test_local_nested_logging
  .\.venv\Lib\site-packages\mlflow\store\tracking\utils\sql_trace_metrics_utils.py:155: SADeprecationWarning: The ``noload`` loader strategy is deprecated and will be removed in a future release.  This option produces incorrect results by returning ``None`` for related items. (deprecated since: 2.1) (This warning originated from the `configure_mappers()` process, which was invoked automatically in response to a user-initiated operation.)
    _SESSION_TRACE_METADATA = aliased(SqlTraceMetadata)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
38 passed, 4 warnings in 7.16s
```
Notebook: 5 celdas de código ejecutadas sin errores. Análisis y logging completados en 9.22 segundos; excluye implementación, instalación y construcción del reporte. Hubo dos reparaciones de exportación (slicing de memmap SHAP y step duplicado); ambas resueltas antes de logging; se corrigió además la lectura UTF-8 del notebook en Windows. Advertencias de deprecación de SHAP/matplotlib y MLflow/SQLAlchemy no bloquean ejecución.

Archivos nuevos: src/fraud_detection/interpretability.py, scripts/run_interpretability.py, scripts/build_phase4_report.py, tests/test_interpretability.py, docs/model_interpretability.md, notebooks/04_interpretability.ipynb, PHASE_4_INTERPRETABILITY_REPORT.md, seis artifacts CSV/JSON pequeños y figuras en reports/figures/interpretability. README actualizado mínimamente; pyproject y uv.lock añaden SHAP; .gitignore permite artifacts pequeños y mantiene matrices/stores ignorados. No se guardan matrices SHAP gigantes ni modelos nuevos. Rama `development`; no commits, push, remoto, merge, tag o release.

```
M .gitignore
 M README.md
 M pyproject.toml
 M uv.lock
?? PHASE_2_MODELING_REPORT.md
?? PHASE_3_OPTIMIZATION_MLFLOW_REPORT.md
?? "Proyecto Final - Curso MLE3.pdf"
?? artifacts/baseline_model_comparison.csv
?? artifacts/development_temporal_profile.csv
?? artifacts/hyperparameter_search_space.json
?? artifacts/interpretability_summary.json
?? artifacts/local_explanations.csv
?? artifacts/non_rule_fraud_explanations.csv
?? artifacts/optimization_trials.csv
?? artifacts/phase2_run.json
?? artifacts/phase3_run.json
?? artifacts/phase3_sanity.json
?? artifacts/sanity_simple_rules.csv
?? artifacts/sanity_univariate_features.csv
?? artifacts/shap_feature_directions.csv
?? artifacts/shap_global_importance.csv
?? artifacts/shap_group_comparison.csv
?? artifacts/tuned_model_comparison.csv
?? docs/feature_catalog.md
?? docs/mlflow_dagshub_setup.md
?? docs/model_interpretability.md
?? docs/perfect_performance_sanity_check.md
?? notebooks/02_ml_training.ipynb
?? notebooks/03_hyperparameter_optimization.ipynb
?? notebooks/04_interpretability.ipynb
?? reports/figures/average_precision_comparison.png
?? reports/figures/confusion_Dummy.png
?? reports/figures/confusion_LightGBM.png
?? reports/figures/confusion_LogisticRegression.png
?? reports/figures/confusion_RandomForest.png
?? reports/figures/confusion_XGBoost.png
?? reports/figures/development_temporal.png
?? reports/figures/interpretability/
?? reports/figures/phase3_confusion_LightGBM.png
?? reports/figures/phase3_confusion_XGBoost.png
?? reports/figures/phase3_optimization_history.png
?? reports/figures/phase3_pr_LightGBM.png
?? reports/figures/phase3_pr_XGBoost.png
?? reports/figures/phase3_roc_LightGBM.png
?? reports/figures/phase3_roc_XGBoost.png
?? reports/figures/precision_recall.png
?? reports/figures/roc.png
?? scripts/build_phase2_report.py
?? scripts/build_phase3_report.py
?? scripts/build_phase4_report.py
?? scripts/execute_phase2_notebook.py
?? scripts/run_baselines.py
?? scripts/run_interpretability.py
?? scripts/run_optimization.py
?? scripts/run_sanity_checks.py
?? src/fraud_detection/features.py
?? src/fraud_detection/interpretability.py
?? src/fraud_detection/metrics.py
?? src/fraud_detection/modeling.py
?? src/fraud_detection/optimization.py
?? src/fraud_detection/splitting.py
?? src/fraud_detection/tracking.py
?? tests/test_interpretability.py
?? tests/test_modeling.py
?? tests/test_optimization.py
```

## Conclusiones revisión y recomendación para Fase 5
El modelo se apoya fuertemente en la regla de vaciado, complementada por monto, balances y ratio. La explicación del FN de monto cero es coherente con la ausencia del patrón dominante, pero requiere revisión de semántica/etiqueta del simulador sin modificarla automáticamente. Las contribuciones no son causales ni prueban capacidad real fuera del simulador. Confirmar disponibilidad de balances al scoring y generalización en una fase independiente autorizada. Champion continúa provisional, threshold continúa de referencia. No iniciar Production, monitoring, drift, dashboard o deployment automáticamente.

PHASE 4: COMPLETE
