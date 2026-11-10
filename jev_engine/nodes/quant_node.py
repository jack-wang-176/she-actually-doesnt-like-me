#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/quant_node.py
分布式节点 1：客观行为量化特征节点 (QuantFeatureNode)
仅消费 shards/meta_shard.json 与 shards/session_shard.json，不接触原始聊天文件。
输出：state/quant_state.json
"""

import json
from pathlib import Path


def _calc_latency_metrics(latencies):
    if not latencies:
        return {"mean_sec": 0.0, "median_sec": 0, "fast_reply_pct": 0.0, "slow_reply_pct": 0.0}
    s = sorted(latencies)
    mean_sec = round(sum(s) / len(s), 1)
    median_sec = int(s[len(s) // 2])
    fast_pct = round(sum(1 for x in s if x <= 30) / len(s) * 100.0, 1)
    slow_pct = round(sum(1 for x in s if x >= 7200) / len(s) * 100.0, 1)
    return {
        "mean_sec": mean_sec,
        "median_sec": median_sec,
        "fast_reply_pct": fast_pct,
        "slow_reply_pct": slow_pct,
    }


def run_quant_node(shards_dir: Path, state_dir: Path) -> dict:
    shards_dir = Path(shards_dir)
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)

    meta = json.loads((shards_dir / "meta_shard.json").read_text(encoding="utf-8"))
    sess = json.loads((shards_dir / "session_shard.json").read_text(encoding="utf-8"))

    totals = meta["totals"]
    span = meta["span"]
    total_msgs = max(1, totals["total_messages"])
    total_sessions = max(1, sess["total_sessions"])

    self_init = sum(1 for x in sess["sessions"] if x["initiated_by"] == "SELF")
    peer_init = total_sessions - self_init
    self_close = sum(1 for x in sess["sessions"] if x["closed_by"] == "SELF")
    peer_close = total_sessions - self_close

    self_init_pct = round(self_init / total_sessions * 100.0, 1)
    peer_init_pct = round(peer_init / total_sessions * 100.0, 1)

    self_chars = totals["self_chars"]
    peer_chars = max(1, totals["peer_chars"])
    char_ratio = round(self_chars / peer_chars, 2)

    self_lat = _calc_latency_metrics(sess.get("self_latencies_sec", []))
    peer_lat = _calc_latency_metrics(sess.get("peer_latencies_sec", []))

    late_night_pct = round(totals["late_night_messages"] / total_msgs * 100.0, 1)
    daily_avg = round(total_msgs / max(1, span["span_days"]), 1)

    # 表层活跃度评分 (Surface Vitality Score, 0-100)：反映未去滤镜前的线上热闹程度
    speed_score = min(40.0, peer_lat["fast_reply_pct"] * 0.55)
    volume_score = min(35.0, daily_avg * 2.2)
    night_score = min(25.0, late_night_pct * 0.5)
    surface_vitality_score = round(min(100.0, speed_score + volume_score + night_score), 1)

    # 投入对称性评分 (Symmetry Index, 0-100)：越接近 50:50 越高，单向破冰或字数顺差越大越低
    init_imbalance = abs(self_init_pct - 50.0) * 1.2
    char_imbalance = min(40.0, abs(char_ratio - 1.0) * 20.0)
    symmetry_index = round(max(5.0, 100.0 - init_imbalance - char_imbalance), 1)

    quant_state = {
        "schema_version": "1.0",
        "node_id": meta["node_id"],
        "node_hash": meta["node_hash"],
        "span": span,
        "volume": {
            "total_messages": totals["total_messages"],
            "daily_avg_messages": daily_avg,
            "self_messages": totals["self_messages"],
            "peer_messages": totals["peer_messages"],
            "self_msg_pct": round(totals["self_messages"] / total_msgs * 100.0, 1),
            "peer_msg_pct": round(totals["peer_messages"] / total_msgs * 100.0, 1),
            "self_chars": self_chars,
            "peer_chars": totals["peer_chars"],
            "char_investment_ratio": char_ratio,
            "self_avg_chars": round(self_chars / max(1, totals["self_messages"]), 1),
            "peer_avg_chars": round(totals["peer_chars"] / max(1, totals["peer_messages"]), 1),
            "self_long_msgs": totals["self_long_msgs"],
            "peer_long_msgs": totals["peer_long_msgs"],
        },
        "dynamics": {
            "total_sessions": sess["total_sessions"],
            "self_initiations": self_init,
            "peer_initiations": peer_init,
            "self_initiation_pct": self_init_pct,
            "peer_initiation_pct": peer_init_pct,
            "self_closings": self_close,
            "peer_closings": peer_close,
            "late_night_messages": totals["late_night_messages"],
            "late_night_pct": late_night_pct,
            "silence_breaks": sess.get("silence_breaks", []),
        },
        "latency": {
            "self": self_lat,
            "peer": peer_lat,
        },
        "monthly_vectors": sess.get("monthly_vectors", {}),
        "indices": {
            "surface_vitality_score": surface_vitality_score,
            "symmetry_index": symmetry_index,
        },
    }

    (state_dir / "quant_state.json").write_text(json.dumps(quant_state, ensure_ascii=False, indent=2), encoding="utf-8")
    return quant_state
