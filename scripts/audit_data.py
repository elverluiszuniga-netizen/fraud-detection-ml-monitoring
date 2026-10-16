import argparse
import csv
import json
import math
import sqlite3
import sys
import tempfile
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from fraud_detection.validation import missing_columns, binary, segment
from fraud_detection.paths import raw_csv


def new_stats():
    return dict(rows=0, fraud=0, steps=set(), types=Counter(), amount_n=0,
                amount_sum=0., amount_sum_sq=0., amount_min=None, amount_max=None)


def update(stats, row, amount):
    stats['rows'] += 1
    stats['fraud'] += row.get('isFraud') == '1'
    stats['steps'].add(row.get('step'))
    stats['types'][row.get('type', '<missing>')] += 1
    if amount is not None:
        stats['amount_n'] += 1
        stats['amount_sum'] += amount
        stats['amount_sum_sq'] += amount * amount
        stats['amount_min'] = amount if stats['amount_min'] is None else min(amount, stats['amount_min'])
        stats['amount_max'] = amount if stats['amount_max'] is None else max(amount, stats['amount_max'])


def finish(stats):
    steps = sorted(float(s) for s in stats['steps'] if segment(s))
    n = stats['amount_n']; mean = stats['amount_sum'] / n if n else None
    return dict(rows=stats['rows'], fraud=stats['fraud'], fraud_pct=100*stats['fraud']/stats['rows'] if stats['rows'] else 0,
                steps=len(stats['steps']), step_min=min(steps) if steps else None, step_max=max(steps) if steps else None,
                types=dict(stats['types']), amount=dict(count=n, min=stats['amount_min'], max=stats['amount_max'], mean=mean,
                std=math.sqrt(max(0, (stats['amount_sum_sq'] - n*mean*mean)/(n-1))) if n > 1 else None))


def audit(path):
    stats = {key: new_stats() for key in ('global', 'reference', 'production')}
    nulls = Counter(); anomalies = Counter(); targets = Counter(); flags = Counter()
    inferred = {}; memory = 0; duplicates = 0
    with tempfile.TemporaryDirectory(prefix='fraud-audit-') as temp:
        db = sqlite3.connect(str(Path(temp)/'audit.sqlite'))
        try:
            db.execute('PRAGMA journal_mode=OFF'); db.execute('PRAGMA synchronous=OFF'); db.execute('PRAGMA cache_size=-32768')
            for table in ('rows_seen', 'origins', 'destinations'):
                db.execute(f'CREATE TABLE {table} (value TEXT PRIMARY KEY) WITHOUT ROWID')
            with path.open(newline='', encoding='utf-8-sig') as stream:
                reader = csv.DictReader(stream); columns = reader.fieldnames or []
                if len(columns) != len(set(columns)):
                    raise ValueError('Nombres de columnas duplicados')
                inferred = {c: set() for c in columns}
                batches = {t: [] for t in ('rows_seen','origins','destinations')}
                for row in reader:
                    if None in row or any(v is None for v in row.values()):
                        raise ValueError(f'Fila mal formada: {stats["global"]["rows"]+2}')
                    for c, value in row.items():
                        memory += sys.getsizeof(value) + 8
                        if value.strip().lower() in ('', 'nan', 'null', 'na', 'n/a'):
                            nulls[c] += 1
                        else:
                            try:
                                v = float(value)
                                inferred[c].add('integer' if math.isfinite(v) and v.is_integer() else 'float')
                            except ValueError:
                                inferred[c].add('string')
                    try:
                        amount = float(row.get('amount',''))
                        if not math.isfinite(amount): amount = None
                    except ValueError: amount = None
                    if amount is None: anomalies['amount_invalid_or_missing'] += 1
                    elif amount < 0: anomalies['amount_negative'] += 1
                    for c in ('oldbalanceOrg','newbalanceOrig','oldbalanceDest','newbalanceDest'):
                        if c in row:
                            try:
                                v = float(row[c])
                                if not math.isfinite(v): anomalies[c+'_nonfinite'] += 1
                                elif v < 0: anomalies[c+'_negative'] += 1
                            except ValueError: anomalies[c+'_invalid'] += 1
                    targets[row.get('isFraud','<missing>')] += 1
                    if not binary(row.get('isFraud')): anomalies['target_nonbinary'] += 1
                    if 'isFlaggedFraud' in row:
                        flags[row['isFlaggedFraud']] += 1
                        if not binary(row['isFlaggedFraud']): anomalies['flag_nonbinary'] += 1
                    group = segment(row.get('step'))
                    update(stats['global'], row, amount)
                    if group: update(stats[group], row, amount)
                    else: anomalies['step_invalid_unassigned'] += 1
                    batches['rows_seen'].append((json.dumps([row[c] for c in columns], ensure_ascii=False, separators=(',',':')),))
                    for table, c in [('origins','nameOrig'),('destinations','nameDest')]:
                        if row.get(c): batches[table].append((row[c],))
                    if stats['global']['rows'] % 50000 == 0:
                        duplicates += flush(db, batches)
                    if stats['global']['rows'] % 1000000 == 0:
                        print(f"Procesadas {stats['global']['rows']:,} filas", flush=True)
                duplicates += flush(db, batches)
            counts = {t: db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('origins','destinations')}
        finally:
            db.close()
    n = stats['global']['rows']
    return dict(dataset=str(path.resolve()), bytes=path.stat().st_size, audited_utc=datetime.now(timezone.utc).isoformat(),
                rows=n, columns=columns, column_count=len(columns), missing_columns=missing_columns(columns),
                schema={c: ('string' if 'string' in inferred[c] else 'float' if 'float' in inferred[c] else 'integer' if inferred[c] else 'unknown') for c in columns},
                memory_estimate_bytes=memory, memory_method='Suma estimada de objetos string y referencias de celdas; excluye overhead de contenedores. Procesamiento streaming; no es RSS.',
                nulls={c: dict(count=nulls[c], pct=100*nulls[c]/n if n else 0) for c in columns}, duplicates_exact=duplicates,
                duplicate_method='Igualdad exacta de todos los valores de campos CSV (texto decodificado), sin normalizaciÃ³n; filas repetidas despuÃ©s de la primera.',
                unique_entities=counts, target=dict(targets), flagged=dict(flags), anomalies=dict(anomalies),
                periods={k: finish(v) for k,v in stats.items()},
                validation=dict(target_binary=not anomalies['target_nonbinary'], step_valid=not anomalies['step_invalid_unassigned'],
                    overlap_steps=len(stats['reference']['steps'] & stats['production']['steps']),
                    exhaustive=stats['reference']['rows']+stats['production']['rows']==n))


