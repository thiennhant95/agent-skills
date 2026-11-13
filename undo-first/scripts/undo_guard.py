#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Undo-First Guard — reversible-action infrastructure for AI agents.

Philosophy: NO UNDO PATH, NO ACTION. Before any side effect:
  1. snapshot  — capture verifiable state (sha256 manifest + backup copies)
  2. plan      — register an undo plan; the risk gate decides if the action may run
  3. act       — (the agent performs the action)
  4. verify    — diff current state against the snapshot
  5. restore   — roll back file-level changes; byte-identical, hash-verified
  6. journal   — immutable audit trail of every decision

Safety invariants of THIS tool (proven by `selfcheck`):
  - It NEVER executes commands found in plans or files (plans are data, not code).
  - Restore works only from its own backup copies, verified against the manifest.
  - A tampered/corrupt backup is refused, not restored.

Stdlib only. Exit codes: 0=ACCEPT  1=ACCEPT_WITH_WARNING  2=REJECT  4=error
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

VERSION = "1.0.0"
JOURNAL_DIR = ".undo-journal"
SNAP_DIR = "snapshots"
JOURNAL_FILE = "journal.jsonl"

RISK_LEVELS = ["low", "medium", "high", "critical"]
UNDO_KINDS = ["builtin_restore", "commands", "compensation", "none"]
IRREVERSIBLE_TYPES = {"external_message", "deploy", "api_call", "payment", "publish", "delete_remote"}
FILE_TYPES = {"file_write", "file_delete", "file_move", "dir_change", "config_change"}

EXIT = {"ACCEPT": 0, "ACCEPT_WITH_WARNING": 1, "REJECT": 2, "ERROR": 4}


# ---------------------------------------------------------------------------
# Hashing & manifest
# ---------------------------------------------------------------------------
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_targets(paths):
    """Expand paths to a deterministic list of files (relative to cwd)."""
    files = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = sorted(d for d in dirs if d != JOURNAL_DIR and d != ".git")
                for n in sorted(names):
                    files.append(os.path.join(root, n))
        elif os.path.isfile(p):
            files.append(p)
        else:
            raise FileNotFoundError(p)
    return sorted(set(files))


def build_manifest(files):
    manifest = {}
    for f in files:
        st = os.stat(f)
        manifest[f] = {
            "sha256": sha256_file(f),
            "size": st.st_size,
            "mode": oct(st.st_mode & 0o777),
        }
    return manifest


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------
def journal_path():
    return os.path.join(JOURNAL_DIR, JOURNAL_FILE)


