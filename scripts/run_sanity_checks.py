"""Verify persisted Phase 2 provenance and explain near deterministic separation."""
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from fraud_detection.paths import raw_csv
from fraud_detection.features import engineer_features, MODEL_COLUMNS
from fraud_detection.metrics import evaluate
from fraud_detection.optimization import DevelopmentData


def file_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(2**20), b''): digest.update(block)
    return digest.hexdigest()


def load_development(root: Path = ROOT):
    location = root / 'data/processed'
    data=DevelopmentData(np.load(location/'train_X.npy',mmap_mode='r'),np.load(location/'train_y.npy'),
                         np.load(location/'validation_X.npy',mmap_mode='r'),np.load(location/'validation_y.npy'))
    data.validate()
    return data


def verify_provenance(path: Path, data: DevelopmentData) -> dict:
    """Regenerate every Development row using row-local, target-independent features."""
    data.validate()
    offsets={'train':0,'validation':0}
    arrays={'train':(data.x_train,data.y_train),'validation':(data.x_validation,data.y_validation)}
    invariant_checked=False
    for chunk in pd.read_csv(path,chunksize=250_000):
        dev=chunk.loc[chunk.step.between(1,400)]
        for name,low,high in (('train',1,320),('validation',321,400)):
            part=dev.loc[dev.step.between(low,high)]
            if part.empty: continue
            x,y=arrays[name]; offset=offsets[name]; stop=offset+len(part)
            expected=engineer_features(part).to_numpy(dtype='float32')
            if not np.array_equal(expected,x[offset:stop]) or not np.array_equal(part.isFraud.to_numpy(),y[offset:stop]):
                raise ValueError('Persisted matrices differ from target-independent raw Development reconstruction')
            offsets[name]=stop
        if not invariant_checked and len(dev):
            sample=dev.iloc[:1000].copy(); altered=sample.copy()
            altered['isFraud']=1-sample.isFraud; altered['isFlaggedFraud']=1-sample.isFlaggedFraud
            altered['newbalanceOrig']=np.nan; altered['newbalanceDest']=np.nan; altered['nameOrig']='arbitrary'
            altered['nameDest']=sample.nameDest.str[:1]+'arbitrary'
            if not engineer_features(sample).equals(engineer_features(altered)):
                raise ValueError('Feature output depends on prohibited columns')
            invariant_checked=True
    if offsets != {'train':len(data.y_train),'validation':len(data.y_validation)}:
        raise ValueError('Raw/matrix row count mismatch')
    return dict(verified_rows=offsets,exact_reconstruction=True,prohibited_column_mutation_invariant=invariant_checked,
                train_steps=[1,320],validation_steps=[321,400],shared_rows=False,
                shared_rows_evidence='Strictly disjoint step values; exact rows include step; Phase 1 found no exact duplicates',
                production_used=False,feature_names=list(MODEL_COLUMNS),
                preprocessing_review='Row-local features have no fit; logistic StandardScaler fitted by Pipeline on Train only')


def analyze_rules(x,y):
    col={name:x[:,i] for i,name in enumerate(MODEL_COLUMNS)}
    risky=(col['type_TRANSFER']==1)|(col['type_CASH_OUT']==1)
    emptied=col['orig_balance_emptied']==1
    rules={
        'TRANSFER':col['type_TRANSFER']==1,
        'CASH_OUT':col['type_CASH_OUT']==1,
        'TRANSFER_or_CASH_OUT':risky,
        'origin_zero':col['orig_balance_zero']==1,
        'amount_approximately_prior_balance':emptied,
        'ratio_approximately_one_positive_balance':(np.abs(col['amount_to_oldbalanceOrg']-1)<=1e-6)&(col['oldbalanceOrg']>0),
        'risky_type_and_requested_emptying':risky&emptied,
    }
    return [dict(rule=name,**evaluate(y,score.astype(float))) for name,score in rules.items()]


