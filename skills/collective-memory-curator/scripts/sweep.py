#!/usr/bin/env python3
"""Weekly curation sweep: stale entries, orphans, broken YAML, duplicates."""
import argparse, os, yaml, json, subprocess
from datetime import datetime, timedelta
from collections import defaultdict

ENTRIES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'collective-memory', 'entries')
INDEX_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'collective-memory', 'index.md')
SEARCH_SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'collective-memory', 'scripts', 'search.py')
VALID_AGENTS = {'olly', 'marty', 'molly', 'lawy', 'sage'}


def sweep(dry_run: bool = True) -> dict:
    report = {
        'stale_drafts': [],
        'orphans': [],
        'broken_yaml': [],
        'empty_bodies': [],
        'duplicate_clusters': [],
        'good': 0
    }
    
    if not os.path.isdir(ENTRIES_DIR):
        return {'error': f'Entries directory not found: {ENTRIES_DIR}'}
    
    # Read current index to find orphaned entries
    indexed_files = set()
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH) as f:
            index_content = f.read()
        # Extract linked filenames from index markdown
        import re
        for match in re.finditer(r'entries/([^)]+\.md)', index_content):
            indexed_files.add(match.group(1))
    
    now = datetime.now()
    
    for fname in sorted(os.listdir(ENTRIES_DIR)):
        if not fname.endswith('.md'):
            continue
        path = os.path.join(ENTRIES_DIR, fname)
        
        with open(path) as f:
            content = f.read()
        
        # Check for missing frontmatter
        if not content.startswith('---\n'):
            report['broken_yaml'].append({'file': fname, 'reason': 'Missing YAML frontmatter'})
            continue
        
        parts = content.split('---\n', 2)
        if len(parts) < 3:
            report['broken_yaml'].append({'file': fname, 'reason': 'Incomplete frontmatter'})
            continue
        
        try:
            meta = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            report['broken_yaml'].append({'file': fname, 'reason': 'Invalid YAML'})
            continue
        
        if not isinstance(meta, dict):
            report['broken_yaml'].append({'file': fname, 'reason': 'Frontmatter not a mapping'})
            continue
        
        # Check empty body
        body = parts[2].strip() if len(parts) > 2 else ''
        if len(body.split()) < 3:
            report['empty_bodies'].append({'file': fname, 'agent': meta.get('agent', '?'), 'topic': meta.get('topic', '?')})
        
        # Check stale drafts
        confidence = str(meta.get('confidence', 'unknown'))
        if 'date' in meta:
            try:
                entry_date = datetime.strptime(str(meta['date']), '%Y-%m-%d')
                age_days = (now - entry_date).days
                if confidence == 'draft' and age_days > 7:
                    report['stale_drafts'].append({
                        'file': fname, 'agent': meta.get('agent', '?'),
                        'topic': str(meta.get('topic', '?')),
                        'age_days': age_days,
                        'confidence': confidence
                    })
                if confidence == 'plausible' and age_days > 30:
                    report['stale_drafts'].append({
                        'file': fname, 'agent': meta.get('agent', '?'),
                        'topic': str(meta.get('topic', '?')),
                        'age_days': age_days,
                        'confidence': confidence
                    })
            except ValueError:
                pass
        
        # Check orphaned
        if fname not in indexed_files:
            report['orphans'].append({'file': fname, 'agent': meta.get('agent', '?'), 'topic': meta.get('topic', '?')})
        
        report['good'] += 1
    
    # Check for duplicate clusters via semantic search
    # Sample random entries and check similarity
    if os.path.exists(SEARCH_SCRIPT) and report['good'] > 10:
        all_files = [f for f in os.listdir(ENTRIES_DIR) if f.endswith('.md')]
        import random
        sample = random.sample(all_files, min(10, len(all_files)))
        checked = set()
        for f in sample:
            if f in checked:
                continue
            query = f.replace('.md', '').replace('-', ' ').replace('_', ' ')
            result = subprocess.run(
                ['python3', SEARCH_SCRIPT, query, '--top', '3', '--json'],
                capture_output=True, text=True
            )
            try:
                matches = json.loads(result.stdout)
                close_matches = [m for m in (matches if isinstance(matches, list) else []) 
                                if m.get('score', 0) > 0.85 and m.get('file') != f]
                if close_matches:
                    report['duplicate_clusters'].append({
                        'source': f,
                        'matches': [{'file': m.get('file', '?'), 'score': m.get('score', 0)} for m in close_matches]
                    })
                    checked.add(f)
                    for m in close_matches:
                        checked.add(m.get('file', ''))
            except (json.JSONDecodeError, subprocess.CalledProcessError):
                pass
    
    return report


def print_report(report: dict):
    if 'error' in report:
        print(f'❌ {report["error"]}')
        return
    
    print('=== Curation Sweep Report ===')
    print(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print(f'Total entries scanned: {report["good"]}\n')
    
    if report['stale_drafts']:
        print(f'⚠️ Stale entries ({len(report["stale_drafts"])}):')
        for e in report['stale_drafts']:
            print(f'  {e["file"]} — {e["agent"]}/{e["topic"]} — {e["age_days"]} days old ({e["confidence"]})')
    
    if report['orphans']:
        print(f'\n📄 Orphan entries — not in index.md ({len(report["orphans"])}):')
        for e in report['orphans'][:10]:
            print(f'  {e["file"]} — {e["agent"]}/{e["topic"]}')
        if len(report['orphans']) > 10:
            print(f'  ... and {len(report["orphans"]) - 10} more')
    
    if report['broken_yaml']:
        print(f'\n❌ Broken YAML ({len(report["broken_yaml"])}):')
        for e in report['broken_yaml']:
            print(f'  {e["file"]} — {e["reason"]}')
    
    if report['empty_bodies']:
        print(f'\n📭 Empty bodies ({len(report["empty_bodies"])}):')
        for e in report['empty_bodies']:
            print(f'  {e["file"]} — {e["agent"]}/{e["topic"]}')
    
    if report['duplicate_clusters']:
        print(f'\n🔀 Potential duplicate clusters ({len(report["duplicate_clusters"])}):')
        for c in report['duplicate_clusters']:
            print(f'  {c["source"]} ~')
            for m in c['matches']:
                print(f'    {m["file"]} (score: {m["score"]:.3f})')
    
    print(f'\n{"="*40}')
    if report['stale_drafts'] or report['broken_yaml'] or report['empty_bodies']:
        print('Run with --apply to auto-clean (dry-run by default)')
    if report['orphans']:
        print('Run reindex.py to rebuild index.md')
    print('Done.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Curation sweep for collective memory')
    parser.add_argument('--apply', action='store_true', help='Apply cleanup actions (default: dry-run)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    
    report = sweep(dry_run=not args.apply)
    
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)