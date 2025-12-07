#!/usr/bin/env python3
"""Backdated commits spelling HIRE ME (5x7 font, wide spacing) in the GitHub contribution graph.
Usage: python3 make_pattern.py [--preview]"""
import datetime as dt, os, subprocess, sys
FONT = {
'H':["X...X","X...X","X...X","XXXXX","X...X","X...X","X...X"],
'I':["XXXXX","..X..","..X..","..X..","..X..","..X..","XXXXX"],
'R':["XXXX.","X...X","X...X","XXXX.","X.X..","X..X.","X...X"],
'E':["XXXXX","X....","X....","XXXX.","X....","X....","XXXXX"],
'M':["X...X","XX.XX","X.X.X","X.X.X","X...X","X...X","X...X"],
}
TEXT="HIRE ME"; LETTER_GAP=2; WORD_GAP=5
def grid():
    rows=[""]*7; words=TEXT.split()
    for wi,w in enumerate(words):
        for li,ch in enumerate(w):
            rows=[rows[r]+FONT[ch][r] for r in range(7)]
            if li<len(w)-1: rows=[x+"."*LETTER_GAP for x in rows]
        if wi<len(words)-1: rows=[x+"."*WORD_GAP for x in rows]
    return rows
GRAPH_START=dt.date(2025,11,2)   # first Sunday on graph as of 2026-11-03
GRAPH_WEEKS=53
TODAY=dt.date(2026,11,3)
N=int(os.environ.get("COMMITS_PER_PIXEL","40"))
rows=grid(); W=len(rows[0]); off=(GRAPH_WEEKS-W)//2
start=GRAPH_START+dt.timedelta(weeks=off)
dates=sorted(start+dt.timedelta(weeks=c,days=r) for r in range(7) for c in range(W) if rows[r][c]=="X")
assert off>=3 and GRAPH_WEEKS-W-off>=3 and dates[0]>=GRAPH_START+dt.timedelta(weeks=2) and dates[-1]<TODAY
if __name__=="__main__":
    print(f"width={W} margins={off}/{GRAPH_WEEKS-W-off} first={dates[0]} last={dates[-1]} lit_days={len(dates)} commits={len(dates)*N}")
    for r,name in zip(rows,"Sun Mon Tue Wed Thu Fri Sat".split()): print(name,"|"+"."*off+r.replace("X","#").replace("."," ")+"."*(GRAPH_WEEKS-W-off)+"|")
    if "--preview" in sys.argv: sys.exit()
    for d in dates:
        for i in range(N):
            ts=f"{d.isoformat()}T12:{i//60:02d}:{i%60:02d}+00:00"
            env=dict(os.environ,GIT_AUTHOR_DATE=ts,GIT_COMMITTER_DATE=ts)
            with open("pixels.log","a") as f: f.write(f"{d} {i}\n")
            subprocess.run(["git","add","pixels.log"],check=True)
            subprocess.run(["git","commit","-q","-m",f"pixel {d} #{i+1}"],check=True,env=env)
