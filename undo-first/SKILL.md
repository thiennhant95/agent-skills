---
name: undo-first
description: Reversible-action infrastructure for AI agents. Use before any side-effecting action (writing/deleting/moving files, config changes, git pushes, sending messages, deploys, API calls) when the user asks "can we roll this back?", "make this safe to try", or when executing risky multi-step work. Provides hash-verified snapshots, a risk gate that demands an undo or compensation plan before acting, byte-identical restore, and an audit journal. Philosophy - no undo path, no action.
---

# Undo-First Guard

**No undo path, no action.** Every side effect gets a verified way back — or it does not happen.

## The workflow (always in this order)

1. **Classify** the action: `file_write | file_delete | file_move | dir_change | config_change | git_push | external_message | deploy | api_call | payment | publish`
2. **Snapshot** file-level state before acting:
   ```bash
   python3 scripts/undo_guard.py snapshot <paths...>
   ```
   Stores sha256 manifest + backup copies under `.undo-journal/`. For non-file actions, skip snapshot.
3. **Write the undo plan** (JSON, schema: [references/plan-schema.md](references/plan-schema.md)) and pass the gate:
   ```bash
   python3 scripts/undo_guard.py plan my-plan.json
   ```
   Exit `0` ACCEPT · `1` ACCEPT_WITH_WARNING · `2` REJECT. **A REJECT means do not perform the action** — either build the undo path or ask the user to accept the risk explicitly.
4. **Act** (the agent performs the action).
5. **Verify / restore** if anything goes wrong:
   ```bash
   python3 scripts/undo_guard.py verify <snapshot-id>   # what changed since snapshot?
   python3 scripts/undo_guard.py restore <snapshot-id>  # byte-identical rollback
   ```
   Restore is sha256-verified both ways: backups are checked against the manifest before restoring (tamper → REFUSED) and after (restored file must be byte-identical).
6. **Journal** — every decision is already recorded; show it when asked:
   ```bash
   python3 scripts/undo_guard.py journal
   ```

## Risk-gate rules (deterministic)

- **Irreversible actions** (`external_message`, `deploy`, `api_call`, `payment`, `publish`, `delete_remote`) require `undo.kind = "compensation"` with concrete mitigation steps — the gate REJECTS "none" or bare "commands". An email cannot be unsent; the plan must say what makes it right.
- **File actions at risk ≥ medium** require `builtin_restore` (snapshot taken) or rollback `commands` with a `verify.check`.
- **`undo.kind = "commands"`** requires non-empty steps AND `verify.check` proving restoration.
- **Unknown action type → REJECT.** Classify first.
- Low-risk file actions with no undo path get ACCEPT_WITH_WARNING (exit 1) — reproduce-only-if-trivial.

## Safety invariants of this tool

The engine itself never executes anything found in plans or files — plans are **data, not code**. Prove it any time:

```bash
python3 scripts/undo_guard.py selfcheck
```

It scans its own source for execution primitives (`os.system`, `subprocess`, `eval(`, …) and reports each as absent. Tampered backups are refused by design (S4 in the harness).

## Choosing undo.kind

| Situation | kind |
|---|---|
| Files/dirs/config on disk | `builtin_restore` (snapshot first — tool restores) |
| Git/deploy where a documented rollback command exists | `commands` + `verify.check` |
| Email, messages, payments, publishes (cannot be unsent) | `compensation` (mitigation steps) |
| Trivially reproducible, low risk | `none` (exit 1 warning) |

## Verification

```bash
python3 tests/test_undo_guard.py
```

12 cases: modify/delete/multi-file restore proven **byte-identical by sha256**, tampered-backup refusal, 6 risk-gate decisions, zero-execution-primitives selfcheck, journal audit trail. Evidence JSON is written to `../evidence/undo_test_results.json`.

## Limitations

- Restore covers file-level state only; remote-world actions rely on `compensation` plans executed by the agent.
- Snapshots consume disk proportional to target size; snapshot specific paths, not whole disks.
- The risk gate validates plan *structure*, not the quality of compensation steps — write them concretely (who, what, by when).
