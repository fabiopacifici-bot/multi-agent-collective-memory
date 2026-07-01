#!/usr/bin/env python3
"""Verify provenance stamp on a collective memory entry."""
import argparse, os, yaml, hashlib, sys


def verify_file(path: str) -> dict:
    if not os.path.exists(path):
        return {'error': f'File not found: {path}'}
    
    with open(path) as f:
        content = f.read()
    
    if not content.startswith('---\n'):
        return {'valid': False, 'error': 'Missing YAML frontmatter'}
    
    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return {'valid': False, 'error': 'Incomplete frontmatter'}
    
    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return {'valid': False, 'error': 'Invalid YAML'}
    
    if not isinstance(meta, dict):
        return {'valid': False, 'error': 'Frontmatter not a mapping'}
    
    if 'signature' not in meta:
        return {'valid': False, 'error': 'No signature found. Use sign.py first.'}
    
    stored_signature = meta['signature']
    parts_sig = stored_signature.split(':', 2)
    if len(parts_sig) < 3:
        return {'valid': False, 'error': 'Malformed signature'}
    
    stored_agent = parts_sig[0]
    stored_timestamp = parts_sig[1]
    stored_hash = parts_sig[2]
    
    # Recompute hash from body
    body = parts[2].strip()
    computed_hash = hashlib.sha256(body.encode()).hexdigest()[:16]
    
    matches = stored_hash == computed_hash
    agent_match = stored_agent == meta.get('agent', '')
    
    return {
        'valid': matches and agent_match,
        'file': path,
        'signature': stored_signature,
        'signed_by': stored_agent,
        'signed_at': stored_timestamp,
        'agent_match': agent_match,
        'content_integrity': matches,
        'current_agent': meta.get('agent', 'unknown')
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Verify signature on a collective memory entry')
    parser.add_argument('path', help='Path to entry file')
    args = parser.parse_args()
    
    result = verify_file(args.path)
    
    if 'error' in result:
        print(f'❌ {result["error"]}')
        sys.exit(1)
    
    if result['valid']:
        print(f'✅ Signature valid')
        print(f'   Signed by: {result["signed_by"]} at {result["signed_at"]}')
        print(f'   Content integrity: ✅ intact')
        print(f'   Agent match: ✅ {result["signed_by"]} == {result["current_agent"]}')
    else:
        print(f'❌ Signature INVALID')
        if not result.get('content_integrity'):
            print(f'   Content has been modified since signing (hash mismatch)')
        if not result.get('agent_match'):
            print(f'   Agent mismatch: signed by {result["signed_by"]}, current is {result["current_agent"]}')