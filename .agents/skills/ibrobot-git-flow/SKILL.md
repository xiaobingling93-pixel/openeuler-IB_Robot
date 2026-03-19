---
name: ibrobot-git-flow
description: "Handles Git commit and push workflow for IB_Robot project and its submodule (libs/lerobot). Includes strict openEuler Embedded Commit Message compliance. Supports pushing root repo and submodule to their respective origin (personal fork) remotes."
---

# IB_Robot Git Workflow Guide

This skill automates code commit process for IB_Robot project (root repo with src directory) and its submodule `libs/lerobot`. The commit process enforces openEuler Embedded specification.

## Core Specifications

### 1. Commit Message Format
Must strictly follow this structure with exactly one blank line between sections:

```
<area>: <subject>

<body>

<footer_tags>
```

- **Title (<area>: <subject>)**:
  - Format: `<module>: <brief description>` (e.g., `robot_interface: fix moveit crash`).
  - Length limit: Non-revert commits max 80 chars, revert commits max 102 chars.
  - Subject must have at least 2 words, no trailing punctuation.
  - Exactly one space after colon.
  - No Chinese characters allowed.
- **Body**:
  - Must provide detailed description explaining "why" and "what".
  - Each line max 100 characters (unless containing URL).
  - No Chinese characters allowed.
- **Footer (Tags)**:
  - Must include `Signed-off-by: Name <email>`.
  - `Signed-off-by` must be the last line.
  - Allowed tags: `Fixes`, `Closes`, `Co-developed-by`, `Link`.
  - Tags must start with capital letter, one space after colon.
  - `Fixes` format: `Fixes: <12-char-SHA1>(<original-commit-title>)`.

### 2. Mandatory Requirements
- **All commits must be signed**: Use `git commit -s` to auto-add `Signed-off-by` to footer. Ensure this line is last.
- **Remote repositories**:
  - `origin`: Personal fork (for pushing code).
  - `upstream`: Main project repo (for submitting Pull Requests).

## Execution Steps

### Status Determination
If user explicitly requests **local commit only** (e.g., "commit to local", "only commit no push"), execute **only Phase 1, 2, and local commit part of Phase 3**. Skip push to remote, PR link, and PR description generation.

### Phase 1: Check and Summarize
1. Run `git status` in root directory and `libs/lerobot` separately.
2. Summarize pending changes to user.

### Phase 2: Compose Commit Message
1. Help user draft commit message (Title, Body, Footer) following specifications above.
2. **Validate**: Check title length, format, blank lines, and Chinese characters.

### Phase 3: Execute Commit and Push

For submodule `libs/lerobot` (if changed):
1. Change to directory -> `git add` -> `git commit -s`.
2. If NOT "local commit only":
   - Execute `git push origin <branch>`.
   - Record commit hash.

For root repository:
1. Return to root directory.
2. If submodule updated, run `git add libs/lerobot`.
3. Run `git add .` (includes `src` directory).
4. Run `git commit -s`.
5. If NOT "local commit only":
   - Execute `git push origin <branch>`.
   - **Get remote info**: Extract username and repo name via `git remote get-url origin`.
   - **Generate GitCode PR link**: Format `https://gitcode.com/<username>/IB_Robot/merge_requests/new?source_branch=<current-branch>`.
   - **Output PR description**: Compose detailed PR description from commit message body.

## Common Commands Reference
- Push to personal fork: `git push origin <branch>`
- Signed commit: `git commit -s` (opens editor or use -m flag)
- Undo last commit (keep changes): `git reset --soft HEAD~1`