def markdown_table(frame):
    columns=list(frame.columns)
    lines=['| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']
    for row in frame.itertuples(index=False,name=None):
        lines.append('| '+' | '.join(f'{v:.8f}' if isinstance(v,float) else str(v) for v in row)+' |')
    return '\n'.join(lines)


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    start=time.perf_counter(); data=load_development()
    evidence=verify_provenance(raw_csv(ROOT),data)
    logging.info('Exact Development matrix reconstruction passed')
    univariate=[]; rules=[]
    for segment,x,y in (('train',data.x_train,data.y_train),('validation',data.x_validation,data.y_validation)):
        for i,feature in enumerate(MODEL_COLUMNS):
            score=x[:,i]
            # Report both predetermined directions; no model feature choice is made using these results.
            univariate.append(dict(segment=segment,feature=feature,pr_auc_high=average_precision_score(y,score),
                pr_auc_low=average_precision_score(y,-score),roc_auc_high=roc_auc_score(y,score)))
        rules.extend(dict(segment=segment,**r) for r in analyze_rules(x,y))
    uf=pd.DataFrame(univariate); rf=pd.DataFrame(rules)
    uf.to_csv(ROOT/'artifacts/sanity_univariate_features.csv',index=False)
    rf.to_csv(ROOT/'artifacts/sanity_simple_rules.csv',index=False)
    evidence['matrix_sha256']={p.name:file_hash(p) for p in (ROOT/'data/processed').glob('*_[Xy].npy')}
    evidence['phase2_source_sha256']={p.as_posix():file_hash(ROOT/p) for p in map(Path,[
        'src/fraud_detection/features.py','src/fraud_detection/modeling.py','scripts/run_baselines.py','PHASE_2_MODELING_REPORT.md'])}
    profile=pd.read_csv(ROOT/'artifacts/development_temporal_profile.csv')
    evidence['all_fraud_development_steps']=int((profile.fraud_rate==1).sum())
    evidence['all_fraud_step_transactions']=int(profile.loc[profile.fraud_rate==1,'transactions'].sum())
    evidence['seconds']=time.perf_counter()-start
    evidence['conclusion']='B: No implementation leakage detected; near-deterministic simulator patterns. C: Operational availability and external validity remain uncertain.'
    (ROOT/'artifacts/phase3_sanity.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    lines=['# Perfect performance sanity check','',
        'All checks use Development only. Every saved model-matrix row and target was reconstructed from raw rows at steps 1–400; arrays were not rewritten. Train steps 1–320 and Validation steps 321–400 are strictly disjoint.',
        '## Leakage evidence',json.dumps(evidence,indent=2),
        'The fixed MODEL_COLUMNS list excludes isFraud, isFlaggedFraud, raw IDs, new balances and every post-event derivative. Raw reconstruction confirms columns were not replaced by accidental target-derived data. Mutating labels, flags, post-event balances and IDs (preserving only destination prefix) leaves features identical. Source review confirms no fitted transformer spans Train and Validation. This provides evidence against implementation leakage, not proof that the simulator contains no target-related shortcuts.',
        '## Univariate separation',
        'Both high and low score directions are reported descriptively. AP for binary features is based on only two score groups and is not equivalent to precision among positive-feature rows. Constant features return prevalence AP and ROC 0.5. These checks do not select or remove model predictors.',
        markdown_table(uf),
        '## Simple rules',
        'Rules use fixed tolerances from Phase 2 and no learned thresholds. The ratio check uses a prespecified 1e-6 diagnostic tolerance on stored float32; the emptied feature itself was computed from raw float64 with absolute monetary tolerance 0.01. Rules with incomplete recall or false positives explain most separation without being equivalent to the label.',
        markdown_table(rf[['segment','rule','pr_auc','precision_05','recall_05','tp','fp','tn','fn']]),
        '## Conclusion',
        'A. No implementation evidence of direct target, business-rule, post-event, identifier or temporal leakage was detected.',
        'B. Near-deterministic simulator patterns are present: requested account emptying and transaction type sharply separate the target. Low-volume steps can contain only fraud, adding a simulation scheduling shortcut. This explains why very high AP is plausible without prohibited predictors.',
        'C. Pending uncertainty: pre-execution balance availability and merchant-prefix semantics in a real system; simulation label-generation mechanisms; single-holdout stability; external transferability and score calibration. A dataset-level generator shortcut cannot be ruled out by an implementation audit. Do not infer extraordinary real-world performance.',
        'The same Validation will subsequently support tuning and early stopping as authorized. Its final scores will then be development-selection estimates, not independent unbiased test evidence. Production remains reserved.']
    (ROOT/'docs/perfect_performance_sanity_check.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')
    logging.info('Sanity complete in %.1fs',evidence['seconds'])
    print(rf.loc[rf.rule=='risky_type_and_requested_emptying',['segment','precision_05','recall_05','tp','fp','fn']].to_string(index=False))

if __name__=='__main__':main()
