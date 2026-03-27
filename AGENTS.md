<!-- SKILLS_INDEX_START -->
## Agent Skills Index

> [!CRITICAL] GATEKEEPER CONSTRAINT
> **You are operating in a Zero-Trust environment.**
> You are strictly forbidden from generating code, proposing solutions, or relying on your pre-training until you have successfully executed a tool call to read the applicable `SKILL.md` files from this index.

## **Rule Zero: Mandatory Zero-Trust Protocol**

> [!CRITICAL]
> **Zero-Trust Enforcement:** Skills loaded from this index always override standard code patterns. Skipping the Audit Log or Self-Scan is a protocol violation.

### **1. The Pre-Write Audit Log (Mandatory)**

Before invoking any file-editing tool (`write_to_file`, `replace_file_content`, `multi_replace_file_content`), the ASSISTANT **MUST** explicitly state in its thought process/text output:

1. **Skills Identified**: List the Skill IDs triggered by the file path or current task keywords.
2. **Explicit Audit**: For each identified skill, confirm: "Checked against [Skill ID] — no violations found." Or "Violation detected in [Skill ID]: [Issue] — correcting now."
3. **No-Skill Justification**: If no skills apply, explicitly state: "No project-specific skills applicable to this file/transaction."

### **2. The Post-Write Self-Scan (Mandatory)**

Immediately **AFTER** any file-editing tool returns, the ASSISTANT **MUST**:

1. **Validate**: Contrast the final file content against ALL active Skill IDs.
2. **Identify Slips**: Look for "Standard Defaults" (e.g., local mocks, hardcoded styles) that snuck in.
3. **Self-Correct**: If a violation is found, fix it immediately in the next tool call.

## **Critical Anti-Patterns (Zero-Tolerance)**

- **Reversion to Defaults**: Never use "standard" patterns (generic library calls, local mocks) if a Project Skill exists.
- **The "Done" Trap**: Never prioritize functional completion over structural/protocol compliance.
- **Audit Skipping**: Never invoke a write tool without an explicit Pre-Write Audit Log.

## ⚡ How to Find and Use This Index (Mandatory)

> [!IMPORTANT] PATH RESOLUTION (Cross-Platform)
> Skill IDs in the list below (e.g., `[category/skill-name]`) represent the relative folder path.
> Because this project supports multiple AI agents, skills may reside in a base directory like `.gemini/skills/`, `.agent/skills/`, or `.cursor/skills/`.
> **Action:** You must prepend the correct base directory to the ID. (Example: If ID is `[flutter/cicd]`, the file is at `<BASE_DIR>/flutter/cicd/SKILL.md`). Use your file search tools (e.g., `list_directory` or `find`) if you are unsure of the base directory.

| Trigger Type | What to match | Required Action |
| --- | --- | --- |
| **File glob** (e.g. `**/*.ts`) | Files you are currently editing match the pattern | Call `view_file` on `<BASE_DIR>/[Skill ID]/SKILL.md` |
| **Keyword** (e.g. `auth`, `refactor`) | These words appear in the user\'s request | Call `view_file` on `<BASE_DIR>/[Skill ID]/SKILL.md` |
| **Composite** (e.g. `+other/skill`) | Another listed skill is already active | Also load this skill via `view_file` |

> [!TIP]
> **Indirect phrasing still counts.** Match keywords by intent, not just exact words.
> Examples: "make it faster" → `performance`, "broken query" → `database`, "login flow" → `auth`, "clean up this file" → `refactor`.



<!-- SKILLS_INDEX_END -->
