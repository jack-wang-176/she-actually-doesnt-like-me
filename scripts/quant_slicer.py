#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/quant_slicer.py
多联系人聊天记录量化统计与高能切片分析引擎
支持格式：JSON (SIWX, MemoTrace, WeChatMsg, NapCat 等), CSV, TXT, SQLite (.db)
标准目录架构：
  - 输入：contacts/<联系人>/raw/
  - 输出：
      - contacts/<联系人>/reports/quant_metrics.json (全量结构化指标)
      - contacts/<联系人>/reports/quant_summary.md (人类可读量化体检报告)
      - data/chat_metrics.db (全局多联系人 SQLite 指标库)
用法：
  python scripts/quant_slicer.py --contact "女生备注"
  python scripts/quant_slicer.py --all
  python scripts/quant_slicer.py --input /path/to/raw_dir --contact "女生备注"
"""

import os
import sys
import json
import csv
import re
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

WORKSPACE = Path(__file__).resolve().parent.parent
CONTACTS_DIR = WORKSPACE / "contacts"
TEMPLATES_DIR = WORKSPACE / "templates"
DATA_DIR = WORKSPACE / "data"


def parse_time(val):
    if not val:
        return None
    if isinstance(val, (int, float)):
        if val > 1e11:
            return datetime.fromtimestamp(val / 1000.0)
        return datetime.fromtimestamp(val)
    if isinstance(val, str):
        val = val.strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M",
            "%m-%d %H:%M:%S"
        ):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                pass
        try:
            ts = float(val)
            if ts > 1e11:
                return datetime.fromtimestamp(ts / 1000.0)
            return datetime.fromtimestamp(ts)
        except ValueError:
            pass
    return None


def load_from_json(file_path):
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)

    msgs_raw = []
    if isinstance(data, list):
        msgs_raw = data
    elif isinstance(data, dict):
        for k in ("messages", "data", "chat", "msg_list", "records"):
            if k in data and isinstance(data[k], list):
                msgs_raw = data[k]
                break
        if not msgs_raw:
            msgs_raw = [data]

    normalized = []
    for m in msgs_raw:
        if not isinstance(m, dict):
            continue
        raw_ts = (
            m.get("timestamp") or m.get("time") or m.get("ts") or
            m.get("StrTime") or m.get("create_time") or m.get("datetime") or m.get("createTime")
        )
        dt = parse_time(raw_ts)
        if not dt:
            continue

        content = (
            m.get("content") or m.get("StrContent") or m.get("text") or
            m.get("message") or m.get("msg") or ""
        )
        if not isinstance(content, str):
            content = str(content)

        is_me = False
        sender = (
            m.get("senderDisplayName") or m.get("sender") or m.get("sender_name") or
            m.get("from") or m.get("user_id") or m.get("talker") or "对方"
        )
        if "isSend" in m:
            is_me = (m["isSend"] == 1 or m["isSend"] is True)
        elif "is_sender" in m:
            is_me = bool(m["is_sender"])
        elif "is_me" in m:
            is_me = bool(m["is_me"])
        elif "IsSender" in m:
            is_me = bool(m["IsSender"])
        elif str(sender).lower() in ("me", "self", "我"):
            is_me = True

        msg_type = str(m.get("typeName") or m.get("type") or m.get("Type") or m.get("msg_type") or "text")

        normalized.append({
            "datetime": dt,
            "timestamp": int(dt.timestamp()),
            "sender": "我" if is_me else str(sender),
            "is_me": is_me,
            "content": content.strip(),
            "msg_type": msg_type,
            "char_count": len(content.strip())
        })

    normalized.sort(key=lambda x: x["timestamp"])
    return normalized


def load_from_csv(file_path):
    normalized = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_ts = (
                row.get("timestamp") or row.get("time") or row.get("StrTime") or
                row.get("datetime") or row.get("时间") or row.get("发送时间")
            )
            dt = parse_time(raw_ts)
            if not dt:
                continue

            content = (
                row.get("content") or row.get("StrContent") or row.get("message") or
                row.get("内容") or row.get("消息内容") or ""
            )
            sender = (
                row.get("sender") or row.get("talker") or row.get("发送人") or
                row.get("发送者") or "对方"
            )
            is_me = False
            is_sender_val = row.get("is_sender") or row.get("IsSender") or row.get("是否我发送")
            if is_sender_val is not None:
                is_me = str(is_sender_val).strip() in ("1", "true", "True", "是")
            elif sender in ("我", "me", "self"):
                is_me = True

            msg_type = row.get("type") or row.get("Type") or row.get("类型") or "text"

            normalized.append({
                "datetime": dt,
                "timestamp": int(dt.timestamp()),
                "sender": "我" if is_me else str(sender),
                "is_me": is_me,
                "content": str(content).strip(),
                "msg_type": str(msg_type),
                "char_count": len(str(content).strip())
            })

    normalized.sort(key=lambda x: x["timestamp"])
    return normalized


def load_from_txt(file_path):
    normalized = []
    pattern1 = re.compile(r"^(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s+([^\n:]+?)[:\s]+(.*)$")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        curr_msg = None
        for line in f:
            m = pattern1.match(line)
            if m:
                if curr_msg:
                    normalized.append(curr_msg)
                dt_str, sdr, cnt = m.groups()
                dt = parse_time(dt_str)
                is_me = sdr.strip() in ("我", "me", "Self")
                curr_msg = {
                    "datetime": dt,
                    "timestamp": int(dt.timestamp()) if dt else 0,
                    "sender": "我" if is_me else sdr.strip(),
                    "is_me": is_me,
                    "content": cnt.strip(),
                    "msg_type": "text",
                    "char_count": len(cnt.strip())
                }
            else:
                if curr_msg:
                    curr_msg["content"] += "\n" + line.strip()
                    curr_msg["char_count"] = len(curr_msg["content"])
        if curr_msg:
            normalized.append(curr_msg)

    normalized = [m for m in normalized if m["timestamp"] > 0]
    normalized.sort(key=lambda x: x["timestamp"])
    return normalized


def load_from_sqlite(file_path):
    conn = sqlite3.connect(file_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

    target_tbl = None
    for tbl in ("message", "messages", "Msg", "chat_message"):
        if tbl in tables:
            target_tbl = tbl
            break
    if not target_tbl and tables:
        target_tbl = tables[0]

    if not target_tbl:
        conn.close()
        return []

    cols = [c[1] for c in cursor.execute(f"PRAGMA table_info({target_tbl})").fetchall()]
    time_col = next((c for c in ("CreateTime", "create_time", "timestamp", "time", "ts") if c in cols), None)
    content_col = next((c for c in ("StrContent", "content", "message", "msg") if c in cols), None)

    normalized = []
    if time_col and content_col:
        rows = cursor.execute(f"SELECT * FROM {target_tbl}").fetchall()
        for r in rows:
            r_dict = dict(r)
            dt = parse_time(r_dict[time_col])
            if not dt:
                continue
            content = str(r_dict.get(content_col) or "")
            is_me = False
            if "IsSender" in cols:
                is_me = bool(r_dict["IsSender"])
            elif "is_sender" in cols:
                is_me = bool(r_dict["is_sender"])
            elif "Des" in cols:
                is_me = (r_dict["Des"] == 0)

            sdr = "我" if is_me else "对方"
            normalized.append({
                "datetime": dt,
                "timestamp": int(dt.timestamp()),
                "sender": sdr,
                "is_me": is_me,
                "content": content.strip(),
                "msg_type": "text",
                "char_count": len(content.strip())
            })
    conn.close()
    normalized.sort(key=lambda x: x["timestamp"])
    return normalized


def load_messages(source_path):
    p = Path(source_path)
    if not p.exists():
        return []
    if p.is_file():
        suffix = p.suffix.lower()
        if suffix == ".json":
            return load_from_json(p)
        elif suffix in (".csv", ".tsv"):
            return load_from_csv(p)
        elif suffix in (".txt", ".log"):
            return load_from_txt(p)
        elif suffix in (".db", ".sqlite", ".sqlite3"):
            return load_from_sqlite(p)
    elif p.is_dir():
        for f in sorted(p.rglob("*.json")):
            if f.name not in ("manifest.json", "quant_metrics.json", "stats.json", "analysis.json"):
                msgs = load_from_json(f)
                if msgs:
                    return msgs
        for f in sorted(p.rglob("*.csv")):
            msgs = load_from_csv(f)
            if msgs:
                return msgs
        for f in sorted(p.rglob("*.txt")):
            msgs = load_from_txt(f)
            if msgs:
                return msgs
        for f in sorted(p.rglob("*.db")):
            msgs = load_from_sqlite(f)
            if msgs:
                return msgs
    return []


def compute_metrics(messages):
    if not messages:
        return {}

    total_msgs = len(messages)
    first_time = messages[0]["datetime"]
    last_time = messages[-1]["datetime"]
    total_days = max(1, (last_time.date() - first_time.date()).days + 1)

    unique_dates = set(m["datetime"].date() for m in messages)
    active_days = len(unique_dates)

    my_msgs = [m for m in messages if m["is_me"]]
    her_msgs = [m for m in messages if not m["is_me"]]

    my_count = len(my_msgs)
    her_count = len(her_msgs)

    my_chars = sum(m["char_count"] for m in my_msgs)
    her_chars = sum(m["char_count"] for m in her_msgs)
    my_avg_chars = round(my_chars / my_count, 1) if my_count else 0
    her_avg_chars = round(her_chars / her_count, 1) if her_count else 0

    my_long_msgs = sum(1 for m in my_msgs if m["char_count"] >= 50)
    her_long_msgs = sum(1 for m in her_msgs if m["char_count"] >= 50)

    late_night_msgs = [m for m in messages if m["datetime"].hour >= 22 or m["datetime"].hour < 2]
    late_night_count = len(late_night_msgs)
    late_night_ratio = round(late_night_count / total_msgs * 100, 1) if total_msgs else 0

    GAP_THRESHOLD = 7200
    sessions = []
    current_session = [messages[0]]

    for i in range(1, total_msgs):
        gap = messages[i]["timestamp"] - messages[i - 1]["timestamp"]
        if gap > GAP_THRESHOLD:
            sessions.append(current_session)
            current_session = [messages[i]]
        else:
            current_session.append(messages[i])
    if current_session:
        sessions.append(current_session)

    total_sessions = len(sessions)
    my_initiations = sum(1 for s in sessions if s[0]["is_me"])
    her_initiations = total_sessions - my_initiations
    my_closings = sum(1 for s in sessions if s[-1]["is_me"])
    her_closings = total_sessions - my_closings

    my_latencies = []
    her_latencies = []

    for s in sessions:
        for i in range(1, len(s)):
            prev, curr = s[i - 1], s[i]
            if prev["is_me"] != curr["is_me"]:
                diff = curr["timestamp"] - prev["timestamp"]
                if diff >= 0:
                    if curr["is_me"]:
                        my_latencies.append(diff)
                    else:
                        her_latencies.append(diff)

    def stats_latency(latencies):
        if not latencies:
            return {"mean_sec": 0, "median_sec": 0, "fast_rate": 0, "slow_rate": 0}
        lat_sorted = sorted(latencies)
        mean_sec = round(sum(latencies) / len(latencies), 1)
        median_sec = lat_sorted[len(lat_sorted) // 2]
        fast_rate = round(sum(1 for x in latencies if x <= 30) / len(latencies) * 100, 1)
        slow_rate = round(sum(1 for x in latencies if x >= 7200) / len(latencies) * 100, 1)
        return {
            "mean_sec": mean_sec,
            "median_sec": median_sec,
            "fast_rate": fast_rate,
            "slow_rate": slow_rate
        }

    my_lat_stats = stats_latency(my_latencies)
    her_lat_stats = stats_latency(her_latencies)

    monthly = defaultdict(lambda: {"total": 0, "my_cnt": 0, "her_cnt": 0, "my_chars": 0, "her_chars": 0})
    for m in messages:
        m_key = m["datetime"].strftime("%Y-%m")
        monthly[m_key]["total"] += 1
        if m["is_me"]:
            monthly[m_key]["my_cnt"] += 1
            monthly[m_key]["my_chars"] += m["char_count"]
        else:
            monthly[m_key]["her_cnt"] += 1
            monthly[m_key]["her_chars"] += m["char_count"]

    scored_sessions = []
    for idx, s in enumerate(sessions):
        if len(s) < 4:
            continue
        is_night = any(m["datetime"].hour >= 22 or m["datetime"].hour < 2 for m in s)
        total_len = sum(m["char_count"] for m in s)
        warmth_score = (len(s) * 2) + (30 if is_night else 0) + (total_len / 20.0)
        scored_sessions.append((warmth_score, "warmth", idx, s))

    scored_sessions.sort(key=lambda x: x[0], reverse=True)
    top_warm_slices = [s[3] for s in scored_sessions[:5]]

    cold_candidates = []
    for idx, s in enumerate(sessions):
        if len(s) >= 2:
            for j in range(1, len(s)):
                if s[j - 1]["is_me"] != s[j]["is_me"]:
                    gap = s[j]["timestamp"] - s[j - 1]["timestamp"]
                    if gap > 1800 and s[j]["char_count"] <= 4:
                        cold_candidates.append((gap, idx, s))
                        break

    cold_candidates.sort(key=lambda x: x[0], reverse=True)
    top_cold_slices = [s[2] for s in cold_candidates[:5]]

    return {
        "summary": {
            "total_messages": total_msgs,
            "start_time": first_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": last_time.strftime("%Y-%m-%d %H:%M:%S"),
            "span_days": total_days,
            "active_days": active_days,
            "daily_avg_messages": round(total_msgs / total_days, 1)
        },
        "volume": {
            "my_messages": my_count,
            "her_messages": her_count,
            "my_ratio_pct": round(my_count / total_msgs * 100, 1) if total_msgs else 0,
            "her_ratio_pct": round(her_count / total_msgs * 100, 1) if total_msgs else 0,
            "my_characters": my_chars,
            "her_characters": her_chars,
            "my_avg_char": my_avg_chars,
            "her_avg_char": her_avg_chars,
            "my_long_messages": my_long_msgs,
            "her_long_messages": her_long_msgs
        },
        "interaction_dynamics": {
            "total_sessions": total_sessions,
            "my_initiations": my_initiations,
            "her_initiations": her_initiations,
            "my_initiation_pct": round(my_initiations / total_sessions * 100, 1) if total_sessions else 0,
            "her_initiation_pct": round(her_initiations / total_sessions * 100, 1) if total_sessions else 0,
            "my_closings": my_closings,
            "her_closings": her_closings,
            "late_night_messages": late_night_count,
            "late_night_ratio_pct": late_night_ratio
        },
        "response_latency": {
            "my_stats": my_lat_stats,
            "her_stats": her_lat_stats
        },
        "monthly_trend": dict(monthly),
        "slices": {
            "warm_slices": [
                [{"time": m["datetime"].strftime("%Y-%m-%d %H:%M:%S"), "sender": m["sender"], "content": m["content"]} for m in slc[:12]]
                for slc in top_warm_slices
            ],
            "cold_slices": [
                [{"time": m["datetime"].strftime("%Y-%m-%d %H:%M:%S"), "sender": m["sender"], "content": m["content"]} for m in slc[:12]]
                for slc in top_cold_slices
            ]
        }
    }


def format_summary_markdown(metrics, contact_name=""):
    sm = metrics["summary"]
    vol = metrics["volume"]
    dyn = metrics["interaction_dynamics"]
    lat = metrics["response_latency"]
    title_prefix = f"【{contact_name}】" if contact_name else ""

    md = f"""# 《{title_prefix}聊天记录硬核量化体检报告》

