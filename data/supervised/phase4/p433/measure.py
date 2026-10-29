import os,sys
t=n=0
for dp,dn,fn in os.walk('.'):
    for f in fn:
        try: t+=os.path.getsize(os.path.join(dp,f)); n+=1
        except OSError: pass
print(n,t,round(t/1e9,3))
