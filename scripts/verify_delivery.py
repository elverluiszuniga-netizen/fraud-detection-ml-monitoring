"""Read-only delivery checks and notebook execution; never trains or rewrites evidence."""
import argparse
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from fraud_detection.paths import raw_csv, champion_path


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(root=ROOT, check_raw=False):
    root = Path(root)
    freeze = json.loads((root / 'artifacts/production_monitoring_freeze.json').read_text())
    publication = json.loads((root / 'publication_sanitization_manifest.json').read_text())['files']
    for relative, record in publication.items():
        if digest(root / relative) != record['public_sha256']:
            raise ValueError('Publication copy changed: ' + relative)
    if digest(champion_path(root)) != freeze['model_sha256']:
        raise ValueError('Champion hash mismatch')
    for relative, expected in freeze['previous_phase_hashes'].items():
        if relative in publication:
            record = publication[relative]
            if record['original_sha256'] != expected:
                raise ValueError('Historical provenance mismatch: ' + relative)
            expected = record['public_sha256']
        if digest(root / relative) != expected:
            raise ValueError('Historical evidence changed: ' + relative)
    from app.data_access import load_bundle, report_paths
    load_bundle(root)
    if not all(path.is_file() for path in report_paths(root).values()):
        raise FileNotFoundError('HTML report missing')
    if check_raw:
        manifest = json.loads((root / 'data/dataset_manifest.json').read_text())
        path = raw_csv(root)
        if path.stat().st_size != manifest['bytes'] or digest(path) != manifest['sha256']:
            raise ValueError('Original CSV hash mismatch')
    print('Delivery artifacts, frozen model and historical evidence: OK')


def notebooks():
    """Execute trusted artifact-presentation cells without writing existing outputs."""
    os.chdir(ROOT)
    for path in sorted((ROOT / 'notebooks').glob('*.ipynb')):
        notebook = json.loads(path.read_text(encoding='utf-8'))
        scope = {}
        count = 0
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            for cell in notebook['cells']:
                if cell['cell_type'] == 'code':
                    count += 1
                    exec(compile(''.join(cell['source']), str(path), 'exec'), scope)
        print(path.name + ': ' + str(count) + ' cells OK (no output files written)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw', action='store_true', help='Hash the original CSV (~500 MB)')
    parser.add_argument('--notebooks', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    verify(check_raw=args.raw)
    if args.notebooks:
        notebooks()


if __name__ == '__main__':
    main()
