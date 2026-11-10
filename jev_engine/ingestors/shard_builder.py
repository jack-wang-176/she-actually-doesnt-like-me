#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/ingestors/shard_builder.py
解耦式导入层：将不同来源的原始聊天数据（JSON / CSV / TXT / SQLite）
抽象为与具体分析逻辑解耦的「分布式节点切片 (Distributed Shards)」：
  - shards/meta_shard.json     : 时间跨度、活跃天数、消息总量等基础元数据
  - shards/session_shard.json  : 分布式会话级向量（破冰方、终结方、回复时延分布、深夜特征）
  - shards/slice_shard.json    : 关键语义窗口切片（高频升温切片、长时延冷场切片、长文剖白交互切片）
"""

import csv
import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse_timestamp(val):
    if not val:
        return None
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val / 1000.0 if val > 1e11 else val)
    if isinstance(val, str):
        val = val.strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M",
        ):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                pass
        try:
            ts = float(val)
            return datetime.fromtimestamp(ts / 1000.0 if ts > 1e11 else ts)
        except ValueError:
            pass
    return None


def _parse_json_file(file_path: Path):
    data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
    msgs_raw = []
    if isinstance(data, list):
        msgs_raw = data
    elif isinstance(data, dict):
        for k in ("messages", "data", "chat", "msg_list", "records"):
            if isinstance(data.get(k), list):
                msgs_raw = data[k]
                break
        if not msgs_raw:
            msgs_raw = [data]

    records = []
    for m in msgs_raw:
        if not isinstance(m, dict):
            continue
        raw_ts = (
            m.get("timestamp") or m.get("time") or m.get("ts") or
            m.get("StrTime") or m.get("create_time") or m.get("datetime") or m.get("createTime")
        )
        dt = parse_timestamp(raw_ts)
        if not dt:
            continue
        content = str(
            m.get("content") or m.get("StrContent") or m.get("text") or
            m.get("message") or m.get("msg") or ""
        ).strip()
        is_self = False
        if "isSend" in m:
            is_self = bool(m["isSend"] == 1 or m["isSend"] is True)
        elif "is_sender" in m:
            is_self = bool(m["is_sender"])
        elif "is_me" in m:
            is_self = bool(m["is_me"])
        elif "IsSender" in m:
            is_self = bool(m["IsSender"])
        else:
            sender = str(m.get("sender") or m.get("from") or "").lower()
            is_self = sender in ("me", "self", "我")

        records.append({
            "dt": dt,
            "ts": int(dt.timestamp()),
            "is_self": is_self,
            "content": content,
            "char_len": len(content),
        })
    records.sort(key=lambda x: x["ts"])
    return records


def _parse_csv_file(file_path: Path):
    records = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_ts = (
                row.get("timestamp") or row.get("time") or row.get("StrTime") or
                row.get("datetime") or row.get("时间") or row.get("发送时间")
            )
            dt = parse_timestamp(raw_ts)
            if not dt:
                continue
            content = str(
                row.get("content") or row.get("StrContent") or row.get("message") or
                row.get("内容") or row.get("消息内容") or ""
            ).strip()
            is_sender_val = row.get("is_sender") or row.get("IsSender") or row.get("是否我发送")
            sender = str(row.get("sender") or row.get("发送人") or "").strip()
            if is_sender_val is not None:
                is_self = str(is_sender_val).strip() in ("1", "true", "True", "是")
            else:
                is_self = sender.lower() in ("我", "me", "self")
            records.append({
                "dt": dt,
                "ts": int(dt.timestamp()),
                "is_self": is_self,
                "content": content,
                "char_len": len(content),
            })
    records.sort(key=lambda x: x["ts"])
    return records


def _parse_txt_file(file_path: Path):
    records = []
    pattern = re.compile(r"^(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s+([^\n:]+?)[:\s]+(.*)$")
    curr = None
    for line in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = pattern.match(line)
        if m:
            if curr:
                records.append(curr)
            dt_str, sdr, cnt = m.groups()
            dt = parse_timestamp(dt_str)
            if not dt:
                curr = None
                continue
            is_self = sdr.strip().lower() in ("我", "me", "self")
            curr = {
                "dt": dt,
                "ts": int(dt.timestamp()),
                "is_self": is_self,
                "content": cnt.strip(),
                "char_len": len(cnt.strip()),
            }
        elif curr:
            curr["content"] += "\n" + line.strip()
            curr["char_len"] = len(curr["content"])
    if curr:
        records.append(curr)
    records.sort(key=lambda x: x["ts"])
    return records


def load_raw_records(raw_source: Path):
    p = Path(raw_source)
    if not p.exists():
        return []
    if p.is_file():
        suf = p.suffix.lower()
        if suf == ".json":
            return _parse_json_file(p)
        if suf in (".csv", ".tsv"):
            return _parse_csv_file(p)
        if suf in (".txt", ".log"):
            return _parse_txt_file(p)
        return []

    excluded = {"manifest.json", "quant_metrics.json", "stats.json", "analysis.json"}
    for f in sorted(p.rglob("*.json")):
        if f.name not in excluded and "shards" not in f.parts and "state" not in f.parts:
            recs = _parse_json_file(f)
            if recs:
                return recs
    for f in sorted(p.rglob("*.csv")):
        recs = _parse_csv_file(f)
        if recs:
            return recs
    for f in sorted(p.rglob("*.txt")):
        if "shards" not in f.parts and "state" not in f.parts:
            recs = _parse_txt_file(f)
            if recs:
                return recs
    return []


def build_distributed_shards(contact_id: str, raw_dir: Path, shards_dir: Path, gap_threshold: int = 7200):
    """
    将原始记录转换为分布式节点切片 (meta_shard, session_shard, slice_shard)。
    后续所有分析节点仅读取 shards/，实现导入与分析的彻底解耦。
    """
    records = load_raw_records(raw_dir)
    if not records:
        return None

    shards_dir = Path(shards_dir)
    shards_dir.mkdir(parents=True, exist_ok=True)

    node_hash = hashlib.sha256(contact_id.encode("utf-8")).hexdigest()[:10]
    first_dt, last_dt = records[0]["dt"], records[-1]["dt"]
    span_days = max(1, (last_dt.date() - first_dt.date()).days + 1)
    active_days = len({r["dt"].date() for r in records})

    # 切分分布式会话流
    sessions = []
    curr_sess = [records[0]]
    for i in range(1, len(records)):
        gap = records[i]["ts"] - records[i - 1]["ts"]
        if gap > gap_threshold:
            sessions.append((gap, curr_sess))
            curr_sess = [records[i]]
        else:
            curr_sess.append(records[i])
    if curr_sess:
        sessions.append((0, curr_sess))

    # 构建每月趋势与会话特征向量
    monthly_vectors = defaultdict(lambda: {"total": 0, "self_cnt": 0, "peer_cnt": 0, "self_chars": 0, "peer_chars": 0})
    for r in records:
        ym = r["dt"].strftime("%Y-%m")
        monthly_vectors[ym]["total"] += 1
        if r["is_self"]:
            monthly_vectors[ym]["self_cnt"] += 1
            monthly_vectors[ym]["self_chars"] += r["char_len"]
        else:
            monthly_vectors[ym]["peer_cnt"] += 1
            monthly_vectors[ym]["peer_chars"] += r["char_len"]

    session_vectors = []
    self_latencies, peer_latencies = [], []
    silence_breaks = []

    for idx, (next_gap, s) in enumerate(sessions):
        is_night = any(m["dt"].hour >= 22 or m["dt"].hour < 2 for m in s)
        s_self_chars = sum(m["char_len"] for m in s if m["is_self"])
        s_peer_chars = sum(m["char_len"] for m in s if not m["is_self"])

        for j in range(1, len(s)):
            if s[j - 1]["is_self"] != s[j]["is_self"]:
                diff = max(0, s[j]["ts"] - s[j - 1]["ts"])
                if s[j]["is_self"]:
                    self_latencies.append(diff)
                else:
                    peer_latencies.append(diff)

        if idx > 0:
            prev_end_ts = sessions[idx - 1][1][-1]["ts"]
            silence_days = round((s[0]["ts"] - prev_end_ts) / 86400.0, 1)
            if silence_days >= 7.0:
                silence_breaks.append({
                    "silence_days": silence_days,
                    "re_initiated_by": "SELF" if s[0]["is_self"] else "PEER",
                    "timestamp": s[0]["dt"].strftime("%Y-%m-%d %H:%M:%S"),
                    "opening_preview": s[0]["content"][:80],
                })

        session_vectors.append({
            "session_index": idx,
            "start_time": s[0]["dt"].strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": s[-1]["dt"].strftime("%Y-%m-%d %H:%M:%S"),
            "msg_count": len(s),
            "initiated_by": "SELF" if s[0]["is_self"] else "PEER",
            "closed_by": "SELF" if s[-1]["is_self"] else "PEER",
            "self_chars": s_self_chars,
            "peer_chars": s_peer_chars,
            "has_late_night": is_night,
        })

    # 提取长文交互切片 (检测单向深度剖白 vs 回避型回复)
    long_exchanges = []
    for idx, r in enumerate(records):
        if r["char_len"] >= 120 and not r["content"].startswith(("public class", "import ", "1. ")):
            window = records[max(0, idx - 1):min(len(records), idx + 15)]
            long_exchanges.append({
                "anchor_time": r["dt"].strftime("%Y-%m-%d %H:%M:%S"),
                "author": "SELF" if r["is_self"] else "PEER",
                "char_len": r["char_len"],
                "window": [
                    {
                        "time": w["dt"].strftime("%Y-%m-%d %H:%M:%S"),
                        "role": "SELF" if w["is_self"] else "PEER",
                        "text": w["content"][:300],
                    }
                    for w in window
                ],
            })

    meta_shard = {
        "schema_version": "1.0",
        "node_id": contact_id,
        "node_hash": f"node_{node_hash}",
        "ingested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "span": {
            "start_time": first_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": last_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "span_days": span_days,
            "active_days": active_days,
        },
        "totals": {
            "total_messages": len(records),
            "self_messages": sum(1 for r in records if r["is_self"]),
            "peer_messages": sum(1 for r in records if not r["is_self"]),
            "self_chars": sum(r["char_len"] for r in records if r["is_self"]),
            "peer_chars": sum(r["char_len"] for r in records if not r["is_self"]),
            "self_long_msgs": sum(1 for r in records if r["is_self"] and r["char_len"] >= 50),
            "peer_long_msgs": sum(1 for r in records if not r["is_self"] and r["char_len"] >= 50),
            "late_night_messages": sum(1 for r in records if r["dt"].hour >= 22 or r["dt"].hour < 2),
        },
    }

    session_shard = {
        "node_id": contact_id,
        "total_sessions": len(session_vectors),
        "self_latencies_sec": self_latencies,
        "peer_latencies_sec": peer_latencies,
        "monthly_vectors": dict(monthly_vectors),
        "silence_breaks": silence_breaks,
        "sessions": session_vectors,
    }

    slice_shard = {
        "node_id": contact_id,
        "long_exchanges": long_exchanges[:10],
    }

    (shards_dir / "meta_shard.json").write_text(json.dumps(meta_shard, ensure_ascii=False, indent=2), encoding="utf-8")
    (shards_dir / "session_shard.json").write_text(json.dumps(session_shard, ensure_ascii=False, indent=2), encoding="utf-8")
    (shards_dir / "slice_shard.json").write_text(json.dumps(slice_shard, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "meta_shard": meta_shard,
        "session_shard": session_shard,
        "slice_shard": slice_shard,
    }
