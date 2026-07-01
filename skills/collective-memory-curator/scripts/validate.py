#!/usr/bin/env python3
"""Validate a collective memory entry against schema."""
import argparse, sys, yaml, json, os, re
from datetime import datetime

VALID_AGENTS = {'olly', 'marty', 'molly', 'lawy', 'sage'}
VALID_CONFIDENCE = {'confirmed', 'plausible', 'draft'}

ENTRIES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'collective-memory', 'entries')


def validate_entry(content: str, source: str = 'unknown') -> dict:
    errors = []
    warnings = []
    
    if not content.startswith('---\n'):
        return {'valid': False, 'errors': ['Missing YAML frontmatter (must start with ---)']}
    
    parts = content.split('---\n', 2)
    if len(parts) < 3:
        return {'valid': False, 'errors': ['Incomplete YAML frontmatter']}
    
    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return {'valid': False, 'errors': [f'Invalid YAML: {e}']}
    
    if not isinstance(meta, dict):
        return {'valid': False, 'errors': ['Frontmatter must be a YAML mapping']}
    
    for field in ('date', 'agent', 'topic'):
        if field not in meta:
            errors.append(f'Missing required field: {field}')
    
    if 'date' in meta:
        try:
            datetime.strptime(str(meta['date']), '%Y-%m-%d')
        except ValueError:
            errors.append(f'Invalid date format: "{meta["date"]}" — must be YYYY-MM-DD')
    
    if 'agent' in meta and meta['agent'] not in VALID_AGENTS:
        errors.append(f'Unknown agent: "{meta["agent"]}" — must be one of {VALID_AGENTS}')
    
    if 'topic' in meta and len(str(meta['topic'])) > 50:
        errors.append(f'Topic too long ({len(str(meta["topic"]))} chars, max 50)')
    
    if 'tags' in meta:
        tags = meta['tags']
        if not isinstance(tags, list):
            errors.append('tags must be a list')
        elif len(tags) < 1:
            warnings.append('tags list is empty')
        elif len(tags) > 5:
            errors.append(f'Too many tags ({len(tags)}, max 5)')
        for t in (tags if isinstance(tags, list) else []):
            if len(str(t)) > 30:
                errors.append(f'Tag too long: "{t}" ({len(str(t))} chars, max 30)')
    
    if 'confidence' in meta:
        if meta['confidence'] not in VALID_CONFIDENCE:
            errors.append(f'Invalid confidence: "{meta["confidence"]}" — must be one of {VALID_CONFIDENCE}')
    
    body = parts[2].strip() if len(parts) > 2 else ''
    word_count = len(body.split())
    if word_count < 3:
        errors.append('Body too short (min 3 words)')
    elif word_count > 500:
        warnings.append(f'Body long ({word_count} words)')
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'source': source,
        'word_count': word_count,
        'agent': meta.get('agent', 'unknown'),
        'topic': meta.get('topic', 'unknown'),
        'date': str(meta.get('date', 'unknown')),
        'confidence': meta.get('confidence', 'unknown'),
        'tags': meta.get('tags', [])
    }


def validate_file(path: str) -> dict:
    with open(path) as f:
        content = f.read()
    return validate_entry(content, source=path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Validate collective memory entries')
    parser.add_argument('target', nargs='?', help='File path')
    parser.add_argument('--all', action='store_true', help='Validate all entries')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    
    results = []
    
    if args.all:
        if not os.path.isdir(ENTRIES_DIR):
            print(json.dumps({'error': f'Entries directory not found: {ENTRIES_DIR}'}))
            sys.exit(1)
        for fname in sorted(os.listdir(ENTRIES_DIR)):
            if fname.endswith('.md'):
                path = os.path.join(ENTRIES_DIR, fname)
                results.append(validate_file(path))
    elif args.target:
        results.append(validate_file(args.target))
    else:
        parser.print_help()
        sys.exit(1)
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            status = '✅' if r['valid'] else '❌'
            print(f"{status} {r['source']}")
            for e in r.get('errors', []):
                print(f'  ✗ {e}')
            for w in r.get('warnings', []):
                print(f'  ⚠ {w}')
        total = len(results)
        valid = sum(1 for r in results if r['valid'])
        print(f'\n{valid}/{total} valid')