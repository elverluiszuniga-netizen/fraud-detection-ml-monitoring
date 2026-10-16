"""Complete Phase 4 report, documentation and executable artifact notebook."""
import base64, contextlib, hashlib, io, json, subprocess, sys
from pathlib import Path
import pandas as pd
from IPython.display import Image, Markdown
import mlflow
from mlflow.tracking import MlflowClient
ROOT=Path(__file__).resolve().parents[1]

def table(frame):
    lines=['| '+' | '.join(frame.columns)+' |','| '+' | '.join(['---']*len(frame.columns))+' |']
    for row in frame.itertuples(index=False,name=None):
        lines.append('| '+' | '.join(f'{v:.6f}' if isinstance(v,float) else str(v) for v in row)+' |')
    return '\n'.join(lines)

def main():
    r=json.loads((ROOT/'artifacts/interpretability_summary.json').read_text())
    if not r['metric_reproduction'] or r['production_used']:raise ValueError('Invalid explanation evidence')
    for relative,digest in r['previous_phase_file_hashes'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=digest:raise ValueError('Prior phase changed: '+relative)
    if hashlib.sha256(Path(r['source_model']).read_bytes()).hexdigest()!=r['model_sha256']:raise ValueError('Model changed')
    tests=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=ROOT,capture_output=True,text=True)
    if tests.returncode:raise RuntimeError(tests.stdout+tests.stderr)
    importance=pd.read_csv(ROOT/'artifacts/shap_global_importance.csv')
    locals=pd.read_csv(ROOT/'artifacts/local_explanations.csv')
    outside=pd.read_csv(ROOT/'artifacts/non_rule_fraud_explanations.csv')
    groups=pd.read_csv(ROOT/'artifacts/shap_group_comparison.csv')
    directions=pd.read_csv(ROOT/'artifacts/shap_feature_directions.csv')
    state=r['emptied']['states'];o=r['outside_rule'];sample=r['sample']
    git=['git','-c',f'safe.directory={ROOT.as_posix()}']
    branch=subprocess.check_output(git+['branch','--show-current'],cwd=ROOT,text=True).strip()
    if branch!='development':raise ValueError('Wrong branch')
    cases=[]
    narratives={
      'A_high_score_TP':'La transferencia iguala monto y saldo previo. El vaciado aproximado aporta +6.700 log-odds, reforzado por ratio 1 y monto; esto supera el valor base negativo. Explica el score alto, sin demostrar causalidad.',
      'B_low_score_TN':'El ratio 1.022 aporta positivamente, pero no basta: ausencia de CASH_OUT, vaciado 0, destino merchant y PAYMENT aportan negativamente. La base negativa y el patrón operativo mantienen el score bajo.',
      'C_false_negative':'CASH_OUT con monto 0, saldo origen 0 y ratio 0 (sentinel de división por cero), sin vaciado. La base es -5.281 log-odds. Monto (+1.326) y CASH_OUT (+1.054) elevan el margen, pero no lo suficiente; vaciado 0 (-0.211) y saldo destino (-0.172) lo reducen. El score 0.057349 queda bajo 0.5. El error no se atribuye únicamente a una contribución negativa: faltan las grandes contribuciones positivas de los patrones habituales. Debe revisarse este caso de monto cero y su semántica de simulación.',
      'E_non_rule_TP':'TRANSFER por 10 millones con saldo previo 14.892 millones, ratio 0.67149 y vaciado 0. Monto (+4.170), saldo origen (+3.425) y ratio (+0.906) superan la base negativa y la pequeña penalización por ausencia de vaciado. El modelo también reconoce un patrón multivariable fuera de la regla principal.',
      'F_nearest_reference_threshold':'El score más cercano a 0.5 es 0.716314, a distancia 0.216314. Es el caso más próximo disponible, pero no una transacción realmente cercana a 0.5; no se inventa un caso ambiguo. Monto y saldo origen elevan el margen, mientras el ratio 0.222756 y vaciado 0 lo reducen.'}
    for name,case in r['local_cases'].items():
        if not case['exists']:
            cases.append('### '+name+'\n\nNo existe False Positive en Validation a threshold 0.5; no se inventa caso ni waterfall.')
            continue
        frame=locals.loc[locals.case==name,['feature','feature_value','shap_log_odds','absolute_rank']]
        cases.append(f"### {name}\n\nÍndice Validation cero-based {case['validation_row_index']}; step {case['step']}; label {case['label']}; score {case['score']:.9f}; predicción @0.5 {case['prediction_05']}.\n\n{narratives[name]}\n\n"+table(frame))
    core=f'''# Interpretabilidad del modelo XGBoost

## Objetivo modelo y período
Explicar global y localmente el champion provisional XGBoost tuned de Fase 3, sin reentrenar, cambiar features, seleccionar threshold ni leer Production. Solo se abren validation_X.npy y validation_y.npy, correspondientes a steps 321–400: 1,398,242 filas y 868 fraudes. No se abre el CSV raw ni matrices Train. Las métricas recargadas reproducen exactamente Fase 3: AP {r['validation_metrics']['pr_auc']:.9f}, TP 867, TN 1,397,374, FN 1, FP 0.

Modelo fuente: `{r['source_model']}`; SHA256 `{r['model_sha256']}`; run fuente `{r['source_phase3_run_id']}`. El archivo tiene 44 rondas, pero sklearn usa best_iteration+1 = 24. Tree SHAP y gain nativo se calculan exclusivamente con esas 24 rondas; no se modifica el archivo ni se explica accidentalmente el ensemble posterior al mejor punto. Features y matrices de Fase 2 permanecen iguales.

## Metodología y muestra
Tree SHAP exacto nativo de XGBoost, pred_contribs=True, approx_contribs=False, iteration_range=(0,24). Se utiliza SHAP para representar Explanation, beeswarm, bar y waterfall. Método tree-path-dependent: las estadísticas de cobertura de entrenamiento ya guardadas en los árboles definen la referencia; no se crea un background nuevo. Las contribuciones y la base se expresan en log-odds. Sigmoid(base + suma SHAP) reconstruye el score. No son puntos de probabilidad aditivos ni probabilidades calibradas.

Muestra de {sample['rows']:,} filas: todos los {sample['frauds']} fraudes y {sample['nonfrauds']:,} no fraudes, uniformes sin reemplazo, semilla 42. Su prevalencia es {100*sample['fraud_fraction']:.2f}%, frente a {100*r['validation_frauds']/r['validation_rows']:.6f}% real. No debe confundirse esta muestra enriquecida de explicación con la distribución de Validation. La importancia poblacional se estima ponderando las medias por clase con la prevalencia real; es una estimación basada en 2,000 no fraudes, no SHAP exhaustivo de toda Validation. Casos locales extremos se explican por separado y no se añaden a la muestra global.

Errores máximos de reconstrucción: margen {r['additivity']['max_margin_error']:.9g}; score {r['additivity']['max_probability_error']:.9g}. Las pruebas también verifican las rondas efectivas y el slicing de matrices memory-mapped.

## Explicación global e importancia nativa
{table(importance)}

La feature dominante es orig_balance_emptied, seguida de amount_to_oldbalanceOrg y amount. En la muestra enriquecida, el vaciado concentra {100*r['emptied']['mean_abs_shap']/importance.mean_abs_shap.sum():.2f}% de la suma de mean absolute SHAP; esto no representa porcentaje de varianza explicada ni causalidad. La ponderación por prevalencia mantiene vaciado en primer lugar, pero cambia el orden de las demás variables: revisar ambas columnas/rankings.

Gain nativo resume mejora media de la función objetivo en los splits del ensemble efectivo; split count cuenta frecuencia de uso. Mean absolute SHAP resume magnitud de contribuciones sobre una distribución de explicación concreta. Sus rankings pueden diferir por cobertura, ponderación de clases, correlación entre saldo/monto/ratio/vaciado, interacciones y distribución de la muestra. Ambos identifican vaciado como dominante; no implican efectos causales.

## Dirección dependence e interacciones
Beeswarm y tres dependence plots están en reports/figures/interpretability. Monto y ratio muestran relaciones no lineales; no debe imponerse una relación monotónica a todas las transacciones. Las contribuciones del saldo destino tienden a reducirse al aumentar su valor en esta muestra, pero hay contexto e interacciones. Las variables monetarias se presentan como log1p cuando la escala es grande. El color representa ratio o vaciado según el gráfico; es evidencia descriptiva de dependencia, no efecto causal.

{table(directions.drop_duplicates('feature')[['feature','spearman_value_vs_shap']])}

Los coeficientes Spearman son descriptivos de valor versus contribución dentro de la muestra enriquecida; constantes se dejan vacías. En 128 filas elegidas con semilla 42 se calcularon interaction values; el error máximo de sus sumas marginales es {r['interaction_marginal_error']:.9g}. Se reportan componentes simétricos off-diagonal, sin sumar dos veces ambas posiciones ni interpretar causalidad:

{table(pd.DataFrame(r['top_interaction_components']))}

La interacción de monto y saldo origen destaca, coherente con las features derivadas del mismo par de variables. La muestra de interacción es pequeña y no ofrece conclusiones poblacionales precisas.

## Regla de vaciado
orig_balance_emptied ocupa rank {r['emptied']['sample_rank']} con mean |SHAP| {r['emptied']['mean_abs_shap']:.6f}. Si vale 1, la contribución media es +{state['1']['mean_shap']:.6f} log-odds y el score medio en la muestra es {state['1']['mean_score']:.6f}. Si vale 0, la contribución media es {state['0']['mean_shap']:.6f}, con score medio {state['0']['mean_score']:.6f}. Son medias de subgrupos de una muestra enriquecida; no estiman un efecto de intervención.

El modelo aprende principalmente la regla de vaciado, pero no exclusivamente. Fraudes detectados con vaciado 0 reciben contribuciones fuertes de monto, saldo origen y ratio. Vaciado se definió antes del scoring como saldo origen positivo y abs(monto - saldo previo) <=0.01, calculado en float64 antes del almacenamiento float32.

## Fraudes fuera de la regla
{o['rows']} de 868 fraudes ({100*o['fraud_fraction']:.6f}%) tienen vaciado 0. Detectados {o['detected']}/{o['rows']} ({100*o['detection_rate']:.2f}%) a threshold de referencia 0.5. Scores entre {o['score_min']:.9f} y {o['score_max']:.9f}. Los 15 correctamente detectados son TRANSFER de monto 10 millones y saldo previo superior al monto. El restante es CASH_OUT con monto y saldo origen cero. Esto es un patrón observado, no una afirmación sobre el mecanismo generador ni una regla causal.

{table(pd.DataFrame(o['top_features']))}

{table(outside[['validation_row_index','step','amount','oldbalanceOrg','amount_to_oldbalanceOrg','score','prediction_05']])}

## Explicaciones locales
{r['threshold_note']}

Los casos se eligen de forma determinística: TP de máximo score, TN de mínimo score, FN de mínimo score, FP de máximo score si existe, TP sin vaciado de máximo score y observación más próxima a 0.5. Los empates usan el primer índice Validation. Los índices no son IDs de clientes ni números de fila raw. Cada caso muestra todos los valores y contribuciones firmadas; local_explanations.csv conserva su estructura reutilizable.

{chr(10).join(cases)}

## Consistencia y robustez cualitativa
{table(groups.sort_values(['group','mean_abs_shap'],ascending=[True,False]).groupby('group').head(3))}

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
'''
    (ROOT/'docs/model_interpretability.md').write_text(core,encoding='utf-8')
    def md(text):return dict(cell_type='markdown',metadata={},source=text.splitlines(keepends=True))
    def code(text):return dict(cell_type='code',metadata={},source=text.splitlines(keepends=True),outputs=[],execution_count=None)
    cells=[md('# Fase 4 Interpretabilidad XGBoost\n\nModelo exacto de Fase 3, 24 rondas efectivas, solo Validation. SHAP explica contribuciones del modelo; no causalidad.'),
      code("from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd()\nif ROOT.name=='notebooks': ROOT=ROOT.parent\nr=json.loads((ROOT/'artifacts/interpretability_summary.json').read_text())\nimportance=pd.read_csv(ROOT/'artifacts/shap_global_importance.csv')\ndisplay(r['sample'])\ndisplay(r['validation_metrics'])"),
      md('## Global y comparación nativa\n\nImportancia de muestra enriquecida y estimación ponderada por prevalencia se presentan por separado. Unidades log-odds. No se atribuye causalidad.'),
      code("display(importance)\nfor name in ['shap_beeswarm.png','shap_global_bar.png','shap_prevalence_weighted_bar.png']:\n    display(Image(filename=str(ROOT/'reports/figures/interpretability'/name)))\nfor path in sorted((ROOT/'reports/figures/interpretability').glob('dependence_*.png')):\n    display(Image(filename=str(path)))"),
      md('## Vaciado y fraudes fuera de regla\n\nLa feature dominante no explica todos los fraudes. Revisar señales de monto/saldo en los 16 casos fuera de regla.'),
      code("display(r['emptied'])\ndisplay(r['outside_rule'])\ndisplay(pd.read_csv(ROOT/'artifacts/non_rule_fraud_explanations.csv'))"),
      md('## Casos locales TP TN FN FP y frontera\n\nThreshold 0.5 = reference threshold, not final production threshold. No existe FP; el caso más próximo a 0.5 está a distancia 0.216314 y no se presenta como auténticamente cercano.'),
      code("display(r['local_cases'])\ndisplay(pd.read_csv(ROOT/'artifacts/local_explanations.csv'))\nfor path in sorted((ROOT/'reports/figures/interpretability').glob('waterfall_*.png')):\n    display(Image(filename=str(path)))"),
      md('## Interpretación completa y limitaciones\n\nEl False Negative tiene monto y saldo origen cero. La base negativa no se compensa con sus contribuciones positivas; ausencia de vaciado y saldo destino añaden contribuciones negativas. El análisis no selecciona nuevo threshold ni cambia el modelo.'),
      code("display(Markdown((ROOT/'docs/model_interpretability.md').read_text(encoding='utf-8')))\ndisplay(pd.read_csv(ROOT/'artifacts/shap_group_comparison.csv'))\ndisplay(r['mlflow'])"),
      md('## Conclusión\n\nPredominio de la regla del simulador y detección multivariable de 15/16 fraudes fuera de regla. Disponibilidad operacional, validación independiente y caso de monto cero requieren revisión. La lógica está en src/fraud_detection/interpretability.py. Este notebook carga artifacts: no reentrena ni lee Production. Detener aquí; Fase 5 requiere autorización.')]
    namespace={};number=0
    for i,cell in enumerate(cells):
        cell['id']=f'phase4-{i:02d}'
        if cell['cell_type']!='code':continue
        number+=1;outputs=[]
        def capture(*values):
            for value in values:
                if isinstance(value,Image):data={'image/png':base64.b64encode(value.data).decode()}
                elif isinstance(value,Markdown):data={'text/markdown':value.data}
                elif isinstance(value,pd.DataFrame):data={'text/html':value.to_html(),'text/plain':value.to_string()}
                else:data={'text/plain':str(value)}
                outputs.append(dict(output_type='display_data',metadata={},data=data))
        namespace['display']=capture
        source=''.join(cell['source']).replace('from IPython.display import display, Image, Markdown','from IPython.display import Image, Markdown')
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):exec(compile(source,f'phase4-cell-{i}','exec'),namespace)
        if stream.getvalue():outputs.append(dict(output_type='stream',name='stdout',text=stream.getvalue()))
        cell['execution_count']=number;cell['outputs']=outputs
    notebook=dict(cells=cells,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3'),language_info=dict(name='python')),nbformat=4,nbformat_minor=5)
    (ROOT/'notebooks/04_interpretability.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
    status=subprocess.check_output(git+['status','--short'],cwd=ROOT,text=True)
    report='# Phase 4 Interpretability Report\n\n## Executive summary\n\nSHAP identifica vaciado aproximado como feature dominante; el modelo también detecta 15/16 fraudes fuera de regla. Se explica el único FN y se documenta ausencia de FP. Modelo, matrices y métricas previas preservados. Production reservado.\n\n'+core+f'''\n\n## MLflow tests artifacts y Git
Un solo nuevo run de interpretabilidad: `{r['mlflow']['run_id']}`, estado {r['mlflow']['run_status']}, experimento {r['mlflow']['experiment_id']}. URI local `{r['mlflow']['tracking_uri']}`. Metadata de los 29 runs históricos de Fase 3 verificada sin cambios. Se registran importance CSV, casos locales, resumen, CSV de direcciones/grupos/fraudes fuera de regla, figuras y configuración/source; no se suben datasets ni matrices SHAP completas.

Suite existente y nueva:
```
{tests.stdout.strip()}
```
Notebook: {number} celdas de código ejecutadas sin errores. Análisis y logging completados en {r['total_seconds']:.2f} segundos; excluye implementación, instalación y construcción del reporte. Hubo dos reparaciones de exportación (slicing de memmap SHAP y step duplicado); ambas resueltas antes de logging; se corrigió además la lectura UTF-8 del notebook en Windows. Advertencias de deprecación de SHAP/matplotlib y MLflow/SQLAlchemy no bloquean ejecución.

Archivos nuevos: src/fraud_detection/interpretability.py, scripts/run_interpretability.py, scripts/build_phase4_report.py, tests/test_interpretability.py, docs/model_interpretability.md, notebooks/04_interpretability.ipynb, PHASE_4_INTERPRETABILITY_REPORT.md, seis artifacts CSV/JSON pequeños y figuras en reports/figures/interpretability. README actualizado mínimamente; pyproject y uv.lock añaden SHAP; .gitignore permite artifacts pequeños y mantiene matrices/stores ignorados. No se guardan matrices SHAP gigantes ni modelos nuevos. Rama `{branch}`; no commits, push, remoto, merge, tag o release.

```
{status.strip()}
```

## Conclusiones revisión y recomendación para Fase 5
El modelo se apoya fuertemente en la regla de vaciado, complementada por monto, balances y ratio. La explicación del FN de monto cero es coherente con la ausencia del patrón dominante, pero requiere revisión de semántica/etiqueta del simulador sin modificarla automáticamente. Las contribuciones no son causales ni prueban capacidad real fuera del simulador. Confirmar disponibilidad de balances al scoring y generalización en una fase independiente autorizada. Champion continúa provisional, threshold continúa de referencia. No iniciar Production, monitoring, drift, dashboard o deployment automáticamente.

PHASE 4: COMPLETE
'''
    (ROOT/'PHASE_4_INTERPRETABILITY_REPORT.md').write_text(report,encoding='utf-8')
    mlflow.set_tracking_uri('sqlite:///' + (ROOT/'mlruns/mlflow.db').resolve().as_posix());client=MlflowClient()
    for relative in ('PHASE_4_INTERPRETABILITY_REPORT.md','docs/model_interpretability.md','notebooks/04_interpretability.ipynb'):
        client.log_artifact(r['mlflow']['run_id'],str(ROOT/relative),'presentation')
    sys.path.insert(0,str(ROOT/'scripts'))
    from run_interpretability import history_fingerprints
    if history_fingerprints(client,list(r['mlflow']['phase3_history_hashes']))!=r['mlflow']['phase3_history_hashes']:
        raise ValueError('Historical run metadata changed')
    print(tests.stdout.strip());print(f'Notebook cells: {number}');print('PHASE 4: COMPLETE')

if __name__=='__main__':main()