## 一、基础互动盘点
- **时间跨度**：`{sm['start_time']}` 至 `{sm['end_time']}`（共 {sm['span_days']} 天，活跃互动 {sm['active_days']} 天）
- **消息总量**：双方共发送 **{sm['total_messages']}** 条消息（日均约 {sm['daily_avg_messages']} 条）
- **深夜时段（22:00-02:00）互动**：共 **{dyn['late_night_messages']}** 条，占全部消息的 **{dyn['late_night_ratio_pct']}%**

## 二、双方投入度与主动性对比
| 指标项 | 我 (Me) | 对方 (Her) | 对比态势与解读 |
| :--- | :--- | :--- | :--- |
| **发送消息数** | {vol['my_messages']} 条 ({vol['my_ratio_pct']}%) | {vol['her_messages']} 条 ({vol['her_ratio_pct']}%) | {'双方基本对称' if abs(vol['my_ratio_pct'] - 50) < 5 else ('我方单向输出过多' if vol['my_ratio_pct'] > 55 else '对方投入活跃')} |
| **总字数投入** | {vol['my_characters']} 字 (均字 {vol['my_avg_char']}) | {vol['her_characters']} 字 (均字 {vol['her_avg_char']}) | 均字差: {round(vol['my_avg_char'] - vol['her_avg_char'], 1)} 字 |
| **深度长文(>50字)** | {vol['my_long_messages']} 次 | {vol['her_long_messages']} 次 | 倾诉意愿与情绪承载度指标 |
| **话题主动发起率** | {dyn['my_initiations']} 次 ({dyn['my_initiation_pct']}%) | {dyn['her_initiations']} 次 ({dyn['her_initiation_pct']}%) | {'我方主导破冰' if dyn['my_initiation_pct'] > 60 else ('对方主动性极高' if dyn['her_initiation_pct'] > 50 else '势均力敌')} |
| **话题终结率** | {dyn['my_closings']} 次 | {dyn['her_closings']} 次 | {'我方习惯垫底' if dyn['my_closings'] > dyn['her_closings'] else '对方更有离场决断力'} |

