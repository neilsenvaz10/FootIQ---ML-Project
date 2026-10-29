p="docs/mini-project/PHASE3_RULES_STATUS.md"
s=open(p,encoding="utf-8").read()
s=s.replace("SpOL para 14 and the match-result paragraph (no. 4-5)","SpOL para 14, no. 4-5")
s=s.replace("Rule found (para 14 and no. 4/5 of the match-result paragraph); outcome set by DFB legal bodies","Rule found (SpOL para 14, no. 4-6); outcome set by DFB legal bodies")
open(p,"w",encoding="utf-8",newline="\n").write(s)
