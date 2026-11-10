#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/ingestors/multi_platform_sync.py
she-dont-love-me: 多平台聊天记录分布式汇总、手动关系连接 (Identity Binding) 与实时增量重排引擎

解决核心痛点：
  现实中同一个人的互动往往分布在多个社交平台（WeChat / QQ / Telegram / iMessage / 小红书等），
  且聊天记录存在分批导出、实时增量追加、跨平台时间戳乱序等问题。

三层分布式抽象架构：
  1. 单平台总体聊天记录汇总层 (Platform Pool Layer):
     路径: `<workspace>/platforms/<platform>/<account_id>/pool.json`
     职责: 负责单一平台内同一账号历史记录与实时增量消息的幂等去重、水位线 (watermark_ts) 维护与汇总。
  2. 上层跨平台关系连接层 (Manual Identity Binding Layer):
     路径: `<workspace>/identity_links.json`
     职责: 由用户手动指定“哪几个不同平台的账号属于现实中的同一个人 (person_node_id)”，不做黑盒盲猜。
  3. 跨平台实时更新与最终时间线重排层 (Global Timeline Reordering Layer):
     职责: 根据 `identity_links.json` 拉取该人名下所有绑定平台的增量/全量消息流，
     执行多路归并排序 (Multi-way Merge-Sort with Causal Tie-Breaking)，消除乱序到达，
     缝合跨平台连续会话（如微信聊一半转到 QQ 发文件），最终输出标准分布式切片 `shards/`。
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from .shard_builder import load_raw_records, build_distributed_shards


def _compute_msg_uid(platform: str, account_id: str, ts: int, is_self: bool, content: str) -> str:
    """生成幂等消息唯一指纹，防止实时更新或重复导入时产生脏数据"""
    raw = f"{platform}|{account_id}|{ts}|{'1' if is_self else '0'}|{content.strip()}"
    return hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()[:20]


