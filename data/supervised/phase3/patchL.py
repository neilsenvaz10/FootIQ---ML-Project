p = "docs/mini-project/PHASE3_FINAL_VALIDATION_PROTOCOL.md"
s = open(p, encoding="utf-8").read()
a = s.index("* Benchmark v1 is frozen as-is:")
b = s.index("* Its verdict stays")
new = """* Benchmark v1 is frozen as-is (sha256, recorded 2026-10-25):

| File | sha256 |
|---|---|
| `docs/mini-project/PHASE3_SCORELINE_BENCHMARK.md` | `48ebb7b05c9bb1ed2f1a4a616928adb9f63de24cacf2a45384c20028f81a8997` |
| `data/supervised/phase3/m2_distribution_report.json` | `05fe9b100b782f65be27beda2a431d2c3d107beea661548d5b135aa35da97b97` |
| `data/supervised/phase3/m2b_report.json` | `23741826680ed67cb091f03aaf2d3d31d868915e051ac4d069b84ec9b04765d3` |
| `data/supervised/phase3/m2_rule_power.json` | `777934c0f3a7e12eb3551f80927a14baf8863c594b3141c09a0e48a965bee93a` |
| `data/supervised/phase3/m2_s4_tuning.json` | `5bd8dc1fbb13b45a051aaed08fb49d43e2d97e0ec9dd222de8b71ada1b6e4158` |
| `data/supervised/phase3/m2_matches.pkl` | `3c381bd303f0cb77033bd6474c45569b5dc36c2c53804a55056268ace3878f2a` |

"""
s = s[:a] + new + s[b:]
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
