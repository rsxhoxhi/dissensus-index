#!/usr/bin/env python3
"""
Dissensus Index — incremental cases.json builder.
Reads the tracker (xlsx) + the current published cases.json, carries every
already-published case over UNCHANGED, and appends any new tracker rows as
fresh cases (clean field mapping, normalized country, correct outlet parsing,
and a provisional stage flagged for editorial review).
Usage: python3 build_cases.py tracker.xlsx cases.json cases.out.json
"""
import sys, json, re, datetime
import pandas as pd

TRACKER, CURRENT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
TODAY = "2026-06-17"

COLMAP = {  # tracker column -> json field
    "Artwork / Object":"title","Artist":"artist","Location / Institution":"institution",
    "Country":"country","Governance Type":"governance_type","Date of Controversy":"date_controversy",
    "Date Discovered":"date_discovered","Brief Description":"description","Outcome / Status":"outcome",
    "Broad Tags":"tags","Court Case":"court_case","Coverage Tier":"coverage_tier",
    "Primary Source Link":"source",
}
STAGE_LABEL = {1:"Watching",2:"Escalating",3:"In process",4:"Active",5:"Resolved"}

def parse_outlets(v):
    v=(v or "").strip()
    if not v: return []
    parts = v.split(";") if ";" in v else v.split(", ")
    return [p.strip() for p in parts if p.strip()]

def to_iso(datestr):
    s=(datestr or "").strip()
    m=re.search(r"([A-Z][a-z]+)\s+(\d{1,2}),?\s+(\d{4})", s)
    if m:
        try: return datetime.datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}","%B %d %Y").date().isoformat()
        except: pass
    m=re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    return m.group(0) if m else TODAY

def guess_stage(court, outcome):
    o=(outcome or "").lower(); c=(court or "").lower()
    if re.search(r"\b(resolved|reinstated|settle|ruling issued|dismissed|withdrawn|completed|concluded|final)\b", o): return 5
    if c=="yes" or re.search(r"\b(litigation|lawsuit|appeal|injunction|court|sued|filing)\b", o): return 4
    if re.search(r"\b(pending|underway|investigation|review|hearing|negotiat|proceeding|awaiting)\b", o): return 3
    if re.search(r"\b(petition|protest|boycott|open letter|campaign|backlash|demand)\b", o): return 2
    return 1

def main():
    sh = pd.read_excel(TRACKER, sheet_name="Sheet", dtype=str, keep_default_na=False)
    cur = json.load(open(CURRENT))
    cases = cur["cases"]
    published_ids = {c.get("entry_id","").strip() for c in cases}

    # derive country normalization map from already-published cases
    jById = {c.get("entry_id","").strip(): c for c in cases}
    cmap = {}
    for _,r in sh.iterrows():
        eid=r["Entry ID"].strip()
        if eid in jById:
            t=r["Country"].strip(); j=str(jById[eid].get("country","")).strip()
            if t and j: cmap[t]=j

    max_seq = max((c.get("seq",0) for c in cases), default=0)
    new=[]
    for idx,r in sh.iterrows():
        eid=r["Entry ID"].strip()
        if eid in published_ids: continue        # already live -> leave untouched
        if eid.upper()=="NOTE": continue          # protocol annotation, not a case
        rec={"id":f"ACI-{eid}","entry_id":eid}
        for col,key in COLMAP.items():
            rec[key]=r[col].strip()
        rec["country"]=cmap.get(rec["country"], rec["country"])
        rec["outlets"]=parse_outlets(r["Key Outlets"])
        rec["sort_date"]=to_iso(r["Date Discovered"])
        st=guess_stage(rec["court_case"], rec["outcome"])
        rec["stage"]=st; rec["stage_label"]=STAGE_LABEL[st]
        rec["_tracker_row"]=idx
        new.append(rec)

    # newest first; assign seq above current max
    new.sort(key=lambda c:(c["sort_date"], c["_tracker_row"]), reverse=True)
    for i,c in enumerate(new):
        c["seq"]=max_seq+len(new)-i
    review=[{"id":c["id"],"title":c["title"][:70],"court":c["court_case"],"stage":c["stage"]} for c in new]
    for c in new: c.pop("_tracker_row",None)

    # order fields like the published records, then write
    keyorder=["id","entry_id","seq","title","artist","institution","country","governance_type",
              "date_controversy","date_discovered","sort_date","description","outcome","tags",
              "court_case","coverage_tier","outlets","source","stage","stage_label"]
    new=[{k:c.get(k,"") for k in keyorder} for c in new]

    out=dict(cur)
    out["cases"]=new+cases
    out["meta"]=dict(cur["meta"]); out["meta"]["total_cases"]=len(out["cases"]); out["meta"]["last_published"]=TODAY
    json.dump(out, open(OUT,"w"), ensure_ascii=False, indent=2)
    print("published before:",len(cases),"| new added:",len(new),"| total now:",len(out["cases"]))
    print("\nNEW CASES (review stages):")
    for x in review: print(f"  {x['id']:<12} S{x['stage']}  court={x['court']:<8} {x['title']}")

if __name__=="__main__": main()