def flush(db, batches):
    before = db.total_changes
    db.executemany('INSERT OR IGNORE INTO rows_seen VALUES (?)', batches['rows_seen'])
    duplicates = len(batches['rows_seen']) - (db.total_changes-before)
    for table in ('origins','destinations'):
        db.executemany(f'INSERT OR IGNORE INTO {table} VALUES (?)', batches[table])
    db.commit()
    for batch in batches.values(): batch.clear()
    return duplicates


def report(r):
    g = r['periods']['global']; ref = r['periods']['reference']; prod = r['periods']['production']
    lines = ['# INITIAL DATA AUDIT', '', '## 1. Executive summary',
        f"AuditorÃ­a completa de {r['rows']:,} transacciones; {g['fraud']:,} fraudes ({g['fraud_pct']:.6f}%). No se entrenaron modelos ni se realizaron pruebas formales de drift.",
        '## 2. UbicaciÃ³n y tamaÃ±o', f"`{r['dataset']}` â€” {r['bytes']:,} bytes ({r['bytes']/1024**2:.2f} MiB). Original intacto; Ãºnica copia. Fecha UTC: {r['audited_utc']}.",
        '## 3. Dimensiones', f"{r['rows']:,} filas Ã— {r['column_count']} columnas. Memoria aproximada de celdas como strings: {r['memory_estimate_bytes']/1024**3:.3f} GiB. {r['memory_method']}",
        '## 4. Schema completo', 'Tipos inferidos sobre todo el archivo, no dtypes de un DataFrame. Nombres exactos:', '', '| Columna | Tipo inferido | Nulos | % nulos |', '|---|---|---:|---:|']
    for c in r['columns']:
        lines.append(f"| {c} | {r['schema'][c]} | {r['nulls'][c]['count']} | {r['nulls'][c]['pct']:.6f} |")
    lines += ['', '## 5. Calidad de datos', f"Columnas faltantes: {r['missing_columns']}. Duplicados exactos: {r['duplicates_exact']:,}. {r['duplicate_method']}",
        f"Validaciones: `{json.dumps(r['validation'])}`. AnomalÃ­as bÃ¡sicas: `{json.dumps(r['anomalies'])}`.",
        f"Step global: {g['step_min']}â€“{g['step_max']}; {g['steps']} valores Ãºnicos. Entidades Ãºnicas exactas: {r['unique_entities']}. No se limpiÃ³ ni transformÃ³ el CSV.",
        '## 6. DistribuciÃ³n del target', f"isFraud: {r['target']}. isFlaggedFraud: {r['flagged']}.",
        '## 7. Desbalance de clases', f"Fraudes: {g['fraud']:,} ({g['fraud_pct']:.6f}%); no fraude: {g['rows']-g['fraud']:,} ({100-g['fraud_pct']:.6f}%). El desbalance exige evaluar mÃ©tricas adecuadas en la fase posterior, sin elegir aÃºn umbral ni tÃ©cnica.",
        '## 8. DistribuciÃ³n por tipo de transacciÃ³n', '', '| Tipo | Global n (%) | Reference n (%) | Production n (%) |', '|---|---:|---:|---:|']
    for t in sorted(g['types']):
        vals = [f"{s['types'].get(t,0):,} ({100*s['types'].get(t,0)/s['rows']:.4f}%)" if s['rows'] else '0 (0%)' for s in (g, ref, prod)]
        lines.append('| '+t+' | '+' | '.join(vals)+' |')
    for i, key in [(9,'reference'),(10,'production')]:
        s = r['periods'][key]
        lines += [f'## {i}. {key.title()} period: '+('step <= 400' if key=='reference' else 'step >= 401'),
            f"Observaciones: {s['rows']:,}; steps: {s['steps']}; rango: {s['step_min']}â€“{s['step_max']}; fraudes: {s['fraud']:,}; tasa: {s['fraud_pct']:.6f}%.", f"Amount (desviaciÃ³n estÃ¡ndar muestral): `{json.dumps(s['amount'])}`."]
    lines += ['## 11. ComparaciÃ³n preliminar reference vs production',
        f"Cambio observado en tasa de fraude: {prod['fraud_pct']-ref['fraud_pct']:.6f} puntos porcentuales. Las proporciones de type se comparan en la tabla anterior. Amount global: `{json.dumps(g['amount'])}`.",
        f"Amount medio: reference {ref['amount']['mean']} frente a production {prod['amount']['mean']}; desviaciÃ³n estÃ¡ndar: {ref['amount']['std']} frente a {prod['amount']['std']}; mÃ¡ximos: {ref['amount']['max']} frente a {prod['amount']['max']}. Comparar cambios en mezcla operativa, frecuencia de fraude y dispersiÃ³n del monto en una fase posterior; los montos extremos requieren revisiÃ³n de dominio, no eliminaciÃ³n automÃ¡tica.",
        'Los periodos difieren en duraciÃ³n y volumen; comparar proporciones y no solo conteos. Las diferencias descriptivas no demuestran data drift, concept drift ni model drift. No se calcularon tests estadÃ­sticos. No se calcularon cuantiles: los estadÃ­sticos bÃ¡sicos son conteo, media, desviaciÃ³n estÃ¡ndar, mÃ­nimo y mÃ¡ximo.',
        '## 12. Posibles riesgos de leakage',
        'Los balances nuevos corresponden potencialmente a informaciÃ³n posterior a la operaciÃ³n. Sus diferencias y cualquier residual no serÃ­an utilizables si el scoring ocurre antes de ejecutar la transferencia. Confirmar el instante de scoring y la disponibilidad real antes de incluirlos. Los identificadores pueden favorecer memorizaciÃ³n; no asumir capacidad de generalizar a nuevos clientes. isFlaggedFraud representa una regla/alerta existente: excluirlo de los predictores inicialmente hasta conocer su procedencia, disponibilidad y relaciÃ³n con la etiqueta. isFraud se usa Ãºnicamente como target. Todo ajuste, codificaciÃ³n o agregaciÃ³n futura debe aprenderse Ãºnicamente del periodo de desarrollo; producciÃ³n queda reservada. Las agregaciones histÃ³ricas deben usar exclusivamente eventos anteriores.',
        '## 13. Features sugeridas por la consigna (solo diseÃ±o)',
        '- oldbalanceOrg - newbalanceOrig: salida neta; evaluar disponibilidad de balance posterior.\n- oldbalanceDest - newbalanceDest: signo negativo para incremento neto; mismo riesgo temporal.\n- amount / oldbalanceOrg: intensidad; definir manejo de denominador cero sin convertir infinito en valor arbitrario.\n- Merchant por prefijo M de nameDest: verificar semÃ¡ntica antes de usar.\n- CodificaciÃ³n de type: vocabulario ajustado solo en desarrollo y manejo de categorÃ­as nuevas.\n- Indicadores CASH_OUT y TRANSFER: evaluarlos por su relaciÃ³n con la operativa; no asumir causalidad.',
        '## 14. Features adicionales propuestas (solo diseÃ±o)',
        '- log1p(amount) para escala asimÃ©trica, previa validaciÃ³n de no negativos.\n- Indicadores de balance de origen cero y monto superior al balance previo: disponibilidad previa a scoring.\n- Frecuencias y sumas histÃ³ricas por origen: solo pasado, con control de entidades nuevas.\n- Residuales contables respecto de amount: candidatos condicionados a disponibilidad de balances posteriores.\nNo se generÃ³ dataset modelado ni se adoptaron decisiones metodolÃ³gicas definitivas.',
        '## 15. Estructura del repositorio creada',
        '`data/{raw,processed}`, `notebooks`, `src/fraud_detection`, `scripts`, `tests`, `artifacts`, `reports/{figures,monitoring}`, `app`, `docs`. Carpetas futuras vacÃ­as con .gitkeep.',
        '## 16. Archivos creados/modificados',
        'README.md, data/README.md, pyproject.toml, uv.lock, .python-version, .gitignore, src/fraud_detection/{__init__,validation}.py, scripts/audit_data.py, tests/test_validation.py, reports/audit_results.json, INITIAL_DATA_AUDIT.md y .gitkeep. El PDF acadÃ©mico preexistente permanece intacto.',
        '## 17. Tests ejecutados y resultado',
        'Ejecutado: uv run --offline python -m unittest discover -s tests -v. Resultado: 5 tests OK; columnas, target binario, lÃ­mites/valores invÃ¡lidos de step y auditorÃ­a sintÃ©tica con duplicados, entidades y segmentaciÃ³n, sin leer el CSV grande.',
        '## 18. Estado Git local',
        'Repositorio local preparado con main y development, sin remoto ni push. Dataset excluido explÃ­citamente; sin versionar el raw. Sin identidad Git preconfigurada: el commit inicial utiliza una identidad tÃ©cnica local solo en ese comando (Academic project initialization <local@localhost>). Se utiliza safe.directory por comando debido a propiedad del directorio distinta entre usuario y entorno ejecutor, sin modificar configuraciÃ³n global.',
        '## 19. Dependencias instaladas/agregadas',
        'Compatibilidad Python >=3.10; ejecuciÃ³n con Python 3.14.5 fijado en .python-version. Biblioteca estÃ¡ndar exclusivamente (csv, sqlite3, unittest, etc.). uv 0.11.16 utilizado para entorno y lockfile; sin dependencias de modelado. UV_CACHE_DIR apunta a .uv-cache dentro del proyecto por permisos del entorno.',
        '## 20. Problemas encontrados',
        'Conteo de duplicados definido por igualdad textual de campos; representaciones numÃ©ricas equivalentes con distinto texto se consideran distintas. Nulos reconocidos como campos vacÃ­os o tokens nan/null/na/n/a, sin transformar datos. No se verificaron semÃ¡nticas externas ni periodicidad real de step. EstadÃ­sticos acumulados en coma flotante tienen error de redondeo. Identificadores Ãºnicos son exactos, sin interpretaciÃ³n de personas reales.',
        '## 21. Decisiones que requieren aprobaciÃ³n antes de continuar',
        'Autorizar expresamente una siguiente fase de modelado. Antes de esa fase definir instante de scoring, disponibilidad de balances, polÃ­tica sobre isFlaggedFraud, validaciÃ³n temporal dentro de step <= 400 y tratamiento de ratios con cero. No se continÃºa automÃ¡ticamente.', '', 'INITIAL DATA AUDIT: COMPLETE']
    return '\n\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=None)
    args = parser.parse_args()
    try:
        result = audit(raw_csv(ROOT, args.input))
        (ROOT/'reports').mkdir(exist_ok=True)
        (ROOT/'reports/audit_results.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        (ROOT/'INITIAL_DATA_AUDIT.md').write_text(report(result), encoding='utf-8')
        print(json.dumps({k: result[k] for k in ('rows','duplicates_exact','validation')}))
    except Exception as exc:
        (ROOT/'INITIAL_DATA_AUDIT.md').write_text(f'# INITIAL DATA AUDIT\n\nBloqueo: {type(exc).__name__}: {exc}\n\nINITIAL DATA AUDIT: BLOCKED\n', encoding='utf-8')
        raise

if __name__ == '__main__':
    main()
