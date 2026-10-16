"""Audit every local Git object, including unreachable objects, without printing secrets."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import struct
import zlib

PRIVATE = re.compile(rb'(?<![A-Za-z0-9])[A-Za-z]:[\\/]+[A-Za-z0-9_.]|/(?:Users|home)/')
SECRET_PATTERNS = {
    'github': rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})',
    'aws': rb'(?:AKIA|ASIA)[A-Z0-9]{16}',
    'private_key': rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',
    'google_api': rb'AIza[A-Za-z0-9_-]{30,}',
    'slack': rb'xox[baprs]-[A-Za-z0-9-]{20,}',
    'literal_secret': rb'''(?i)(?:password|passwd|api_key|api_secret|access_token|auth_token|client_secret)\s*["']?\s*[:=]\s*["']([A-Za-z0-9_+/.=-]{20,})["']''',
    'url_credentials': rb'https?://[^\s/"\x27<>:@]+:[^\s/"\x27<>@]+@[^\s/"\x27<>]+',
}


def git(root, *args, input=None):
    return subprocess.check_output(['git', '-c', f'safe.directory={root.as_posix()}',
                                    '-C', str(root), *args], input=input)


def tree(root, ref):
    result = {}
    for entry in git(root, 'ls-tree', '-rz', ref).split(b'\0'):
        if entry:
            metadata, name = entry.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            result[name.decode()] = {'mode': mode, 'type': kind, 'oid': oid}
    return result


def prohibited(name):
    path = Path(name)
    return (path.suffix.lower() in {'.db', '.sqlite', '.sqlite3', '.pem', '.key', '.bundle'}
            or path.name == '.env' or path.name.startswith('.env.') and path.name != '.env.example'
            or path.name == 'PS_20174392719_1491204439457_log.csv'
            or any(name.startswith(prefix) and not name.endswith('.gitkeep') for prefix in
                   ('data/raw/', 'data/processed/', 'mlruns/', 'mlartifacts/',
                    'private_publication_originals/', '.venv/', 'optuna_studies/')))


def path_search_content(data):
    """Scan text and PNG metadata, not coincidental bytes in compressed pixels."""
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        chunks = []
        offset = 8
        while offset + 12 <= len(data):
            length = struct.unpack('>I', data[offset:offset + 4])[0]
            kind = data[offset + 4:offset + 8]
            payload = data[offset + 8:offset + 8 + length]
            if kind == b'tEXt':
                chunks.append(payload)
            elif kind == b'zTXt':
                key, value = payload.split(b'\0', 1)
                chunks.append(key + b'\0' + zlib.decompress(value[1:]))
            elif kind == b'iTXt':
                key, rest = payload.split(b'\0', 1)
                compressed = rest[0]
                language, translated, text = rest[2:].split(b'\0', 2)
                chunks.append(key + language + translated + (zlib.decompress(text) if compressed else text))
            offset += 12 + length
        return b'\n'.join(chunks)
    try:
        data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return b''
    return data


def audit(root):
    refs = git(root, 'for-each-ref', '--format=%(refname) %(objectname)').decode().splitlines()
    commits = git(root, 'rev-list', '--all', '--reverse').decode().splitlines()
    names = {}
    commit_paths = {}
    forbidden = []
    for commit in commits:
        entries = tree(root, commit)
        commit_paths[commit] = entries
        for name, entry in entries.items():
            names.setdefault(entry['oid'], set()).add(name)
            if prohibited(name):
                forbidden.append({'commit': commit, 'path': name})
            if entry['mode'] not in {'100644', '100755'}:
                forbidden.append({'commit': commit, 'path': name, 'reason': 'non-regular file'})
    inventory = git(root, 'cat-file', '--batch-all-objects',
                    '--batch-check=%(objectname) %(objecttype) %(objectsize)').decode().splitlines()
    wanted = []
    sizes = {}
    for line in inventory:
        oid, kind, size = line.split()
        sizes[oid] = (kind, int(size))
        if kind in {'blob', 'commit', 'tag'}:
            wanted.append(oid)
    packed = git(root, 'cat-file', '--batch', input=('\n'.join(wanted) + '\n').encode())
    offset = 0
    private = []
    secrets = []
    fixtures = []
    for oid in wanted:
        end = packed.index(b'\n', offset)
        header = packed[offset:end].decode().split()
        size = int(header[2])
        data = packed[end + 1:end + 1 + size]
        offset = end + 1 + size + 1
        paths = sorted(names.get(oid, []))
        hits = list(PRIVATE.finditer(path_search_content(data)))
        if hits:
            private.append({'oid': oid, 'type': header[1], 'paths': paths,
                            'occurrences': len(hits)})
        for label, expression in SECRET_PATTERNS.items():
            for match in re.finditer(expression, data):
                hit = {'oid': oid, 'paths': paths, 'kind': label,
                       'line': data.count(b'\n', 0, match.start()) + 1}
                if label == 'url_credentials' and match.group() == b'https://user:password@example.invalid':
                    fixtures.append(hit)
                else:
                    secrets.append(hit)
    private_ids = {record['oid'] for record in private}
    affected = []
    for commit in commits:
        files = [{'path': name, 'oid': entry['oid']} for name, entry in commit_paths[commit].items()
                 if entry['oid'] in private_ids]
        if files or commit in private_ids:
            affected.append({'commit': commit, 'private_files': files})
    reachable = {line.split()[0] for line in git(root, 'rev-list', '--objects', '--all').decode().splitlines()}
    result = {'refs': refs, 'commits': commits, 'object_count': len(inventory),
              'blob_count': sum(kind == 'blob' for kind, _ in sizes.values()),
              'largest_blob_bytes': max((size for kind, size in sizes.values() if kind == 'blob'), default=0),
              'unreachable_objects': sorted(set(sizes) - reachable),
              'private_objects': private, 'affected_commits': affected,
              'secret_candidates': secrets, 'synthetic_url_fixtures': fixtures,
              'prohibited_files': forbidden,
              'oversized_blobs': [oid for oid, (kind, size) in sizes.items()
                                  if kind == 'blob' and size > 10 * 1024 * 1024]}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--allow-private-paths', action='store_true',
                        help='For auditing a private source repository only')
    args = parser.parse_args()
    result = audit(Path.cwd().resolve())
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: len(result[key]) for key in ('commits', 'private_objects',
          'affected_commits', 'secret_candidates', 'prohibited_files', 'unreachable_objects')}))
    if result['secret_candidates'] or result['prohibited_files'] or result['oversized_blobs']:
        raise SystemExit(1)
    if result['private_objects'] and not args.allow_private_paths:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
