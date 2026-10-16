"""Offline publication smoke checks, including a separate checkout directory."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    tracked = subprocess.check_output(['git', '-c', f'safe.directory={ROOT.as_posix()}',
                                      'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    tracked = list(filter(None, tracked))
    findings = []
    private = re.compile(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]+[A-Za-z0-9_.]|/(?:Users|home)/')
    secrets = re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----')
    for name in tracked:
        path = ROOT / name
        data = path.read_bytes()
        if path.stat().st_size > 10 * 1024 * 1024:
            findings.append(name + ': exceeds 10 MiB')
        if path.suffix in {'.db', '.sqlite', '.sqlite3'} or name.startswith(('mlruns/', 'mlartifacts/', 'data/raw/')) and not name.endswith('.gitkeep'):
            findings.append(name + ': prohibited store/raw')
        if path.suffix in {'.md', '.json', '.ipynb', '.html', '.py', '.toml', '.yml', '.yaml'}:
            text = data.decode('utf-8-sig')
            if private.search(text):
                findings.append(name + ': absolute path (review required)')
            if secrets.search(text):
                findings.append(name + ': secret candidate')
    print('Tracked security findings:', json.dumps(findings))
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / 'app/main.py'), default_timeout=60).run()
    for page in app.sidebar.radio[0].options:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, str(app.exception)
        assert not app.error, str(app.error)
        print('Dashboard OK:', page)
    from app.data_access import report_paths
    for name, path in report_paths(ROOT).items():
        text = path.read_text(encoding='utf-8').lower()
        assert '<html' in text and '</html>' in text, name
        print('HTML structure OK:', name, path.stat().st_size)
    target = ROOT / 'tmp/publication-portability'
    target.mkdir(parents=True, exist_ok=True)
    for name in tracked + ['publication_sanitization_manifest.json']:
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    env = os.environ.copy()
    env.pop('FRAUD_DATA_PATH', None)
    subprocess.run([sys.executable, str(target / 'scripts/verify_delivery.py'), '--notebooks'],
                   cwd=target, env=env, check=True)
    print('Portability without raw, processed data or local MLflow: OK')
    manifest = json.loads((ROOT / 'publication_sanitization_manifest.json').read_text())
    for name, record in manifest['files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == record['public_sha256']
    print('All public copy hashes: OK')
    originals = ROOT / 'private_publication_originals'
    if originals.is_dir():
        for name, record in manifest['files'].items():
            assert hashlib.sha256((originals / name).read_bytes()).hexdigest() == record['original_sha256']
        print('All original backup hashes: OK')
    else:
        print('Private originals intentionally excluded; original hashes recorded in manifest')
    if findings:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
