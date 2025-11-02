#!/usr/bin/env python3
"""Add 1 backdated commit (12:00 UTC) on every day in the current contribution-graph
window that shows 0 contributions and is not a letter day, so the background is filled.
Usage: python3 fill_background.py [--dry-run]"""
import re, os, sys, subprocess, datetime as dt
import make_pattern as m
h=subprocess.run(["curl","-s","https://github.com/users/radiofrequency/contributions"],capture_output=True,text=True,check=True).stdout
ids=dict(re.findall(r'data-date="([0-9-]+)"[^>]*?id="([^"]+)"',h))
tips=dict(re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>',h))
lit={str(d) for d in m.dates}
today=dt.datetime.now(dt.timezone.utc).date()
empty=[]
for d,i in sorted(ids.items()):
    t=tips.get(i,"")
    if d in lit or dt.date.fromisoformat(d)>today: continue
    if t.startswith("No contributions"): empty.append(d)
    elif not re.match(r"\d+ contribution",t): sys.exit(f"unparsed tooltip for {d}: {t!r}")
print(f"window {min(ids)}..{max(ids)}  empty non-letter days: {len(empty)}")
if "--dry-run" in sys.argv: sys.exit()
for d in empty:
    ts=f"{d}T12:00:00+00:00"; env=dict(os.environ,GIT_AUTHOR_DATE=ts,GIT_COMMITTER_DATE=ts)
    with open("background.log","a") as f: f.write(d+"\n")
    subprocess.run(["git","add","background.log"],check=True)
    subprocess.run(["git","commit","-q","-m",f"background {d}"],check=True,env=env)
