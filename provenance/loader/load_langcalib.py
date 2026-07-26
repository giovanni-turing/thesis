#!/usr/bin/env python3
"""Ingest the language quantile+scale calibration + symmetric-baseline batch (2026-07-24/25)
into experiment='langcalib'. Families:
  forecast  -- eval-span (incl. the mean-conversion arm eval_p90_s1 and the p90/s6 bursts),
               the burst2/burst6 calibration grid, and the 7 daily fold runs (F1-F7);
  reactive  -- Dynamo SLA planner (variant B) calibrated on burst2/burst6 and held-out on
               the eval bursts, plus the {constant,kalman,prophet} predictor sweep;
  static    -- TP1x4 / TP2x2 on the calib + eval windows.
Idempotent (ON CONFLICT (run_id) DO UPDATE), atomic; run_ids namespaced langcalib:*.
Real quantile lives in config (runs_quantile_vocab CHECK permits only {p50,p90,obs});
scale / targets / predictor / tp all in config too. F1-F7 must be registered in windows()
first (done via schema INSERT). Run: python3 provenance/loader/load_langcalib.py ;
then verify with provenance/verify_all.sh / check_all().
"""
import os, glob, json, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db, ingest_common as ic

ROOT = "/home/gio/tese/simulation/results/lang_qsweep"
EXP = "langcalib"
LLM_COLS = ["completed_requests","num_requests","mean_ttft_ms","median_ttft_ms","p90_ttft_ms",
    "p95_ttft_ms","p99_ttft_ms","max_ttft_ms","mean_itl_ms","p99_itl_ms","mean_tpot_ms",
    "p99_tpot_ms","mean_e2e_latency_ms","p90_e2e_latency_ms","p99_e2e_latency_ms",
    "max_e2e_latency_ms","p99_ttst_ms","request_throughput_rps","output_throughput_tok_s",
    "total_throughput_tok_s","gpu_hours","decode_worker_seconds","prefill_worker_seconds",
    "prefix_cache_reused_ratio"]

def _q(q): return q if q in ("p50","p90") else None

