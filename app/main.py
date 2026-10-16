"""Professional offline Streamlit monitoring dashboard; persisted artifacts only."""
from pathlib import Path
import sys
import numpy as np,pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.data_access import (ArtifactError,ROOT,load_bundle,artifact_signature,filtered_metrics,
    filter_step_rows,REPORT_FILES,safe_file)

st.set_page_config(page_title='Fraud Monitoring · PaySim',page_icon='📊',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
.block-container{padding-top:4rem;padding-bottom:3rem;max-width:1500px}
h1,h2,h3{color:#12243a;letter-spacing:-.02em}
[data-testid="stSidebar"]{background:#f2f5f9;border-right:1px solid #dde4ed}
[data-testid="stMetric"]{background:#f7f9fc;border:1px solid #e0e7ef;border-radius:12px;padding:16px}
[data-testid="stMetricLabel"]{color:#516277;font-size:.85rem}
[data-testid="stMetricValue"]{font-size:1.7rem;color:#12243a}
.scope{color:#516277;font-size:.95rem;margin-bottom:1.4rem}
.eyebrow{color:#325f94;font-weight:650;letter-spacing:.10em;font-size:.72rem;margin-bottom:.4rem}
</style>''',unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def cached_bundle(root:str,signature:tuple):return load_bundle(Path(root))

@st.cache_data(show_spinner=False,max_entries=12)
def report_bytes(path:str,mtime:int):return Path(path).read_bytes()

@st.cache_data(show_spinner=False)
def validation_explanations(path:str,mtime:int):return pd.read_csv(path)


def fmt(value,kind='number'):
    if value is None or pd.isna(value):return 'No disponible'
    if kind=='pct':return f'{value:.4%}'
    if kind=='metric':return f'{value:.6f}'
    return f'{int(value):,}'


def chart(fig,height=340):
    fig.update_layout(template='plotly_white',height=height,font=dict(family='Arial',size=12,color='#23364c'),
        margin=dict(l=15,r=15,t=35,b=20),legend_title_text='',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
        colorway=['#245e9b','#7b5ca7','#d69a36','#4b8a8c'])
    st.plotly_chart(fig,width='stretch',config={'displaylogo':False})


def cards(items):
    columns=st.columns(len(items))
    for column,(label,value,kind) in zip(columns,items):column.metric(label,fmt(value,kind))


def section_scope(title,text):
    st.subheader(title);st.caption(text)


def overview(bundle,m,selected):
    cards([('Transacciones',m['observations'],'number'),('Fraudes etiquetados',m['frauds'],'number'),('Prevalencia',m['prevalence'],'pct'),('Tasa de alertas @0.5',m['alert_rate'],'pct')])
    st.write('')
    cards([('Average Precision',m['pr_auc'],'metric'),('Recall @0.5',m['recall_05'],'pct'),('Precision @0.5',m['precision_05'],'pct'),('Falsos negativos',m['fn'],'number')])
    if not m['ranking_available']:st.info(m['ranking_scope']+'. AP no puede obtenerse promediando AP de ventanas.')
    left,right=st.columns([1.6,1])
    with left:
        section_scope('Trayectoria de Production','Volumen y fraudes por step dentro de las ventanas seleccionadas.')
        profile=filter_step_rows(bundle['steps'],bundle['windows'],selected)
        profile['window_id']=(profile.step-bundle['freeze']['window_anchor_step'])//bundle['freeze']['window_width_hours']
        plot=profile.melt(id_vars=['step','window_id'],value_vars=['transactions','frauds'],var_name='Serie',value_name='Transacciones')
        chart(px.line(plot,x='step',y='Transacciones',color='Serie',line_group='window_id',labels={'step':'Step · hora simulada'}))
    with right:
        section_scope('Señales de monitoreo','Comparación completa Reference/Development vs Production; no depende del filtro temporal.')
        st.metric('Diferencias estadísticas',int(bundle['drift'].statistical_shift.sum()))
        st.metric('Superan criterios conjuntos',int(bundle['drift'].drift_detected.sum()))
        st.caption('Holm p<0.05 + KS D≥0.10 / TV≥0.05; step excluido. Cero alertas materiales no significa ausencia total de cambios.')
        st.info(bundle['summary']['concept_drift'])
    section_scope('Comparación de períodos completos','Esta tabla es global: Validation y Production completos, sin aplicar el filtro de ventanas.')
    columns=['period','observations','frauds','prevalence','pr_auc','precision_05','recall_05','alert_rate','fn']
    st.dataframe(bundle['comparison'][columns],width='stretch',hide_index=True)
    with st.expander('Cómo interpretar estos resultados'):
        st.markdown('**AP** evalúa ranking y depende de prevalencia. **Recall** es la fracción de fraudes detectados a 0.5. **Precision** es el rendimiento de las alertas. PaySim es un simulador con patrones casi determinísticos; estos resultados no prueban desempeño real. Las etiquetas permiten evaluación retrospectiva y no equivalen a un sistema en tiempo real.')


def performance(bundle,m,selected):
    cards([('Average Precision',m['pr_auc'],'metric'),('ROC-AUC',m['roc_auc'],'metric'),('Precision @0.5',m['precision_05'],'metric'),('Recall @0.5',m['recall_05'],'metric'),('F2 @0.5',m['f2_05'],'metric')])
    st.caption('Threshold 0.5 = referencia congelada, no threshold definitivo de producción. F1: '+fmt(m['f1_05'],'metric'))
    left,right=st.columns([1,1.4])
    with left:
        section_scope('Matriz de confusión','Conteos agregados exactamente sobre las ventanas seleccionadas.')
        fig=go.Figure(go.Heatmap(z=[[m['tn'],m['fp']],[m['fn'],m['tp']]],x=['Legítima','Fraude'],y=['Legítima','Fraude'],
            text=[[fmt(m['tn']),fmt(m['fp'])],[fmt(m['fn']),fmt(m['tp'])]],texttemplate='%{text}',colorscale='Blues',showscale=False))
        fig.update_xaxes(title='Predicción @0.5');fig.update_yaxes(title='Etiqueta',autorange='reversed');chart(fig)
    with right:
        section_scope('Capacidad de revisión','Recall observado y límite teórico por capacidad; Top-K mantiene el ranking del ámbito disponible.')
        top=pd.DataFrame(m['top_k'])
        long=top.melt(id_vars='capacity',value_vars=['recall','theoretical_recall'],var_name='Serie',value_name='Recall')
        chart(px.bar(long,x='capacity',y='Recall',color='Serie',barmode='group',labels={'capacity':'Capacidad revisada'}))
        st.dataframe(top,width='stretch',hide_index=True)
        if not m['ranking_available']:st.info('Ranking combinado no disponible para varias ventanas. El límite teórico sí se deriva del soporte seleccionado.')
        else:st.caption('Un Top-K pequeño puede saturar su capacidad con precision 100% y recall bajo cuando hay más fraudes que filas revisables.')
    section_scope('Desempeño por ventana','Las métricas de cada fila fueron calculadas en Fase 5 sobre su propia ventana. No son medias de scores.')
    windows=bundle['windows'].loc[bundle['windows'].window.isin(selected)]
    plot=windows.assign(Ventana=windows.step_min.astype(str)+'–'+windows.step_max.astype(str)).melt(id_vars='Ventana',value_vars=['pr_auc','recall_05','f2_05'],var_name='Métrica',value_name='Valor')
    chart(px.line(plot,x='Ventana',y='Valor',color='Métrica',markers=True))
    st.dataframe(windows[['step_min','step_max','observations','frauds','pr_auc','roc_auc','precision_05','recall_05','f1_05','f2_05','fp','fn','support_warning']],width='stretch',hide_index=True)
    with st.expander('Comparación Validation vs Production · períodos completos'):
        st.dataframe(bundle['comparison'][['period','pr_auc','roc_auc','precision_05','recall_05','f1_05','f2_05','tp','fp','tn','fn']],width='stretch',hide_index=True)
    cases=bundle['cases'].loc[(bundle['cases'].period=='Production')&(bundle['cases'].category=='false_negative')]
    cases=filter_step_rows(cases,bundle['windows'],selected)
    st.warning(f'{len(cases)} FN en las ventanas seleccionadas; {int((cases.amount==0).sum())} tienen monto cero. No se usa este hallazgo para ajustar el modelo o el threshold.')
    st.dataframe(cases[['period_row_index','step','amount','oldbalanceOrg','score']],width='stretch',hide_index=True)


def data_drift(bundle):
    st.info('Ámbito: comparación completa Reference/Development (1–400) vs Production. Los filtros temporales no recalculan tests de drift; no existen artifacts de drift por ventana.')
    frame=bundle['drift']
    names=st.multiselect('Variables monitorizadas',frame.feature.tolist(),default=frame.feature.tolist())
    selected=frame.loc[frame.feature.isin(names)].copy()
    cards([('Variables seleccionadas',len(selected),'number'),('Diferencia estadística',int(selected.statistical_shift.sum()),'number'),('Criterios conjuntos',int(selected.drift_detected.sum()),'number')])
    st.caption('Diferencia estadística ≠ drift material. step es separación temporal estructural; no se cuenta como alerta.')
    if selected.empty:st.info('Selecciona al menos una variable.');return
    chart(px.bar(selected,x='feature',y=['effect','practical_threshold'],barmode='group',labels={'feature':'Variable','value':'Distancia / umbral'}),400)
    st.caption('KS D para variables numéricas y TV para indicadores: son distancias distintas. Los umbrales son convenciones documentadas, no leyes universales.')
    st.dataframe(selected,width='stretch',hide_index=True)
    chosen=st.selectbox('Detalle de una variable',selected.feature.tolist())
    row=selected.loc[selected.feature==chosen].iloc[0]
    st.write(f"**{chosen}** · {row['effect_metric']} = {row['effect']:.6f} · umbral = {row['practical_threshold']:.2f} · Holm p = {row['holm_p_value']:.3g}")
    if chosen.startswith('type_') or chosen in ['orig_balance_emptied','orig_balance_zero','dest_is_merchant']:
        proportions=pd.DataFrame({'Período':['Reference','Production'],'Fracción':[row.reference_mean,row.current_mean]})
        chart(px.bar(proportions,x='Período',y='Fracción'),260)
    else:st.caption('El artifact conserva medias y distancias; no inventamos una distribución individual de esta variable. Consulta el HTML Evidently para sus distribuciones muestreadas.')
    conditioned=bundle['conditioned'].loc[bundle['conditioned'].feature==chosen]
    if len(conditioned):
        st.markdown('**Cambio dentro de cada tipo** · diagnóstico para distinguir mezcla de operaciones y cambios dentro del tipo.')
        chart(px.bar(conditioned,x='type',y='effect',color='method'),260)
        st.dataframe(conditioned,width='stretch',hide_index=True)
    with st.expander('Criterios y límites'):
        st.markdown('Se requiere Holm p<0.05 **y** magnitud KS D≥0.10 o TV≥0.05. PSI≥0.20 es un indicador separado de revisión. Evidently usa muestras uniformes y PSI; el cuadro principal usa datos completos y KS/TV. La dependencia temporal limita interpretación iid. Las features raras pueden cambiar operacionalmente aunque no superen umbrales genéricos.')


def predictions(bundle,m,selected):
    st.info('Percentiles y distribución: períodos completos. Evolución por step y tasas agregadas: ventanas seleccionadas. Los percentiles no se promedian entre ventanas.')
    frame=bundle['scores']
    section_scope('Distribución de scores','Scores del XGBoost congelado; no son probabilidades calibradas.')
    image=ROOT/'reports/figures/monitoring/score_distributions.png'
    if image.is_file():st.image(str(image),width='stretch')
    else:st.warning('No está disponible la figura persistida score_distributions.png.')
    left,right=st.columns(2)
    with left:
        percentiles=frame.melt(id_vars='period',value_vars=['p01','p10','median','p90','p99','p999'],var_name='Percentil',value_name='Score')
        chart(px.line(percentiles,x='Percentil',y='Score',color='period',markers=True),320)
    with right:
        chart(px.bar(frame,x='period',y='alert_rate',labels={'period':'Período completo','alert_rate':'Tasa de alertas'}),320)
    st.dataframe(frame,width='stretch',hide_index=True)
    section_scope('Tasa de alertas en la selección',f"Steps {m['step_min']}–{m['step_max']} · {m['window_count']} ventanas completas. Esta serie sí aplica la selección.")
    profile=filter_step_rows(bundle['steps'],bundle['windows'],selected)
    profile['alert_rate']=profile.alerts/profile.transactions
    profile['window_id']=(profile.step-bundle['freeze']['window_anchor_step'])//bundle['freeze']['window_width_hours']
    plot=profile.melt(id_vars=['step','window_id'],value_vars=['alert_rate','fraud_rate'],var_name='Serie',value_name='Tasa')
    chart(px.line(plot,x='step',y='Tasa',color='Serie',line_group='window_id',labels={'step':'Step · hora simulada'}))
    st.metric('Alertas / volumen seleccionado',fmt(m['alert_rate'],'pct'))
    st.caption('Score shift (global): '+str(bundle['summary']['score_shift']))
    st.info('Prediction drift no implica automáticamente concept drift ni deterioro. '+bundle['summary']['concept_drift'])


def investigate(bundle,selected):
    period=st.radio('Período de los casos',['Production','Validation'],horizontal=True)
    categories=bundle['cases'].loc[bundle['cases'].period==period].category.unique().tolist()
    category=st.selectbox('Categoría de investigación',categories)
    cases=bundle['cases'].loc[(bundle['cases'].period==period)&(bundle['cases'].category==category)].copy()
    if period=='Production':cases=filter_step_rows(cases,bundle['windows'],selected)
    else:st.caption('Casos de Validation completos; el filtro de Production no se aplica.')
    st.caption('Casos exportados por Fase 5, no todo el dataset. Índices anónimos con base cero; sin datos personales. Las categorías pueden compartir la misma transacción.')
    st.metric('Casos disponibles en este ámbito',len(cases))
    columns=['period_row_index','step','label','prediction_05','score','amount','oldbalanceOrg','oldbalanceDest','amount_to_oldbalanceOrg','orig_balance_emptied']
    st.dataframe(cases[columns],width='stretch',hide_index=True)
    if cases.empty:st.info('No hay casos exportados para esta selección.')
    else:
        identifiers=cases.period_row_index.astype(int).tolist()
        index=st.selectbox('Índice de transacción',identifiers)
        record=cases.loc[cases.period_row_index==index].iloc[0]
        cards([('Score',record.score,'metric'),('Etiqueta',record.label,'number'),('Predicción @0.5',record.prediction_05,'number')])
        st.json({name:float(record[name]) for name in columns if name not in ['period_row_index']})
    if period=='Production':st.info('No hay SHAP específico de Production exportado. No atribuimos explicaciones de Validation a transacciones de Production.')
    with st.expander('Explicaciones SHAP existentes · solo Validation'):
        path=ROOT/'artifacts/local_explanations.csv'
        if not path.is_file():st.warning('Falta local_explanations.csv de Fase 4.');return
        local=validation_explanations(str(path),path.stat().st_mtime_ns)
        case=st.selectbox('Caso SHAP de Validation',local.case.unique().tolist())
        show=local.loc[local.case==case]
        st.caption('Contribuciones de Fase 4 en log-odds; no causales. El caso seleccionado puede ser distinto al de la tabla superior.')
        st.dataframe(show[['validation_row_index','true_label','score','feature','feature_value','shap_log_odds']],width='stretch',hide_index=True)
        plot=ROOT/'reports/figures/interpretability'/('waterfall_'+case+'.png')
        if plot.is_file():st.image(str(plot),width='stretch')


def html_reports():
    st.divider()
    with st.expander('Informes offline de Fase 5 · descarga de los cinco HTML'):
        st.caption('Informes globales completos: no se recalculan con filtros. Se descargan los archivos reales, sin duplicarlos ni subirlos a un servicio.')
        columns=st.columns(2)
        for i,(label,name) in enumerate(REPORT_FILES.items()):
            with columns[i%2]:
                try:
                    path=safe_file(ROOT,'reports/monitoring/'+name)
                    content=report_bytes(str(path),path.stat().st_mtime_ns)
                    st.download_button(label,data=content,file_name=path.name,mime='text/html',key='report_'+path.name,width='stretch')
                    st.caption(f'{path.stat().st_size/1024:.0f} KB · {name}')
                except ArtifactError as exc:st.warning(str(exc))


def main():
    try:bundle=cached_bundle(str(ROOT),artifact_signature(ROOT))
    except (ArtifactError,KeyError,ValueError,OSError) as exc:
        st.error('No se pueden mostrar KPIs fiables: '+str(exc));st.caption('Restaurá los artifacts indicados desde el pipeline documentado de Fase 5. La app no fabrica valores ni ejecuta entrenamiento.');st.stop()
    with st.sidebar:
        st.markdown('### FRAUD MONITORING')
        st.caption('PaySim · análisis offline')
        page=st.radio('Navegación',['Resumen ejecutivo','Desempeño del modelo','Datos y drift','Scores y alertas','Investigación de casos'])
        st.divider()
        windows=bundle['windows']
        labels={int(row.window):f'{int(row.step_min)}–{int(row.step_max)}' for row in windows.itertuples()}
        selected=st.multiselect('Ventanas Production · steps',list(labels),default=list(labels),format_func=lambda index:labels[index])
        st.caption('Ventanas completas. El filtro no altera comparaciones globales de drift, scores ni informes HTML.')
        if st.button('Releer artifacts',width='stretch'):cached_bundle.clear();report_bytes.clear();st.rerun()
        st.divider();st.caption('XGBoost tuned · champion provisional')
        st.caption('Threshold de referencia: '+str(bundle['freeze']['threshold']))
        st.caption('Modelo: '+bundle['summary']['model_sha256'][:16]+'…')
    if not selected:st.info('Selecciona al menos una ventana Production para continuar.');st.stop()
    m=filtered_metrics(bundle,selected)
    st.markdown('<div class="eyebrow">PRODUCCIÓN SIMULADA · MODELO CONGELADO · OFFLINE</div>',unsafe_allow_html=True)
    st.title(page)
    st.markdown(f'<div class="scope">Steps {m["step_min"]}–{m["step_max"]} · {m["window_count"]} ventanas seleccionadas · fuente: artifacts validados de Fase 5</div>',unsafe_allow_html=True)
    if len(selected)<len(windows):st.caption('La selección puede contener intervalos no contiguos. Solo se suman las ventanas elegidas; AP/ROC-AUC/Top-K combinados no se inventan.')
    {'Resumen ejecutivo':lambda:overview(bundle,m,selected),'Desempeño del modelo':lambda:performance(bundle,m,selected),
     'Datos y drift':lambda:data_drift(bundle),'Scores y alertas':lambda:predictions(bundle,m,selected),
     'Investigación de casos':lambda:investigate(bundle,selected)}[page]()
    html_reports()
    st.caption('No es monitoreo en tiempo real. No se recalcula scoring, entrenamiento, SHAP, Optuna, MLflow ni Evidently al navegar.')

if __name__=='__main__':main()


