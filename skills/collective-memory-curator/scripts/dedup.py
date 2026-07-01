#!/usr/bin/env python3
"""Semantic dedup check for collective memory."""
import argparse, json, sys, os, subprocess

SEARCH_SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'collective-memory', 'scripts', 'search.py')


def check_dedup(query: str, threshold: float = 0.85, top_k: int = 5) -> list:
    if not os.path.exists(SEARCH_SCRIPT):
        print(json.dumps({'error': f'Search script not found: {SEARCH_SCRIPT}'}))
        sys.exit(1)
    
    result = subprocess.run(
        ['python3', SEARCH_SCRIPT, query, '--top', str(top_k), '--json'],
        capture_output=True, text=True
    )
    try:
        matches = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    
    dups = []
    for m in matches if isinstance(matches, list) else []:
        score = m.get('score', 0)
        if score >= threshold:
            dups.append(m)
    return dups


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check for duplicate collective memory entries')
    parser.add_argument('--query', required=True, help='Semantic query describing the new entry')
    parser.add_argument('--threshold', type=float, default=0.85, help='Similarity threshold (0-1)')
    parser.add_argument('--top', type=int, default=5, help='How many results to check')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    
    dups = check_dedup(args.query, args.threshold, args.top)
    
    if dups:
        if args.json:
            print(json.dumps(dups, indent=2))
        else:
            print(f'⚠️ Potential duplicates found ({len(dups)} matches above {args.threshold}):')
            for d in dups:
                print(f'  Score {d.get("score", 0):.3f} — {d.get("file", "?")}')
    else:
        if args.json:
            print(json.dumps({'matches': [], 'message': 'No duplicates found'}))
        else:
            print('✅ No duplicates found above threshold')