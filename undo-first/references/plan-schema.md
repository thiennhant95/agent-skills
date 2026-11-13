# Undo Plan Schema (JSON)

One plan per action. The gate (`undo_guard.py plan`) validates structure deterministically — plans are **data**, the engine never executes their contents.

## Template

```json
{
  "action": {
    "type": "file_write",
    "description": "Overwrite reports/summary.md with the new quarterly summary",
    "target": "reports/summary.md"
  },
  "risk": "medium",
  "undo": {
    "kind": "builtin_restore",
    "steps": ["python3 scripts/undo_guard.py restore <snapshot-id>"],
    "snapshot": "<snapshot-id>"
  },
  "verify": {
    "check": "sha256 of reports/summary.md equals the snapshot manifest entry"
  }
}
```

## Fields

### `action` (required)
| Field | Values | Notes |
|---|---|---|
| `type` | `file_write`, `file_delete`, `file_move`, `dir_change`, `config_change` (file class) · `git_push`, `external_message`, `deploy`, `api_call`, `payment`, `publish`, `delete_remote` (irreversible class) | Unknown values → REJECT |
| `description` | free text | Missing → warning (journal becomes unauditable) |
| `target` | path / endpoint | optional but recommended |

### `risk` (required)
`low` | `medium` | `high` | `critical` — how hard to recover if the action is wrong.

### `undo` (required)
| `kind` | When to use | Gate requirements |
|---|---|---|
| `builtin_restore` | Anything on disk — snapshot taken first | none beyond file class; `verify.check` warned for `critical` |
| `commands` | Documented rollback exists (git revert, deploy rollback) | `steps` non-empty **and** `verify.check` present |
| `compensation` | Irreversible in the real world (email, payment, publish) | mandatory for the irreversible class; `steps` non-empty |
| `none` | Trivially reproducible, low risk only | `risk=low` → ACCEPT_WITH_WARNING; `risk≥medium` → REJECT |

`steps`: array of concrete rollback/mitigation instructions (for the agent/human — the engine does not run them).
`snapshot`: snapshot id when `kind=builtin_restore`.

### `verify` (required for `commands`, warned for `critical`)
`check`: how to prove the rollback actually restored the desired state (hash comparison, API status, confirmed receipt…).

## Gate outcomes

| Verdict | Exit | Meaning |
|---|---|---|
| ACCEPT | 0 | Action may proceed |
| ACCEPT_WITH_WARNING | 1 | Proceed only after acknowledging the warning |
| REJECT | 2 | **Do not act.** Build an undo path or get explicit user acceptance of the risk |

Every gate decision is appended to `.undo-journal/journal.jsonl` with the full plan — the audit trail is the evidence that the decision was made before the action, not after.
