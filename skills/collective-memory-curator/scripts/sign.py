#!/usr/bin/env python3
"""Add provenance stamp to a collective memory entry."""
import argparse, os, yaml, hashlib
from datetime import datetime, timezone

VALID_AGENTS = {'olly', 'marty', 'molly', 'lawy', 'sage'}


def sign_file(path: str, agent: str = None) -> dict:
    if not os.path.exists(path):
        return {'error': f'File not found: {path}'}
    
    with open(path) as f:
        content = f.read()
    
    if not content.startswith('---\n'):
        return {'error': 'Missing YAML frontmatter'}
    
    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return {'error': 'Incomplete frontmatter'}
    
    meta = yaml.safe_load(parts[1])
    if not isinstance(meta, dict):
        return {'error': 'Invalid frontmatter'}
    
    if agent is None:
        agent = meta.get('agent', 'unknown')
    
    if agent not in VALID_AGENTS:
        return {'error': f'Unknown agent: {agent}. Must be one of {VALID_AGENTS}'}
    
    # Hash content before signature (body text only, skip frontmatter)
    body = parts[2].strip()
    content_hash = hashlib.sha256(body.encode()).hexdigest()[:16]
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    signature = f'{agent}:{timestamp}:{content_hash}'
    
    # Add or update signature in frontmatter
    meta['signature'] = signature
    
    # Rebuild file
    new_frontmatter = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()
    rebuilt = f'---\n{new_frontmatter}\n---\n\n{body}\n'
    
    with open(path, 'w') as f:
        f.write(rebuilt)
    
    return {'signed': True, 'agent': agent, 'timestamp': timestamp, 'hash': content_hash, 'signature': signature}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sign a collective memory entry')
    parser.add_argument('path', help='Path to entry file')
    parser.add_argument('--agent', help='Agent ID (default: from frontmatter)')
    args = parser.parse_args()
    
    result = sign_file(args.path, args.agent)
    if 'error' in result:
        print(f'❌ {result["error"]}')
        sys.exit(1)
    print(f'✅ Signed: {args.path}')
    print(f'   Signature: {result["signature"]}')