from pathlib import Path
import os, sys, json, time, urllib.request
import pandas as pd
root=Path(__file__).resolve().parents[4]
os.environ["FOOTIQ_STORE_PATH"]=str(root/"data/supervised/phase4/p44/preview.sqlite")
sys.path.insert(0,str(root/"app"))
import analytics
checks=[]
for key in ["EPL","LALIGA","BUNDESLIGA","SERIEA","LIGUE1"]:
 for season in analytics.seasons(key):
  frame=analytics.matches(); f=frame[(frame.competition_key==key)&(frame.season==season)]
  sides=[]
  for team,gf,ga in [("home","home_goals","away_goals"),("away","away_goals","home_goals")]:
   d=pd.DataFrame({"team":f[team],"gf":f[gf],"ga":f[ga]})
   d["played"]=1;d["won"]=(d.gf>d.ga).astype(int);d["drawn"]=(d.gf==d.ga).astype(int);d["lost"]=(d.gf<d.ga).astype(int)
   sides.append(d)
  expected=pd.concat(sides).groupby("team").sum();expected["points"]=3*expected.won+expected.drawn;expected["gd"]=expected.gf-expected.ga
  actual=analytics.standings(key,season)
  for row in actual:
   for col in ["played","won","drawn","lost","gf","ga","gd","points"]:assert row[col]==int(expected.loc[row["team"],col]),(key,season,row,col)
  assert len(actual)==len(expected)
  checks.append({"competition":key,"season":season,"clubs":len(actual),"matches":len(f),"result":"identical"})
latency=[]
for i in range(3):
 t=time.perf_counter()
 with urllib.request.urlopen("http://127.0.0.1:8004/api/health") as r: h=json.load(r)
 with urllib.request.urlopen("http://127.0.0.1:8004/api/meta") as r: json.load(r)
 latency.append({"seconds":time.perf_counter()-t,"ready":h["club_prediction_ready"]})
result={"standings_checks":checks,"health_and_meta_ready_latency":latency,"scope":"Independent vector aggregation of the same verified stored results, not certification against official league tables."}
Path(__file__).with_suffix(".json").write_text(json.dumps(result,indent=2))
print(len(checks),"league-season tables identical; readiness latency",latency)
