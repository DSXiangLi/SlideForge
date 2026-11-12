import os, sys, glob, json
import numpy as np
ANALYSIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ANALYSIS)
import _fingerprint as F

PAGES = ["cover","toc","low","high","chart","closing"]
THEMES = ["b1","e5","c3","h1"]
files = sorted(glob.glob(os.path.join(ANALYSIS, "PILOT-*.png")))
feats = {}
for f in files:
    b = os.path.basename(f)[:-4].split("-")
    feats[(b[1],b[2])] = F.features(f)

def cos(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float)
    na=np.linalg.norm(a); nb=np.linalg.norm(b)
    return 0.0 if na<1e-9 or nb<1e-9 else float(np.dot(a,b)/(na*nb))

print("=== PER-PAGE STATS ===")
for t in THEMES:
    for p in PAGES:
        fr=feats[(t,p)]
        print("%s %-7s pol=%-5s dark=%.3f cx=%.3f cy=%.3f edom=%-9s es_aniso=%.3f" % (
            t.upper(), p, fr["polarity"], fr["dark_ratio"], fr["cx"], fr["cy"],
            fr["edge_struct_dominant"], fr["edge_struct_anisotropy"]))

print("\n=== TOP 12 CROSS-THEME PAIRS (skeleton corr) ===")
pairs=[]
for t1 in THEMES:
    for t2 in THEMES:
        if t1>=t2: continue
        for p1 in PAGES:
            for p2 in PAGES:
                c=cos(feats[(t1,p1)]["s"], feats[(t2,p2)]["s"])
                pairs.append((c,"%s/%s"%(t1,p1),"%s/%s"%(t2,p2)))
pairs.sort(reverse=True)
for c,a,b in pairs[:12]:
    print("  %.3f  %s  <->  %s" % (c,a,b))

print("\n=== TOP 8 WITHIN-THEME PAIRS (skeleton corr) ===")
for t in THEMES:
    wp=[]
    for i,a in enumerate(PAGES):
        for b in PAGES[i+1:]:
            wp.append((cos(feats[(t,a)]["s"],feats[(t,b)]["s"]),a,b))
    wp.sort(reverse=True)
    print("  %s:" % t.upper(), "  ".join("%.2f(%s-%s)"%(c,a,b) for c,a,b in wp[:4]))

print("\n=== BOTTOM 4 WITHIN-THEME PAIRS (most different) ===")
for t in THEMES:
    wp=[]
    for i,a in enumerate(PAGES):
        for b in PAGES[i+1:]:
            wp.append((cos(feats[(t,a)]["s"],feats[(t,b)]["s"]),a,b))
    wp.sort()
    print("  %s:" % t.upper(), "  ".join("%.2f(%s-%s)"%(c,a,b) for c,a,b in wp[:3]))
