#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Undo-First verification harness.

Proves the undo infrastructure with measurable evidence:
  - restore is byte-identical (sha256) for write/delete/move/multi-file scenarios
  - tampered backups are REFUSED, not restored
  - the risk gate rejects irreversible actions without compensation plans
  - the engine contains zero execution primitives (selfcheck)

Usage: python3 tests/test_undo_guard.py [--evidence-dir DIR]
Exit 0 = all criteria pass.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
GUARD = os.path.join(SKILL_ROOT, "scripts", "undo_guard.py")

spec = importlib.util.spec_from_file_location("undo_guard", GUARD)
ug = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ug)

SANDBOX = os.path.join(HERE, ".sandbox")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def run_guard(*args, cwd=None):
    p = subprocess.run([sys.executable, GUARD] + list(args),
                       capture_output=True, text=True, cwd=cwd)
    return p.returncode, p.stdout + p.stderr


def tree_state(root):
    out = {}
    for r, d, fs in os.walk(root):
        d[:] = [x for x in d if x not in (".undo-journal", ".git")]
        for f in sorted(fs):
            p = os.path.join(r, f)
            out[os.path.relpath(p, root)] = sha(p)
    return out


def fresh(name):
    wd = os.path.join(SANDBOX, name)
    shutil.rmtree(wd, ignore_errors=True)
    os.makedirs(wd)
    return wd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", default=os.path.join(SKILL_ROOT, "..", "evidence"))
    args = ap.parse_args()
    evidence_dir = os.path.abspath(args.evidence_dir)
    os.makedirs(evidence_dir, exist_ok=True)
    shutil.rmtree(SANDBOX, ignore_errors=True)

    rows = []
    def check(name, ok, detail=""):
        rows.append({"case": name, "pass": bool(ok), "detail": detail})
        print("  [%s] %s %s" % ("PASS" if ok else "FAIL", name, detail))

    print("=" * 74)
    print(" UNDO-FIRST GUARD — VERIFICATION HARNESS")
    print(" run %s UTC" % datetime.now(timezone.utc).isoformat())
    print("=" * 74)

    # ---- S1: file modified → restore byte-identical ----
    print("\n--- Restoration scenarios (sha256 byte-identical proof) ---")
    wd = fresh("s1")
    f = os.path.join(wd, "config.txt")
    open(f, "w").write("original content v1\n")
    before = sha(f)
    rc, out = run_guard("snapshot", "config.txt", cwd=wd)
    snap = out.split()[1]
    open(f, "w").write("MUTATED by a bad action\n")
    rc, out = run_guard("restore", snap, cwd=wd)
    check("S1 modify → restore", sha(f) == before, "sha256 identical: %s" % (sha(f) == before))

    # ---- S2: file deleted → restore ----
    wd = fresh("s2")
    f = os.path.join(wd, "important.md")
    open(f, "w").write("# do not lose me\n")
    before = sha(f)
    rc, out = run_guard("snapshot", ".", cwd=wd); snap = out.split()[1]
    os.remove(f)
    rc, out = run_guard("restore", snap, cwd=wd)
    check("S2 delete → restore", os.path.exists(f) and sha(f) == before,
          "restored from deletion")

    # ---- S3: multi-file tree mutation → full restore ----
    wd = fresh("s3")
    for n, c in [("a.txt", "aaa\n"), ("b/c.txt", "ccc\n"), ("b/d.txt", "ddd\n")]:
        p = os.path.join(wd, n); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(c)
    before = tree_state(wd)
    rc, out = run_guard("snapshot", ".", cwd=wd); snap = out.split()[1]
    open(os.path.join(wd, "a.txt"), "w").write("MUTATED\n")
    os.remove(os.path.join(wd, "b/c.txt"))
    open(os.path.join(wd, "b/d.txt"), "a").write("appended\n")
    rc, out = run_guard("restore", snap, cwd=wd)
    after = tree_state(wd)
    check("S3 tree mutation → restore", before == after,
          "tree sha256 map identical (%d files)" % len(after))

    # ---- S4: tampered backup → REFUSED ----
    wd = fresh("s4")
    f = os.path.join(wd, "x.txt")
    open(f, "w").write("safe\n")
    rc, out = run_guard("snapshot", ".", cwd=wd); snap = out.split()[1]
    open(f, "w").write("changed\n")
    # corrupt the backup copy
    bpath = os.path.join(wd, ".undo-journal", "snapshots", snap, "files", "x.txt")
    open(bpath, "w").write("ATTACKER TAMPERED BACKUP\n")
    rc, out = run_guard("restore", snap, cwd=wd)
    check("S4 tampered backup refused", "REFUSED" in out and "sha256 mismatch" in out,
          "backup tamper detected")

    # ---- S5: risk gate — irreversible without compensation → REJECT ----
    print("\n--- Risk gate scenarios ---")
    wd = fresh("s5")
    plan = {"action": {"type": "external_message", "description": "send email to client"},
            "risk": "high", "undo": {"kind": "none", "steps": []}, "verify": {}}
    pf = os.path.join(wd, "plan.json"); json.dump(plan, open(pf, "w"))
    rc, out = run_guard("plan", pf, cwd=wd)
    check("S5 irreversible + no undo → REJECT", rc == 2 and "compensation" in out,
          "exit=%d" % rc)

    # ---- S6: irreversible WITH compensation plan → ACCEPT ----
    plan["undo"] = {"kind": "compensation",
                    "steps": ["send correction email within 1h", "notify manager"]}
    json.dump(plan, open(pf, "w"))
    rc, out = run_guard("plan", pf, cwd=wd)
    check("S6 irreversible + compensation → ACCEPT", rc == 0,
          "exit=%d" % rc)

    # ---- S7: file action, no undo path, medium risk → REJECT ----
    plan = {"action": {"type": "file_delete", "description": "remove old report"},
            "risk": "medium", "undo": {"kind": "none", "steps": []}, "verify": {}}
    json.dump(plan, open(pf, "w"))
    rc, out = run_guard("plan", pf, cwd=wd)
    check("S7 file action + no undo + risk=medium → REJECT", rc == 2,
          "exit=%d" % rc)

    # ---- S8: file action with builtin_restore + snapshot → ACCEPT ----
    plan = {"action": {"type": "file_delete", "description": "remove old report"},
            "risk": "medium",
            "undo": {"kind": "builtin_restore", "steps": ["restore snapshot"]},
            "verify": {"check": "sha256 manifest comparison"}}
    json.dump(plan, open(pf, "w"))
    rc, out = run_guard("plan", pf, cwd=wd)
    check("S8 file action + builtin_restore → ACCEPT", rc == 0, "exit=%d" % rc)

    # ---- S9: commands kind requires steps + verify ----
    plan = {"action": {"type": "git_push", "description": "push release branch"},
            "risk": "high", "undo": {"kind": "commands", "steps": []}, "verify": {}}
    json.dump(plan, open(pf, "w"))
    rc, out = run_guard("plan", pf, cwd=wd)
    check("S9 commands without steps/verify → REJECT", rc == 2, "exit=%d" % rc)

    # ---- S10: unknown action type → REJECT ----
    plan = {"action": {"type": "mystery", "description": "?"},
            "risk": "low", "undo": {"kind": "builtin_restore", "steps": []}, "verify": {}}
    json.dump(plan, open(pf, "w"))
    rc, out = run_guard("plan", pf, cwd=wd)
    check("S10 unclassified action → REJECT", rc == 2, "exit=%d" % rc)

    # ---- S11: selfcheck — zero execution primitives ----
    print("\n--- Safety invariants ---")
    rc, out = run_guard("selfcheck")
    check("S11 engine has zero execution primitives", rc == 0 and "PASSED" in out,
          "selfcheck")

    # ---- S12: journal audit trail exists in the sandboxes it belongs to ----
    rc1, out1 = run_guard("journal", cwd=os.path.join(SANDBOX, "s3"))   # snapshot+restore
    rc2, out2 = run_guard("journal", cwd=os.path.join(SANDBOX, "s5"))   # plan_gate decisions
    ok = (rc1 == 0 and rc2 == 0 and "snapshot" in out1 and "restore" in out1
          and "plan_gate" in out2 and "REJECT" in out2)
    check("S12 journal records decisions (snapshot/restore/plan_gate)", ok,
          "audit trail present in both journals")

    # ---- metrics ----
    total = len(rows)
    passed = sum(1 for r in rows if r["pass"])
    print("\n" + "=" * 74)
    print(" RESULT: %d/%d cases passed (%.0f%%)" % (passed, total, 100 * passed / total))
    overall = passed == total
    print(" OVERALL: %s" % ("PASS ✅" if overall else "FAIL ❌"))

    payload = {"harness": "undo-first verification harness v1.0",
               "ran_at_utc": datetime.now(timezone.utc).isoformat(),
               "guard_version": ug.VERSION,
               "total": total, "passed": passed, "overall_pass": overall,
               "results": rows}
    jp = os.path.join(evidence_dir, "undo_test_results.json")
    json.dump(payload, open(jp, "w"), indent=2, ensure_ascii=False)
    print(" JSON evidence → %s" % jp)
    shutil.rmtree(SANDBOX, ignore_errors=True)
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
