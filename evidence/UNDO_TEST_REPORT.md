# Undo-First Guard — Verification & Evidence Report

**Skill:** `undo-first/` (SKILL.md + guard engine + test harness)
**Version:** undo_guard 1.0.0 · run 2026-11-13 (UTC)
**Philosophy:** No undo path, no action.

---

## 1. What was built

Reversible-action infrastructure for AI agents:

- **`snapshot`** — sha256 manifest + backup copies of target state (`.undo-journal/`)
- **`plan`** — deterministic risk gate over JSON undo plans: irreversible actions demand a `compensation` plan; file actions at risk ≥ medium demand `builtin_restore` or verified rollback `commands`; unknown action types are rejected outright
- **`verify`** — diff current state vs snapshot (changed/deleted/intact)
- **`restore`** — rollback from own backups, verified BOTH directions: backup sha256 must equal the manifest before restore (tamper → REFUSED) and the restored file must be byte-identical after
- **`journal`** — append-only audit trail (snapshot / plan_gate / verify / restore decisions)
- **`selfcheck`** — proves the engine's own source contains zero execution primitives (plans are data, never code)

## 2. Harness results (12 cases, `python3 tests/test_undo_guard.py`)

### Restoration — byte-identical proof (sha256)

| Case | Scenario | Result |
|---|---|---|
| S1 | file modified → restore | ✅ sha256 identical |
| S2 | file deleted → restore | ✅ recovered from deletion |
| S3 | multi-file tree mutation (modify + delete + append) → restore | ✅ full tree sha256 map identical (3 files) |
| S4 | **backup tampered by attacker → restore** | ✅ REFUSED (sha256 mismatch detected) |

### Risk gate — deterministic decisions

| Case | Scenario | Expected | Result |
|---|---|---|---|
| S5 | `external_message`, undo=none | REJECT | ✅ exit 2, demands compensation |
| S6 | `external_message` + compensation steps | ACCEPT | ✅ exit 0 |
| S7 | `file_delete`, risk=medium, undo=none | REJECT | ✅ exit 2 |
| S8 | `file_delete` + builtin_restore + snapshot | ACCEPT | ✅ exit 0 |
| S9 | `git_push` kind=commands, no steps/verify | REJECT | ✅ exit 2 |
| S10 | unknown action type | REJECT | ✅ exit 2 |

### Safety invariants

| Case | Result |
|---|---|
| S11 engine contains zero execution primitives (`os.system`, `subprocess`, `eval(`, …) | ✅ selfcheck PASSED |
| S12 journal records snapshot/restore/plan_gate decisions (audit trail) | ✅ verified in both journals |

**RESULT: 12/12 (100%) — OVERALL PASS.** Machine-readable: `evidence/undo_test_results.json`.

## 3. Dogfood — real risky task on workspace

Realistic scenario: rewrite release notes + delete an obsolete draft (risk=high).

```
1) snapshot   20261113T152150856449Z — 2 files, sha256-verified backups
2) plan gate  ACCEPT (builtin_restore + verify.check provided)
3) action     file corrupted + draft deleted (simulating a bad run)
4) verify     CHANGED RELEASE_NOTES.md · DELETED draft_old.md  (detected precisely)
5) restore    RESTORED (byte-identical, sha256 verified) × 2
6) result     STATE FULLY RECOVERED ✅
7) journal    snapshot → plan_gate → verify → restore, fully timestamped
```

## 4. Honest limitations

- Restore covers file-level state; remote-world actions (email/deploy/payment) rely on `compensation` steps that the agent executes — the gate validates their presence and structure, not their quality.
- Snapshots consume disk proportional to target size.
- The risk gate is structural: it can demand an undo path but cannot judge whether a rollback command truly works in a given environment — `verify.check` exists for that judgment.

## 5. Reproduction

```bash
cd undo-first
python3 scripts/undo_guard.py selfcheck          # zero-execution-primitives proof
python3 tests/test_undo_guard.py                 # 12/12 harness
python3 scripts/undo_guard.py snapshot <paths>   # capture state
python3 scripts/undo_guard.py plan <plan.json>   # risk gate (exit 0/1/2)
python3 scripts/undo_guard.py restore <id>       # verified rollback
```
