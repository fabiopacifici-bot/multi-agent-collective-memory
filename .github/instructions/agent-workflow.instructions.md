---
description: "Use when implementing features, routes, bug fixes, or refactors in this repository. Enforces issue-based branching from dev, isolated feature branches, per-feature commits, BRIEF progress updates, and no direct push/merge to main without review."
name: "Project Agent Workflow"
---
# Project Agent Workflow

- Create or reference one issue per task before implementation.
- Start from dev, then create one isolated branch per feature or route.
- Use branch naming consistent with task scope (for example: feature/<name>, issue-<id>, fix/<name>). 
- Do not work directly on main.
- Commit after each completed feature with clear, specific messages.
- After each feature commit, update BRIEF.md progress status and commit hash.
- Keep changes scoped to the active feature branch.
- Merge back to dev only after feature completion and validation.
- Never push automatically; push only after user approval.
- Never merge dev to main without explicit review/approval.

## Required Reporting After Each Feature

- Report branch name used.
- Report commit hash and short description.
- Report BRIEF.md progress row update.

## Safety Rules

- Do not revert unrelated user changes.
- If working tree is dirty, inspect and preserve non-related changes.
- If unexpected file loss or branch mismatch is detected, stop and verify git state before continuing.