class PlatformAggregator:
    """第一层：单平台总体聊天记录汇总器（支持全量导入与实时增量追加）"""

    def __init__(self, platforms_root: Path):
        self.platforms_root = Path(platforms_root)

    def pool_path(self, platform: str, account_id: str) -> Path:
        safe_plat = platform.strip().lower()
        safe_acc = account_id.strip()
        return self.platforms_root / safe_plat / safe_acc / "pool.json"

    def ingest_to_platform_pool(self, platform: str, account_id: str, raw_source: Path) -> dict:
        """
        将单平台原始文件或增量消息合并入该平台的总体汇总池 `pool.json`。
        自动按 `msg_uid` 幂等去重并按时间戳局部排序，更新 `watermark_ts`。
        """
        incoming = load_raw_records(Path(raw_source))
        p_path = self.pool_path(platform, account_id)
        p_path.parent.mkdir(parents=True, exist_ok=True)

        if p_path.exists():
            pool_data = json.loads(p_path.read_text(encoding="utf-8"))
        else:
            pool_data = {
                "schema_version": "1.0",
                "platform": platform.strip().lower(),
                "account_id": account_id.strip(),
                "watermark_ts": 0,
                "total_messages": 0,
                "last_updated_at": None,
                "messages": [],
            }

        existing_map = {m["msg_uid"]: m for m in pool_data.get("messages", [])}
        added_count = 0
        duplicate_count = 0

        for r in incoming:
            uid = _compute_msg_uid(platform, account_id, r["ts"], r["is_self"], r["content"])
            if uid not in existing_map:
                existing_map[uid] = {
                    "msg_uid": uid,
                    "platform": platform.strip().lower(),
                    "account_id": account_id.strip(),
                    "ts": r["ts"],
                    "time": r["dt"].strftime("%Y-%m-%d %H:%M:%S"),
                    "is_self": r["is_self"],
                    "content": r["content"],
                    "char_len": r["char_len"],
                }
                added_count += 1
            else:
                duplicate_count += 1

        # 单平台内部时间线重排
        merged_list = sorted(existing_map.values(), key=lambda x: (x["ts"], x["msg_uid"]))
        watermark = merged_list[-1]["ts"] if merged_list else pool_data.get("watermark_ts", 0)

        pool_data.update({
            "watermark_ts": watermark,
            "total_messages": len(merged_list),
            "last_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_delta": {
                "added": added_count,
                "duplicates_skipped": duplicate_count,
            },
            "messages": merged_list,
        })

        p_path.write_text(json.dumps(pool_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "platform": platform,
            "account_id": account_id,
            "pool_path": str(p_path),
            "added": added_count,
            "duplicates_skipped": duplicate_count,
            "total_in_pool": len(merged_list),
            "watermark_ts": watermark,
        }


class IdentityLinkRegistry:
    """第二层：上层跨平台关系连接器（由用户手动指定跨平台账号归属）"""

    def __init__(self, registry_path: Path):
        self.registry_path = Path(registry_path)

    def load_registry(self) -> dict:
        if self.registry_path.exists():
            return json.loads(self.registry_path.read_text(encoding="utf-8"))
        return {
            "schema_version": "1.0",
            "description": "手动指定的跨平台联系人身份映射表 (Person Node <-> Multi-Platform Accounts)",
            "bindings": {},
        }

    def save_registry(self, data: dict):
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def bind_account(self, node_id: str, platform: str, account_id: str, alias_note: str = "") -> dict:
        reg = self.load_registry()
        bindings = reg.setdefault("bindings", {})
        node_entry = bindings.setdefault(node_id, {
            "node_id": node_id,
            "updated_at": None,
            "linked_accounts": [],
        })

        plat_norm = platform.strip().lower()
        acc_norm = account_id.strip()

        already = any(
            a["platform"] == plat_norm and a["account_id"] == acc_norm
            for a in node_entry["linked_accounts"]
        )
        if not already:
            node_entry["linked_accounts"].append({
                "platform": plat_norm,
                "account_id": acc_norm,
                "alias_note": alias_note,
                "linked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        node_entry["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_registry(reg)
        return node_entry

    def get_linked_accounts(self, node_id: str) -> list:
        reg = self.load_registry()
        return reg.get("bindings", {}).get(node_id, {}).get("linked_accounts", [])


class TimelineReconciler:
    """
    第三层：跨平台增量汇聚与最终聊天记录全局重排器 (Global Timeline Reordering)
    - 从 `IdentityLinkRegistry` 获取某个 `node_id` 绑定的所有 `(platform, account_id)`；
    - 读取各平台的汇总池 `pool.json`；
    - 执行多路归并排序 (Multi-way Merge-Sort)，对乱序追加或跨平台并发消息进行全局重排；
    - 输出重排后的统一消息流 `shards/unified_timeline_shard.json` 并刷新下游分布式 `shards/`。
    """

    def __init__(self, platforms_root: Path, registry_path: Path, nodes_root: Path):
        self.aggregator = PlatformAggregator(platforms_root)
        self.registry = IdentityLinkRegistry(registry_path)
        self.nodes_root = Path(nodes_root)

    def reconcile_node_timeline(self, node_id: str, gap_threshold: int = 7200) -> dict:
        linked = self.registry.get_linked_accounts(node_id)
        if not linked:
            raise ValueError(f"节点 [{node_id}] 尚未在 identity_links.json 中绑定任何平台账号。")

        unified_pool = {}
        platform_breakdown = {}
        platform_watermarks = {}

        for item in linked:
            plat = item["platform"]
            acc = item["account_id"]
            p_path = self.aggregator.pool_path(plat, acc)
            if not p_path.exists():
                continue
            pool_data = json.loads(p_path.read_text(encoding="utf-8"))
            msgs = pool_data.get("messages", [])
            platform_breakdown[f"{plat}:{acc}"] = len(msgs)
            platform_watermarks[f"{plat}:{acc}"] = pool_data.get("watermark_ts", 0)
            for m in msgs:
                unified_pool[m["msg_uid"]] = m

        if not unified_pool:
            raise ValueError(f"节点 [{node_id}] 绑定的平台池中暂无任何聊天记录。")

        reordered_messages = sorted(
            unified_pool.values(),
            key=lambda x: (x["ts"], x["platform"], x["msg_uid"]),
        )

        cross_platform_switches = 0
        for i in range(1, len(reordered_messages)):
            if reordered_messages[i]["platform"] != reordered_messages[i - 1]["platform"]:
                if (reordered_messages[i]["ts"] - reordered_messages[i - 1]["ts"]) <= gap_threshold:
                    cross_platform_switches += 1

        node_dir = self.nodes_root / node_id
        shards_dir = node_dir / "shards"
        shards_dir.mkdir(parents=True, exist_ok=True)

        unified_shard_path = shards_dir / "unified_timeline_shard.json"
        unified_payload = {
            "schema_version": "1.0",
            "node_id": node_id,
            "reconciled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "linked_accounts": linked,
            "platform_breakdown": platform_breakdown,
            "platform_watermarks": platform_watermarks,
            "cross_platform_switches_in_session": cross_platform_switches,
            "total_reordered_messages": len(reordered_messages),
            "messages": [
                {
                    "timestamp": m["ts"],
                    "time": m["time"],
                    "isSend": 1 if m["is_self"] else 0,
                    "platform": m["platform"],
                    "account_id": m["account_id"],
                    "content": m["content"],
                }
                for m in reordered_messages
            ],
        }
        unified_shard_path.write_text(json.dumps(unified_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        build_distributed_shards(node_id, unified_shard_path, shards_dir, gap_threshold=gap_threshold)

        meta_path = shards_dir / "meta_shard.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["multi_platform"] = {
                "linked_accounts_count": len(linked),
                "platform_breakdown": platform_breakdown,
                "platform_watermarks": platform_watermarks,
                "cross_platform_switches": cross_platform_switches,
            }
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "node_id": node_id,
            "total_reordered_messages": len(reordered_messages),
            "platform_breakdown": platform_breakdown,
            "cross_platform_switches": cross_platform_switches,
            "shards_dir": str(shards_dir),
        }