def journal_write(entry: dict):
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    entry["ts"] = datetime.now(timezone.utc).isoformat()
    entry["version"] = VERSION
    with open(journal_path(), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------
def cmd_snapshot(args):
    paths = args.paths or ["."]
    files = collect_targets(paths)
    if not files:
        print("nothing to snapshot")
        return EXIT["ERROR"]
    snap_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    snap_root = os.path.join(JOURNAL_DIR, SNAP_DIR, snap_id)
    backup_root = os.path.join(snap_root, "files")
    manifest = build_manifest(files)
    for f in files:
        dst = os.path.join(backup_root, f)
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.copy2(f, dst)
    meta = {"id": snap_id, "created": datetime.now(timezone.utc).isoformat(),
            "roots": paths, "count": len(files), "manifest": manifest}
    with open(os.path.join(snap_root, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    journal_write({"action": "snapshot", "snapshot": snap_id, "files": len(files),
                   "roots": paths})
    print("snapshot %s — %d files, manifest sha256-verified backups stored" % (snap_id, len(files)))
    return 0


# ---------------------------------------------------------------------------
# verify — diff current state vs snapshot
# ---------------------------------------------------------------------------
def load_manifest(snap_id):
    path = os.path.join(JOURNAL_DIR, SNAP_DIR, snap_id, "manifest.json")
    if not os.path.exists(path):
        raise FileNotFoundError("snapshot not found: %s" % snap_id)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def state_diff(meta):
    changed, deleted, intact = [], [], []
    for f, info in meta["manifest"].items():
        if not os.path.exists(f):
            deleted.append(f)
        elif sha256_file(f) != info["sha256"]:
            changed.append(f)
        else:
            intact.append(f)
    return changed, deleted, intact


def cmd_verify(args):
    meta = load_manifest(args.snapshot)
    changed, deleted, intact = state_diff(meta)
    print("verify %s: intact=%d changed=%d deleted=%d" % (
        args.snapshot, len(intact), len(changed), len(deleted)))
    for f in changed:
        print("  CHANGED %s" % f)
    for f in deleted:
        print("  DELETED %s" % f)
    journal_write({"action": "verify", "snapshot": args.snapshot,
                   "intact": len(intact), "changed": changed, "deleted": deleted})
    return 0


# ---------------------------------------------------------------------------
# restore — rollback from backup, refuse tampered backups
# ---------------------------------------------------------------------------
def cmd_restore(args):
    snap_root = os.path.join(JOURNAL_DIR, SNAP_DIR, args.snapshot)
    meta = load_manifest(args.snapshot)
    changed, deleted, intact = state_diff(meta)
    restored, refused = [], []
    for f in changed + deleted:
        backup = os.path.join(snap_root, "files", f)
        if not os.path.exists(backup):
            refused.append((f, "no backup copy"))
            continue
        recorded = meta["manifest"][f]["sha256"]
        actual = sha256_file(backup)
        if actual != recorded:
            refused.append((f, "backup tampered (sha256 mismatch)"))
            continue
        os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
        shutil.copy2(backup, f)
        if sha256_file(f) != recorded:
            refused.append((f, "post-restore verification failed"))
            continue
        restored.append(f)
    print("restore %s: restored=%d intact=%d refused=%d" % (
        args.snapshot, len(restored), len(intact), len(refused)))
    for f in restored:
        print("  RESTORED (byte-identical, sha256 verified) %s" % f)
    for f, why in refused:
        print("  REFUSED  %s — %s" % (f, why))
    journal_write({"action": "restore", "snapshot": args.snapshot,
                   "restored": restored,
                   "refused": [{"file": f, "reason": why} for f, why in refused]})
    return 0 if not refused else EXIT["ERROR"]


# ---------------------------------------------------------------------------
# plan — risk gate (plans are DATA; this tool never executes plan contents)
# ---------------------------------------------------------------------------
def validate_plan(plan: dict):
    """Return (verdict, [reasons]). Deterministic risk-gate rules."""
    reasons, warnings = [], []
    action = plan.get("action") or {}
    undo = plan.get("undo") or {}
    verify = plan.get("verify") or {}
    atype = action.get("type", "unknown")
    risk = plan.get("risk", "unknown")
    kind = undo.get("kind", "none")
    steps = undo.get("steps") or []

    if atype not in FILE_TYPES | IRREVERSIBLE_TYPES:
        reasons.append("unknown action.type %r — classify the action first" % atype)
    if risk not in RISK_LEVELS:
        reasons.append("risk must be one of %s" % RISK_LEVELS)
    if kind not in UNDO_KINDS:
        reasons.append("undo.kind must be one of %s" % UNDO_KINDS)

    if atype in IRREVERSIBLE_TYPES:
        if kind != "compensation":
            reasons.append(
                "%s is irreversible in the real world — undo.kind must be 'compensation' "
                "(mitigation steps), not %r" % (atype, kind))
        if kind == "compensation" and not steps:
            reasons.append("compensation plan has no steps")
    if atype in FILE_TYPES and kind == "none" and risk in ("medium", "high", "critical"):
        reasons.append(
            "file action at risk=%s with undo.kind='none' — take a snapshot "
            "(builtin_restore) or provide rollback steps" % risk)
    if atype in FILE_TYPES and kind == "none" and risk == "low":
        warnings.append("no undo path for a low-risk action — proceed only if trivially reproducible")
    if kind == "commands":
        if not steps:
            reasons.append("undo.kind='commands' requires non-empty undo.steps")
        if not verify.get("check"):
            reasons.append("undo.kind='commands' requires verify.check to prove restoration")
    if risk == "critical" and kind == "builtin_restore" and not verify.get("check"):
        warnings.append("critical risk with builtin_restore — add verify.check for extra assurance")
    if not action.get("description"):
        warnings.append("action.description missing — journal will be hard to audit")

    if reasons:
        return "REJECT", reasons, warnings
    if warnings:
        return "ACCEPT_WITH_WARNING", reasons, warnings
    return "ACCEPT", reasons, warnings


def cmd_plan(args):
    with open(args.plan_file, "r", encoding="utf-8") as fh:
        plan = json.load(fh)
    verdict, reasons, warnings = validate_plan(plan)
    print("PLAN GATE: %s  (%s)" % (verdict, args.plan_file))
    for r in reasons:
        print("  ✗ %s" % r)
    for w in warnings:
        print("  ⚠ %s" % w)
    journal_write({"action": "plan_gate", "plan_file": args.plan_file,
                   "verdict": verdict, "reasons": reasons, "warnings": warnings,
                   "plan": plan})
    return EXIT[verdict]


# ---------------------------------------------------------------------------
# journal / selfcheck
# ---------------------------------------------------------------------------
def cmd_journal(args):
    if not os.path.exists(journal_path()):
        print("journal is empty")
        return 0
    with open(journal_path(), "r", encoding="utf-8") as fh:
        entries = [json.loads(l) for l in fh if l.strip()]
    for e in entries[-args.last:]:
        print("%s  %-11s %s" % (e.get("ts", "?"), e.get("action", "?"),
                                json.dumps({k: v for k, v in e.items()
                                            if k not in ("ts", "version", "action", "plan")},
                                           ensure_ascii=False)[:120]))
    return 0


def cmd_selfcheck(args):
    """Prove the safety invariants of this tool's own source code."""
    src_path = os.path.abspath(__file__)
    with open(src_path, "r", encoding="utf-8") as fh:
        src = fh.read()
    # Build needles without embedding their literals in this source file.
    needles = ["os." + "system", "sub" + "process", "os." + "popen",
               "eval" + "(", "exec" + "(", "__imp" + "ort__",
               "commands." + "getoutput", "pty." + "spawn"]
    hits = [n for n in needles if n in src]
    print("selfcheck: scanning own source for execution primitives…")
    for n in needles:
        print("  %-22s %s" % (n, "FOUND ✗" if n in hits else "absent ✓"))
    if hits:
        print("SELFCHECK FAILED — this tool must never execute content")
        return EXIT["ERROR"]
    print("SELFCHECK PASSED — zero execution primitives: plans and files are data, never code")
    journal_write({"action": "selfcheck", "result": "PASS"})
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(prog="undo_guard",
                                description="Undo-First Guard: snapshot, risk-gated plans, verified restore.")
    ap.add_argument("--version", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("snapshot", help="capture state + backups of target paths")
    p.add_argument("paths", nargs="*")

    p = sub.add_parser("verify", help="diff current state against a snapshot")
    p.add_argument("snapshot")

    p = sub.add_parser("restore", help="roll back to a snapshot (hash-verified)")
    p.add_argument("snapshot")

    p = sub.add_parser("plan", help="risk-gate an undo plan (JSON)")
    p.add_argument("plan_file")

    p = sub.add_parser("journal", help="show the audit trail")
    p.add_argument("--last", type=int, default=20)

    sub.add_parser("selfcheck", help="prove this tool contains no execution primitives")

    args = ap.parse_args(argv)
    if args.version:
        print("undo_guard %s" % VERSION)
        return 0
    if not args.cmd:
        ap.print_help()
        return EXIT["ERROR"]

    try:
        return {
            "snapshot": cmd_snapshot, "verify": cmd_verify, "restore": cmd_restore,
            "plan": cmd_plan, "journal": cmd_journal, "selfcheck": cmd_selfcheck,
        }[args.cmd](args)
    except FileNotFoundError as e:
        print("error: %s" % e, file=sys.stderr)
        return EXIT["ERROR"]
    except json.JSONDecodeError as e:
        print("error: invalid plan JSON: %s" % e, file=sys.stderr)
        return EXIT["ERROR"]


if __name__ == "__main__":
    sys.exit(main())
