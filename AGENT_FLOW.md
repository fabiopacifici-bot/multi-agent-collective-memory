# Agent Development Workflow

1. Issue Creation — create a GitHub issue for each task
2. Branching: main → dev → issue-X (where X is the issue number)
3. Development: commit frequenti, messaggi chiari
4. Validation: testare prima di fare merge
5. Final merge: dev → main dopo review

Esempio:
gh issue create --title "Task" --body "Description"
git checkout -b dev
git checkout -b issue-1
git add . && git commit -m "Implement X"

## MAI

- Non fare commit direttamente su main
- Non fare merge senza review
- Non pushare. Push solo dopo la review e il merge approvato