## 三、回复时延与情绪温差
- **我的回复表现**：中位数 **{lat['my_stats']['median_sec']}s**，秒回率（≤30秒）**{lat['my_stats']['fast_rate']}%**，轮回率（≥2小时）**{lat['my_stats']['slow_rate']}%**
- **对方的回复表现**：中位数 **{lat['her_stats']['median_sec']}s**，秒回率（≤30秒）**{lat['her_stats']['fast_rate']}%**，轮回率（≥2小时）**{lat['her_stats']['slow_rate']}%**

## 四、月度互动热度走势
| 月份 | 总消息数 | 我发送 | 对方发送 | 字数比 (我:对方) |
| :--- | :--- | :--- | :--- | :--- |
"""
    for ym, v in sorted(metrics["monthly_trend"].items()):
        ratio_str = f"{round(v['my_chars'] / max(1, v['her_chars']), 2)} : 1"
        md += f"| {ym} | {v['total']} | {v['my_cnt']} | {v['her_cnt']} | {ratio_str} |\n"

    md += """
## 五、核心切片摘要
- 已自动提取 **Top 5 升温/深聊高能切片** 与 **Top 5 降温/防守切片**，详情已存入同目录 `quant_metrics.json`。
"""
    return md


def save_to_sqlite(metrics, db_path, contact_name="unknown"):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_name TEXT,
        analyzed_at TEXT,
        total_messages INTEGER,
        span_days INTEGER,
        my_ratio_pct REAL,
        her_ratio_pct REAL,
        my_initiation_pct REAL,
        her_initiation_pct REAL,
        her_median_latency INTEGER,
        raw_json TEXT
    )
    """)
    cols = [c[1] for c in cursor.execute("PRAGMA table_info(metrics_summary)").fetchall()]
    if "contact_name" not in cols:
        cursor.execute("ALTER TABLE metrics_summary ADD COLUMN contact_name TEXT DEFAULT 'unknown'")

    sm = metrics["summary"]
    vol = metrics["volume"]
    dyn = metrics["interaction_dynamics"]
    lat = metrics["response_latency"]

    cursor.execute("""
    INSERT INTO metrics_summary (
        contact_name, analyzed_at, total_messages, span_days, my_ratio_pct, her_ratio_pct,
        my_initiation_pct, her_initiation_pct, her_median_latency, raw_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        contact_name,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        sm["total_messages"],
        sm["span_days"],
        vol["my_ratio_pct"],
        vol["her_ratio_pct"],
        dyn["my_initiation_pct"],
        dyn["her_initiation_pct"],
        lat["her_stats"]["median_sec"],
        json.dumps(metrics, ensure_ascii=False)
    ))
    conn.commit()
    conn.close()


def ensure_templates(contact_dir, contact_name):
    profile_dir = contact_dir / "profile"
    reports_dir = contact_dir / "reports"
    profile_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now().strftime("%Y-%m-%d")

    mapping = {
        TEMPLATES_DIR / "her_profile.template.md": profile_dir / "her_profile.md",
        TEMPLATES_DIR / "interaction_red_flags.template.md": profile_dir / "interaction_red_flags.md",
        TEMPLATES_DIR / "shared_memories.template.md": profile_dir / "shared_memories.md",
        TEMPLATES_DIR / "master_roadmap.template.md": reports_dir / "master_roadmap.md",
    }
    for tpl, dst in mapping.items():
        if tpl.is_file() and not dst.exists():
            txt = tpl.read_text(encoding="utf-8")
            txt = txt.replace("{{CONTACT_NAME}}", contact_name).replace("{{CREATED_AT}}", now_str)
            dst.write_text(txt, encoding="utf-8")


def process_single_contact(contact_name, input_override=None):
    contact_dir = CONTACTS_DIR / contact_name
    raw_dir = Path(input_override) if input_override else (contact_dir / "raw")
    reports_dir = contact_dir / "reports"

    print(f"[*] 正在扫描 [{contact_name}] 的原始聊天数据: {raw_dir}")
    messages = load_messages(raw_dir)
    if not messages and contact_dir.exists() and not input_override:
        messages = load_messages(contact_dir)

    if not messages:
        print(f"[-] 未在 {raw_dir} 中找到有效聊天记录（支持 .json, .csv, .txt, .db）。")
        return False

    ensure_templates(contact_dir, contact_name)
    metrics = compute_metrics(messages)

    json_path = reports_dir / "quant_metrics.json"
    json_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[✓] 详细指标已保存: {json_path}")

    md_path = reports_dir / "quant_summary.md"
    md_path.write_text(format_summary_markdown(metrics, contact_name), encoding="utf-8")
    print(f"[✓] 量化体检报告已保存: {md_path}")

    db_path = DATA_DIR / "chat_metrics.db"
    save_to_sqlite(metrics, db_path, contact_name)
    print(f"[✓] 指标已同步存入 SQLite: {db_path} (contact={contact_name})")
    return True


def main():
    parser = argparse.ArgumentParser(description="Multi-Contact Chat Quantitative Slicer")
    parser.add_argument("--contact", "-c", help="指定要分析的女生备注名（对应 contacts/<备注名>/）")
    parser.add_argument("--input", "-i", help="可选：自定义原始聊天记录文件或目录路径")
    parser.add_argument("--all", action="store_true", help="批量分析 contacts/ 目录下的所有联系人")
    args = parser.parse_args()

    if args.all:
        if not CONTACTS_DIR.is_dir():
            print(f"[-] {CONTACTS_DIR} 目录不存在。")
            return 1
        subdirs = [d for d in sorted(CONTACTS_DIR.iterdir()) if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_")]
        for d in subdirs:
            process_single_contact(d.name)
        return 0

    if args.contact:
        ok = process_single_contact(args.contact, args.input)
        return 0 if ok else 1

    if args.input:
        in_path = Path(args.input).resolve()
        inferred_name = in_path.parent.name if in_path.name == "raw" else in_path.stem
        ok = process_single_contact(inferred_name, in_path)
        return 0 if ok else 1

    # 默认：如果只存在一个联系人则自动分析，否则列出所有联系人
    if CONTACTS_DIR.is_dir():
        subdirs = [d for d in sorted(CONTACTS_DIR.iterdir()) if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("_")]
        if len(subdirs) == 1:
            return 0 if process_single_contact(subdirs[0].name) else 1
        elif len(subdirs) > 1:
            print("[*] 检测到多个联系人目录，请使用 --contact \"备注名\" 或 --all：")
            for d in subdirs:
                print(f"  - {d.name}")
            return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
