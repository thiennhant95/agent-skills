# Skill Firewall — Test Results

Run: 2026-11-13T15:06:08.894341+00:00 UTC | Scanner v1.1.0

| Fixture | Kind | Verdict | Score | Findings | Rules | Result |
|---|---|---|---|---|---|---|
| m01_instruction_override.md | malicious | MALICIOUS | 64 | 7 | SF101,SF102,SF104,SF105,SF106 | PASS |
| m02_credential_theft.md | malicious | MALICIOUS | 122 | 11 | SF104,SF201,SF202,SF204,SF205,SF206 | PASS |
| m03_reverse_shell.sh | malicious | MALICIOUS | 150 | 9 | SF201,SF202,SF204,SF302,SF304,SF305 | PASS |
| m04_base64_payload.py.md | malicious | MALICIOUS | 44 | 5 | SF101,SF401,SF403 | PASS |
| m05_destructive.md | malicious | MALICIOUS | 145 | 7 | SF301,SF303 | PASS |
| m06_env_exfil.py | malicious | MALICIOUS | 54 | 6 | SF202,SF203,SF204,SF205,SF206 | PASS |
| m07_fake_system_tag.md | malicious | MALICIOUS | 90 | 9 | SF101,SF102,SF103,SF104 | PASS |
| m08_stealth_zwc.md | malicious | MALICIOUS | 40 | 4 | SF104,SF204,SF206,SF404 | PASS |
| m09_persistence.md | malicious | MALICIOUS | 129 | 9 | SF201,SF302,SF303,SF304,SF601 | PASS |
| m10_hex_payload.js | malicious | MALICIOUS | 40 | 4 | SF101,SF401,SF402 | PASS |
| m11_self_modifying.md | malicious | MALICIOUS | 115 | 7 | SF104,SF106,SF206,SF502 | PASS |
| m12_spread_external.md | malicious | MALICIOUS | 70 | 4 | SF501,SF503 | PASS |
| m13_example_disguise.md | malicious | MALICIOUS | 40 | 4 | SF105,SF201,SF204,SF301 | PASS |
| m14_homoglyph.md | malicious | MALICIOUS | 75 | 6 | SF101,SF105,SF201,SF204,SF407 | PASS |
| m15_double_b64.md | malicious | MALICIOUS | 36 | 3 | SF101,SF204,SF206 | PASS |
| m16_markdown_beacon.md | malicious | SUSPICIOUS | 14 | 2 | SF104,SF408 | PASS |
| m17_supply_chain.json | malicious | MALICIOUS | 39 | 3 | SF204,SF601,SF602 | PASS |
| m18_ci_injection.yml | malicious | MALICIOUS | 55 | 4 | SF201,SF204,SF603 | PASS |
| b01_pdf_rotate.md | benign | SAFE | 0 | 0 | - | PASS |
| b02_weather_curl.md | benign | SAFE | 0 | 0 | - | PASS |
| b03_security_education.md | benign | CAUTION | 16 | 7 | SF101,SF201,SF204,SF206,SF301,SF305 | PASS |
| b04_code_linter.md | benign | SAFE | 0 | 0 | - | PASS |
| b05_base64_font.md | benign | SAFE | 0 | 0 | - | PASS |
| b06_vn_tax.md | benign | SAFE | 0 | 0 | - | PASS |
| b07_git_workflow.md | benign | SAFE | 0 | 0 | - | PASS |
| b08_voice_tts.md | benign | SAFE | 0 | 0 | - | PASS |
| b09_meeting_notes.md | benign | SAFE | 0 | 0 | - | PASS |
| b10_data_analysis.md | benign | SAFE | 0 | 0 | - | PASS |
| b11_rustup_install.md | benign | CAUTION | 4 | 1 | SF601 | PASS |
| b12_readme_badges.md | benign | SAFE | 0 | 0 | - | PASS |
| b13_package_ok.json | benign | SAFE | 0 | 0 | - | PASS |
| b14_actions_ok.yml | benign | SAFE | 0 | 0 | - | PASS |
| b15_multilingual.md | benign | SAFE | 0 | 0 | - | PASS |

## Metrics

- Detection rate: **100.0%** (18/18 malicious caught)
- False positive rate: **0.0%** (0/15 benign flagged)
- Precision: 100.0% | Accuracy: 100.0%

Overall: **PASS**
