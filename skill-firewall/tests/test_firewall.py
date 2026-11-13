#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Firewall — verification harness.

Proves the scanner works with measurable evidence:
  - 12 malicious fixtures  (inert detection test vectors, like EICAR for antivirus)
  - 10 benign fixtures     (real-world-shaped skills incl. false-positive stress cases)

Metrics: detection rate, false-positive rate, precision, accuracy.
Writes machine-readable JSON + human-readable Markdown report.

Usage:
  python3 test_firewall.py [--evidence-dir DIR]

Exit code 0 = all criteria pass, 1 = failure.
"""

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
SCANNER_PATH = os.path.join(SKILL_ROOT, "scripts", "skill_firewall.py")
FIXTURES = os.path.join(HERE, "fixtures")

# Load scanner module
spec = importlib.util.spec_from_file_location("skill_firewall", SCANNER_PATH)
sf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sf)

# Expectation contract:
#   malicious -> verdict must be SUSPICIOUS or MALICIOUS (>= threshold to block install)
#   benign    -> verdict must be SAFE or CAUTION     (< threshold, install allowed)
DETECTED = {"SUSPICIOUS", "MALICIOUS"}
CLEAN = {"SAFE", "CAUTION"}


def scan_one(path):
    res = sf.scan_path(path)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-dir", default=os.path.join(SKILL_ROOT, "..", "evidence"))
    args = ap.parse_args()
    evidence_dir = os.path.abspath(args.evidence_dir)
    os.makedirs(evidence_dir, exist_ok=True)

    rows = []
    tp = fn = tn = fp = 0

    mdir = os.path.join(FIXTURES, "malicious")
    bdir = os.path.join(FIXTURES, "benign")

    print("=" * 78)
    print(" SKILL FIREWALL — VERIFICATION HARNESS")
    print(" run at %s UTC" % datetime.now(timezone.utc).isoformat())
    print("=" * 78)

    print("\n--- MALICIOUS FIXTURES (all must be detected: SUSPICIOUS/MALICIOUS) ---")
    for name in sorted(os.listdir(mdir)):
        path = os.path.join(mdir, name)
        res = scan_one(path)
        ok = res.verdict in DETECTED
        tp += ok
        fn += (not ok)
        rows.append(dict(fixture=name, kind="malicious", verdict=res.verdict,
                         score=res.score, findings=len(res.findings),
                         detected=bool(ok),
                         rules=sorted({f.rule_id for f in res.findings})))
        print("  [%s] %-34s verdict=%-10s score=%3d findings=%2d rules=%s" % (
            "PASS" if ok else "FAIL", name, res.verdict, res.score,
            len(res.findings), ",".join(sorted({f.rule_id for f in res.findings}))))

    print("\n--- BENIGN FIXTURES (all must stay clean: SAFE/CAUTION) ---")
    for name in sorted(os.listdir(bdir)):
        path = os.path.join(bdir, name)
        res = scan_one(path)
        ok = res.verdict in CLEAN
        tn += ok
        fp += (not ok)
        rows.append(dict(fixture=name, kind="benign", verdict=res.verdict,
                         score=res.score, findings=len(res.findings),
                         clean=bool(ok),
                         rules=sorted({f.rule_id for f in res.findings})))
        print("  [%s] %-34s verdict=%-10s score=%3d findings=%2d rules=%s" % (
            "PASS" if ok else "FAIL", name, res.verdict, res.score,
            len(res.findings), ",".join(sorted({f.rule_id for f in res.findings}))))

    total_m, total_b = tp + fn, tn + fp
    detection_rate = tp / total_m if total_m else 0.0
    fp_rate = fp / total_b if total_b else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    accuracy = (tp + tn) / (total_m + total_b) if (total_m + total_b) else 0.0

    print("\n" + "=" * 78)
    print(" METRICS")
    print("=" * 78)
    print("  Detection rate (malicious caught) : %d/%d = %.1f%%" % (tp, total_m, detection_rate * 100))
    print("  False positives (benign flagged)  : %d/%d = %.1f%%" % (fp, total_b, fp_rate * 100))
    print("  Precision                         : %.1f%%" % (precision * 100))
    print("  Accuracy                          : %.1f%%" % (accuracy * 100))

    criteria = dict(
        detection_rate_100pct=(detection_rate == 1.0),
        false_positives_0=(fp == 0),
    )
    print("\n  Acceptance criteria:")
    for k, v in criteria.items():
        print("    [%s] %s" % ("PASS" if v else "FAIL", k))
    passed = all(criteria.values())

    # ---- evidence artifacts ----
    payload = dict(
        harness="skill-firewall verification harness v1.0",
        ran_at_utc=datetime.now(timezone.utc).isoformat(),
        scanner_version=sf.SCANNER_VERSION,
        metrics=dict(total_malicious=total_m, total_benign=total_b,
                     true_positives=tp, false_negatives=fn,
                     true_negatives=tn, false_positives=fp,
                     detection_rate=detection_rate, false_positive_rate=fp_rate,
                     precision=precision, accuracy=accuracy),
        criteria=criteria, overall_pass=passed, results=rows,
    )
    json_path = os.path.join(evidence_dir, "test_results.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print("\n  JSON evidence → %s" % json_path)

    md_path = os.path.join(evidence_dir, "TEST_RESULTS_TABLE.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("# Skill Firewall — Test Results\n\n")
        fh.write("Run: %s UTC | Scanner v%s\n\n" % (payload["ran_at_utc"], sf.SCANNER_VERSION))
        fh.write("| Fixture | Kind | Verdict | Score | Findings | Rules | Result |\n")
        fh.write("|---|---|---|---|---|---|---|\n")
        for r in rows:
            ok = r.get("detected", r.get("clean"))
            fh.write("| %s | %s | %s | %d | %d | %s | %s |\n" % (
                r["fixture"], r["kind"], r["verdict"], r["score"],
                r["findings"], ",".join(r["rules"]) or "-", "PASS" if ok else "FAIL"))
        fh.write("\n## Metrics\n\n")
        fh.write("- Detection rate: **%.1f%%** (%d/%d malicious caught)\n" % (detection_rate * 100, tp, total_m))
        fh.write("- False positive rate: **%.1f%%** (%d/%d benign flagged)\n" % (fp_rate * 100, fp, total_b))
        fh.write("- Precision: %.1f%% | Accuracy: %.1f%%\n" % (precision * 100, accuracy * 100))
        fh.write("\nOverall: **%s**\n" % ("PASS" if passed else "FAIL"))
    print("  Markdown evidence → %s" % md_path)

    print("\n  OVERALL: %s" % ("PASS ✅" if passed else "FAIL ❌"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
