#!/usr/bin/env python
"""Phase 5.1 live anchor: VirtualConnector -> mocker-process reconciler.

Closes the loop the Dynamo tree leaves open (nothing in-repo consumes
VirtualConnector decisions for live workers): watch the planner's scaling
decisions in etcd, reconcile the set of live `dynamo.mocker` worker
processes to the decided replica count, and acknowledge each decision.

Protocol (lib/bindings/python/rust/planner.rs):
  planner writes {num_prefill_workers, num_decode_workers, decision_id}
  under v1/{ns}/planner/  ->  we get()/wait(), scale, complete(event)
  (writes scaled_decision_id).

Cold-start lead semantics (parity with the offline replay's WorkerReady
scheduling, where a scaling-up worker is INVISIBLE to the router until
now+startup_time): live mocker --startup-time instead registers the
worker immediately and stalls its requests — a routable-but-dead window
the router would happily fill. So leads are modeled here: a scale-up
spawns each new worker after --spawn-delay seconds (= L minus the
measured spawn-to-ready latency of a mocker process); a scale-down takes
effect immediately (cancel pending spawns first, then SIGTERM newest).
Decisions are acknowledged immediately after scheduling the action, so
cold starts never block planner cadence — exactly the offline behavior.

Every decision/spawn/kill is appended as JSONL to --log: the live
scaling timeline compared against the offline twin.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time

from dynamo._core import DistributedRuntime, VirtualConnectorClient

PY = sys.executable


class Manager:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.procs: list[subprocess.Popen] = []
        self.pending: list[asyncio.Task] = []
        self.seq = 0

    def log(self, **kw) -> None:
        kw.setdefault("t_wall", time.time())
        with open(self.args.log, "a") as f:
            f.write(json.dumps(kw) + "\n")
        print(f"[manager] {kw}", flush=True)

    def _cmd(self) -> list[str]:
        a = self.args
        cmd = [
            PY, "-m", "dynamo.mocker",
            "--model-path", a.model_path,
            "--endpoint", f"dyn://{a.namespace}.backend.generate",
            "--extra-engine-args", a.engine_args,
        ]
        if a.model_name:
            cmd += ["--model-name", a.model_name]
        if a.mocker_extra:
            cmd += a.mocker_extra.split()
        return cmd

    def _spawn_now(self, reason: str) -> None:
        self.seq += 1
        out = open(os.path.join(self.args.rundir,
                                f"mocker_{self.seq}.log"), "w")
        p = subprocess.Popen(self._cmd(), stdout=out, stderr=out,
                             env=os.environ.copy())
        self.procs.append(p)
        self.log(event="spawn", pid=p.pid, seq=self.seq, reason=reason,
                 n_live=len(self.procs), n_pending=len(self.pending))

    async def _delayed_spawn(self, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            raise
        self._spawn_now(reason=f"lead+{delay:.0f}s")

    def _reap(self) -> None:
        for p in list(self.procs):
            if p.poll() is not None:
                self.log(event="died", pid=p.pid, rc=p.returncode)
                self.procs.remove(p)
        self.pending = [t for t in self.pending if not t.done()]

    def scale_to(self, target: int) -> None:
        """Reconcile live+pending toward target (floor at --min-workers)."""
        target = max(target, self.args.min_workers)
        self._reap()
        effective = len(self.procs) + len(self.pending)
        while effective < target:
            if self.args.spawn_delay > 0:
                t = asyncio.get_running_loop().create_task(
                    self._delayed_spawn(self.args.spawn_delay))
                self.pending.append(t)
                self.log(event="spawn_scheduled",
                         delay_s=self.args.spawn_delay,
                         n_live=len(self.procs),
                         n_pending=len(self.pending))
            else:
                self._spawn_now(reason="immediate")
            effective += 1
        while effective > target:
            if self.pending:  # cheapest first: capacity not yet real
                t = self.pending.pop()
                t.cancel()
                self.log(event="spawn_cancelled",
                         n_live=len(self.procs),
                         n_pending=len(self.pending))
            else:
                p = self.procs.pop()  # LIFO
                p.send_signal(signal.SIGTERM)
                self.log(event="sigterm", pid=p.pid,
                         n_live=len(self.procs))
            effective -= 1

    def killall(self) -> None:
        for t in self.pending:
            t.cancel()
        self.pending = []
        for p in self.procs:
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
        deadline = time.time() + 15
        for p in self.procs:
            try:
                p.wait(timeout=max(0.1, deadline - time.time()))
            except subprocess.TimeoutExpired:
                p.kill()
        self.procs = []


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--namespace", required=True)
    ap.add_argument("--model-path", required=True)
    ap.add_argument("--model-name", default="")
    ap.add_argument("--engine-args", required=True,
                    help="MockEngineArgs JSON path (aic_*; NO startup_time)")
    ap.add_argument("--initial-workers", type=int, default=1)
    ap.add_argument("--min-workers", type=int, default=1)
    ap.add_argument("--spawn-delay", type=float, default=0.0,
                    help="cold-start lead L minus measured spawn-to-ready")
    ap.add_argument("--mocker-extra", default="")
    ap.add_argument("--log", required=True)
    ap.add_argument("--rundir", default=".")
    args = ap.parse_args()
    os.makedirs(args.rundir, exist_ok=True)

    loop = asyncio.get_running_loop()
    runtime = DistributedRuntime(loop, "etcd", "nats")
    client = VirtualConnectorClient(runtime, args.namespace)

    m = Manager(args)
    for _ in range(args.initial_workers):
        m._spawn_now(reason="initial")
    m.log(event="start", initial=args.initial_workers,
          spawn_delay=args.spawn_delay)

    stop = asyncio.Event()
    loop.add_signal_handler(signal.SIGINT, stop.set)
    loop.add_signal_handler(signal.SIGTERM, stop.set)

    last_id = -1
    try:
        while not stop.is_set():
            try:
                ev = await asyncio.wait_for(client.get(), timeout=20)
            except asyncio.TimeoutError:
                m._reap()
                continue
            if ev.decision_id > last_id and ev.decision_id >= 0:
                last_id = ev.decision_id
                m.log(event="decision", decision_id=ev.decision_id,
                      num_prefill=ev.num_prefill_workers,
                      num_decode=ev.num_decode_workers,
                      n_live=len(m.procs), n_pending=len(m.pending))
                m.scale_to(ev.num_decode_workers)
                await client.complete(ev)
                m.log(event="ack", decision_id=ev.decision_id,
                      n_live=len(m.procs), n_pending=len(m.pending))
            else:
                # PyO3 async methods return Futures, not coroutines
                waiter = asyncio.ensure_future(client.wait())
                stopper = asyncio.ensure_future(stop.wait())
                done, pend = await asyncio.wait(
                    {waiter, stopper}, timeout=30,
                    return_when=asyncio.FIRST_COMPLETED)
                for t in pend:
                    t.cancel()
                m._reap()
    finally:
        m.log(event="shutdown", n_live=len(m.procs),
              n_pending=len(m.pending))
        m.killall()
        # Hard-exit: pending PyO3 futures (client.wait/get) abort the
        # process during interpreter teardown ("FATAL: exception not
        # rethrown"); all state is already flushed to the JSONL log.
        os._exit(0)


if __name__ == "__main__":
    asyncio.run(main())