def discover():
    R=[]
    for p in sorted(glob.glob(f"{ROOT}/eval_*/*.report.json")):
        m=re.search(r"/eval_(p\d+)_s([0-9]+)/(\w+)\.report\.json$",p)
        if not m: continue
        q,s,win=m.groups(); wname="aggregate" if win=="week" else win
        mean=(s=="1")
        R.append(dict(rid=f"{EXP}:eval_{q}_s{s}_{win}",window=wname,policy="forecast",model="chronos",
            quantile=_q(q),lead=60,tp=2,res="15s",path=p,config={"forecast_quantile":q,
            "forecast_req_scale":int(s),"point":f"{q}/s{s}","forecast_suffix":None,
            "arm":"eval-mean-conversion" if mean else "eval",
            "conversion":"mean(native)" if mean else "tail-aware"}))
    for p in sorted(glob.glob(f"{ROOT}/burst[26]_p*_s*.report.json")):
        m=re.match(r"(burst[26])_(p\d+)_s([0-9.]+)\.report\.json$",os.path.basename(p))
        if not m: continue
        win,q,s=m.groups()
        R.append(dict(rid=f"{EXP}:calib_{win}_{q}_s{s}",window=win,policy="forecast",model="chronos",
            quantile=_q(q),lead=60,tp=2,res="15s",path=p,config={"forecast_quantile":q,
            "forecast_req_scale":float(s),"point":f"{q}/s{s}","forecast_suffix":"_expctx","arm":"calibration"}))
    for p in sorted(glob.glob(f"{ROOT}/folds_*/F*_lang_p*_s*.report.json")):
        m=re.search(r"/F(\d)_lang_(p\d+)_s([0-9.]+)\.report\.json$",p)
        if not m: continue
        n,q,s=m.groups()
        R.append(dict(rid=f"{EXP}:fold_F{n}_{q}_s{s}",window=f"F{n}",policy="forecast",model="chronos",
            quantile=_q(q),lead=60,tp=2,res="15s",path=p,config={"forecast_quantile":q,
            "forecast_req_scale":float(s),"point":f"{q}/s{s}","forecast_suffix":"_expctx","arm":"fold"}))
    for p in sorted(glob.glob(f"{ROOT}/baseline_*/react_*.report.json")):
        base=os.path.basename(p); sub="bcalib" if "baseline_calib" in p else "beval"
        m=re.match(r"react_(burst\d)_t(\d+)_(\d+)\.report\.json$",base)
        mp=re.match(r"react_(burst\d)_pred_(\w+)\.report\.json$",base)
        if m:
            W,t1,t2=m.groups(); pred="arima"; rid=f"{EXP}:{sub}_react_{W}_t{t1}_{t2}"
            cfg={"targets":f"{t1}/{t2}","predictor":pred}
        elif mp:
            W,pred=mp.groups(); rid=f"{EXP}:{sub}_react_{W}_pred_{pred}"
            cfg={"targets":"200/20","predictor":pred}
        else: continue
        cfg.update(arm=("baseline-calib" if sub=="bcalib" else "baseline-eval"),
                   variant="Dynamo SLA planner (B), ARIMA slot", conversion="mean(native)")
        R.append(dict(rid=rid,window=W,policy="reactive",model=pred,quantile=None,lead=60,tp=2,res=None,path=p,config=cfg))
    for p in sorted(glob.glob(f"{ROOT}/baseline_*/static_*.report.json")):
        base=os.path.basename(p); sub="bcalib" if "baseline_calib" in p else "beval"
        m=re.match(r"static_(burst\d)_tp(\d+)x(\d+)\.report\.json$",base)
        if not m: continue
        W,tp,n=m.groups()
        R.append(dict(rid=f"{EXP}:{sub}_static_{W}_tp{tp}x{n}",window=W,policy="static",model=None,
            quantile=None,lead=0,tp=int(tp),res=None,path=p,
            config={"tp":int(tp),"n_replicas":int(n),"arm":("baseline-calib" if sub=="bcalib" else "baseline-eval")}))
    # --- week-scale (aggregate window) additions, 2026-07-25 -------------------------------------
    # extra_week forecast arms: conversion-lever (Chronos p90 + MEAN conversion, s=1) and the
    # model-independence check of the robust point (Toto / TimesFM p90/s6).
    for p in sorted(glob.glob(f"{ROOT}/extra_week/week_*.report.json")):
        m=re.match(r"week_([a-z]+)_(p\d+)_s([0-9.]+)(_meanconv)?\.report\.json$",os.path.basename(p))
        if not m: continue
        model,q,s,mean=m.groups(); is_mean=bool(mean) or s=="1"
        R.append(dict(rid=f"{EXP}:week_{model}_{q}_s{s}"+("_meanconv" if mean else ""),
            window="aggregate",policy="forecast",model=model,quantile=_q(q),lead=60,tp=2,res="15s",path=p,
            config={"forecast_quantile":q,"forecast_req_scale":float(s),"point":f"{q}/s{s}",
                "forecast_suffix":None,"arm":"week-extra",
                "conversion":"mean(native)" if is_mean else "tail-aware"}))
    # baseline_week: symmetric week-scale reactive + static on the aggregate composed trace.
    for p in sorted(glob.glob(f"{ROOT}/baseline_week/react_aggregate_*.report.json")):
        m=re.match(r"react_aggregate_t(\d+)_(\d+)\.report\.json$",os.path.basename(p))
        if not m: continue
        t1,t2=m.groups()
        R.append(dict(rid=f"{EXP}:bweek_react_aggregate_t{t1}_{t2}",window="aggregate",policy="reactive",
            model="arima",quantile=None,lead=60,tp=2,res=None,path=p,
            config={"targets":f"{t1}/{t2}","predictor":"arima","arm":"baseline-week",
                "variant":"Dynamo SLA planner (B), ARIMA slot","conversion":"mean(native)"}))
    for p in sorted(glob.glob(f"{ROOT}/baseline_week/static_aggregate_*.report.json")):
        m=re.match(r"static_aggregate_tp(\d+)x(\d+)\.report\.json$",os.path.basename(p))
        if not m: continue
        tp,n=m.groups()
        R.append(dict(rid=f"{EXP}:bweek_static_aggregate_tp{tp}x{n}",window="aggregate",policy="static",
            model=None,quantile=None,lead=0,tp=int(tp),res=None,path=p,
            config={"tp":int(tp),"n_replicas":int(n),"arm":"baseline-week"}))
    return R

def main():
    stmts=[]; runs=discover()
    for r in runs:
        assert r["rid"].startswith(f"{EXP}:"), r["rid"]
        rep=json.load(open(r["path"]))
        cfg=dict(r["config"]); cfg.setdefault("note","language calib+baseline batch, ledger 2026-07-24/25")
        run={"run_id":r["rid"],"experiment":EXP,"pool":"language","window_name":r["window"],
             "policy":r["policy"],"model":r["model"],"quantile":r["quantile"],"resolution":r["res"],
             "lead_s":r["lead"],"tp":r["tp"],"converter":"aic","kind":"K1","source_path":r["path"],
             "is_current":True,"config":cfg}
        stmts.append(ic.upsert_sql("runs",run,"run_id",jsonb_cols=("config",)))
        llm={"run_id":r["rid"]}
        for c in LLM_COLS:
            if rep.get(c) is not None: llm[c]=rep[c]
        llm["metrics"]=rep; llm["has_raw_records"]=False
        stmts.append(ic.upsert_sql("llm_run_summary",llm,"run_id",jsonb_cols=("metrics",)))
        sha,nb=ic.file_meta(r["path"]); stmts.append(ic.ingest_sql(r["path"],sha,"K1",1,r["rid"],nb))
    print(f"upserting {len(runs)} runs ({len(stmts)} stmts)")
    db.run_sql("begin;\n"+";\n".join(stmts)+";\ncommit;")
    for pol in ("forecast","reactive","static"):
        c=db.scalar(f"select count(*) from provenance.runs where experiment='{EXP}' and policy='{pol}'")
        print(f"  {pol}: {c}")
    print("total langcalib:",db.scalar(f"select count(*) from provenance.runs where experiment='{EXP}'"))

if __name__=="__main__": main()
