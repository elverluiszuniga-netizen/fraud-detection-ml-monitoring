"""Remove checkout prefixes in publication copies; preserve original bytes locally."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    paths = subprocess.check_output(
        ['git', '-c', f'safe.directory={ROOT.as_posix()}', 'ls-files', '-z'], cwd=ROOT
    ).decode().split('\0')
    prefixes = [str(ROOT), ROOT.as_posix()]
    prefixes += [json.dumps(p)[1:-1] for p in prefixes]
    backup = ROOT / 'private_publication_originals'
    manifest = {}
    for name in filter(None, paths):
        path = ROOT / name
        original = path.read_bytes()
        try:
            text = original.decode('utf-8')
        except UnicodeDecodeError:
            continue
        for prefix in sorted(set(prefixes), key=len, reverse=True):
            text = text.replace(prefix, '.')
        public = text.encode('utf-8')
        if public == original:
            continue
        saved = backup / name
        if saved.exists():
            raise RuntimeError('Original backup already exists: ' + name)
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(original)
        path.write_bytes(public)
        manifest[name] = {'original_sha256': digest(original), 'public_sha256': digest(public)}
    (ROOT / 'publication_sanitization_manifest.json').write_text(
        json.dumps({'transformation': 'Checkout prefix replaced by dot; all other bytes preserved.',
                    'files': manifest}, indent=2) + '\n', encoding='utf-8')
    print('Sanitized:', len(manifest), 'files')


if __name__ == '__main__':
    main()
