p = "app/seasonsim/m2_static_diag.py"
s = open(p, encoding="utf-8").read()
s = s.replace('''        return dict(n=int(len(x)), coverage_simulated_interval=round(cov, 3),''', '''        var_after_drift = float((x.real - x.e_dyn).var(ddof=0))                                     # what is left when the probabilities are allowed to drift (oracle)
        return dict(n=int(len(x)), variance_left_after_oracle_drift=round(var_after_drift, 2), coverage_simulated_interval=round(cov, 3),''')
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
