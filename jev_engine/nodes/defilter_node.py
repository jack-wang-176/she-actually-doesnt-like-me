#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/defilter_node.py
[v2.0 深化] 五维去滤镜 + 博弈论信号甄别引擎 (Defilter & Signaling Game Node)
核心升级：
  1. 博弈论信号分类 (Signaling Game Separation)：
     - 廉价信号 (Cheap Talk, 零机会成本)：打字秒回、口头客套、不触及核心承诺的免责长文。
     - 高昂信号 (Costly Signal, 高机会成本)：公开场合自然并肩、排他性核心时间让渡、双向主动破冰与明确边界担当。
  2. 五大典型内耗病灶诊断与贝叶斯负向似然标志输出：
     - PUBLIC_BOUNDARY_CUT (公开场合刻意避嫌)
     - SHELF_MENTALITY_EXPOSED (买方货架心态言论)
     - CORE_NEED_EVASION (长文回避核心陪伴诉求)
     - BROAD_SOCIAL_WARMTH (广谱社交热情错觉)
     - ALIBI_CONFORMITY_DEVIATION (双面人设与合群托词)
输出：state/defilter_state.json
"""

import json
import re
from pathlib import Path
from typing import Dict, Any


DEFAULT_OFFLINE_SIGNALS = {
    "broad_social_warmth": False,
    "public_distance_cutting": False,
    "shelf_mentality_quote": False,
    "intermittent_utilitarian_contact": False,
    "alibi_clubbing_conformity": False,
    "unilateral_resource_given": False,
    "companionship_evasion": False,
    # v2.0 正向高昂信号 (Costly Signals)
    "public_co_presence_verified": False,
    "exclusive_weekend_time_yield": False,
    "proactive_emotional_support": False,
}


def _detect_online_anomalies(quant_state: dict, slice_shard: dict) -> dict:
    vol = quant_state["volume"]
    dyn = quant_state["dynamics"]
    lat = quant_state["latency"]["peer"]

    high_fast_reply_passive_init = (lat["fast_reply_pct"] >= 50.0 and dyn["self_initiation_pct"] >= 72.0)
    heavy_word_surplus = (vol["char_investment_ratio"] >= 1.75)

    utilitarian_reinit = False
    utilitarian_kw = re.compile(r"认识.*人|帮忙|资源|介绍一下|报价|多少钱|叔叔|学弟|学妹|兼职")
    for sb in dyn.get("silence_breaks", []):
        if sb.get("re_initiated_by") == "PEER":
            if sb.get("re_init_intent_code") == "UTILITARIAN_RESOURCE_REQUEST" or sb.get("utilitarian_score", 0.0) >= 0.7:
                utilitarian_reinit = True
            elif utilitarian_kw.search(sb.get("opening_preview", "")):
                utilitarian_reinit = True

    evasive_long_reply = False
    evasive_kw = re.compile(r"免责声明|暂时先不讨论|情绪跟生活分开|吃好.*睡好|暂时斩断|有需求.*再联系")
    need_kw = re.compile(r"陪我|陪伴|一个人|空虚|崩塌")
    for ex in slice_shard.get("long_exchanges", []):
        if ex.get("author") == "SELF":
            window_texts = " ".join(w.get("text", "") for w in ex.get("window", []))
            peer_texts = " ".join(w.get("text", "") for w in ex.get("window", []) if w.get("role") == "PEER")
            if need_kw.search(window_texts) and evasive_kw.search(peer_texts):
                evasive_long_reply = True

    return {
        "high_fast_reply_passive_init": high_fast_reply_passive_init,
        "heavy_word_surplus": heavy_word_surplus,
        "utilitarian_reinit": utilitarian_reinit,
        "evasive_long_reply": evasive_long_reply,
    }


def _evaluate_signaling_game(quant_state: dict, offline_signals: dict, online_anomalies: dict) -> Dict[str, Any]:
    """区分廉价信号 (Cheap Talk) 与高昂信号 (Costly Signals)"""
    lat = quant_state["latency"]["peer"]
    dyn = quant_state["dynamics"]
    vol = quant_state["volume"]
    sym = quant_state["indices"]["symmetry_index"]

    cheap_talk_signals = []
    if lat["fast_reply_pct"] >= 50.0 and dyn["self_initiation_pct"] >= 68.0:
        cheap_talk_signals.append("HIGH_SPEED_PASSIVE_REPLY (高秒回但零主动破冰：零机会成本的顺手礼貌)")
    if vol.get("peer_long_msgs", 0) >= 3 and (offline_signals.get("companionship_evasion") or online_anomalies["evasive_long_reply"]):
        cheap_talk_signals.append("DEFENSIVE_VERBOSE_DISCLAIMER (防御性说教长文：用免责鸡汤替代实质陪伴)")
    if quant_state["indices"]["surface_vitality_score"] >= 75.0 and sym <= 50.0:
        cheap_talk_signals.append("ASYMMETRIC_NIGHT_CHATTING (深夜高频闲聊但缺乏排他性边界确认)")

    costly_signals = []
    if offline_signals.get("public_co_presence_verified") or (sym >= 85.0 and not offline_signals.get("public_distance_cutting")):
        costly_signals.append("PUBLIC_CO_PRESENCE (公开场合自然并肩与社交圈身份坦诚)")
    if offline_signals.get("exclusive_weekend_time_yield") or (dyn["peer_initiation_pct"] >= 45.0 and sym >= 80.0):
        costly_signals.append("EXCLUSIVE_TIME_YIELD (排他性核心时间让渡与双向约见兑现)")
    if offline_signals.get("proactive_emotional_support") or (0.85 <= vol["char_investment_ratio"] <= 1.20 and dyn["peer_initiation_pct"] >= 45.0):
        costly_signals.append("RECIPROCAL_INITIATION_AND_CARE (高对称主动破冰与实质情绪承接)")

    pathology_flags = []
    if offline_signals.get("broad_social_warmth") or online_anomalies["high_fast_reply_passive_init"]:
        pathology_flags.append("BROAD_SOCIAL_WARMTH")
    if offline_signals.get("public_distance_cutting"):
        pathology_flags.append("PUBLIC_BOUNDARY_CUT")
    if offline_signals.get("shelf_mentality_quote") or offline_signals.get("intermittent_utilitarian_contact") or online_anomalies["utilitarian_reinit"]:
        pathology_flags.append("SHELF_MENTALITY_EXPOSED")
    if offline_signals.get("alibi_clubbing_conformity"):
        pathology_flags.append("ALIBI_CONFORMITY_DEVIATION")
    if offline_signals.get("companionship_evasion") or online_anomalies["evasive_long_reply"] or (offline_signals.get("unilateral_resource_given") and online_anomalies["heavy_word_surplus"]):
        pathology_flags.append("CORE_NEED_EVASION")

    return {
        "cheap_talk_signals": cheap_talk_signals,
        "costly_signals": costly_signals,
        "pathology_flags": pathology_flags,
        "cheap_talk_count": len(cheap_talk_signals),
        "costly_signal_count": len(costly_signals),
    }


def run_defilter_node(shards_dir: Path, state_dir: Path) -> dict:
    shards_dir = Path(shards_dir)
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)

    quant_state = json.loads((state_dir / "quant_state.json").read_text(encoding="utf-8"))
    slice_shard_path = shards_dir / "slice_shard.json"
    slice_shard = json.loads(slice_shard_path.read_text(encoding="utf-8")) if slice_shard_path.exists() else {}

    offline_path = state_dir / "offline_signals.json"
    if offline_path.exists():
        raw_sig = json.loads(offline_path.read_text(encoding="utf-8"))
        offline_signals = {k: bool(raw_sig.get(k, False)) for k in DEFAULT_OFFLINE_SIGNALS}
    else:
        offline_signals = dict(DEFAULT_OFFLINE_SIGNALS)
        offline_path.write_text(json.dumps(offline_signals, ensure_ascii=False, indent=2), encoding="utf-8")

    online_anomalies = _detect_online_anomalies(quant_state, slice_shard)
    signaling_game = _evaluate_signaling_game(quant_state, offline_signals, online_anomalies)

    pathologies = []
    discount_factors = []

    if "BROAD_SOCIAL_WARMTH" in signaling_game["pathology_flags"]:
        severity = "CRITICAL" if (offline_signals["broad_social_warmth"] and online_anomalies["high_fast_reply_passive_init"]) else "HIGH"
        discount_factors.append(0.55 if severity == "CRITICAL" else 0.72)
        pathologies.append({
            "code": "PATHOLOGY_01_BROAD_WARMTH",
            "flag": "BROAD_SOCIAL_WARMTH",
            "title": "「广谱社交热情」被误读为「排他性偏爱」",
            "severity": severity,
            "mechanism": (
                f"对方线上秒回率虽高（{quant_state['latency']['peer']['fast_reply_pct']}%），但你承担了 "
                f"{quant_state['dynamics']['self_initiation_pct']}% 的主动破冰。她的热情属于高外向/销售型人格的广谱社交货币（Cheap Talk），"
                "对其他同伴或社交圈同样熟络主动，并非针对你的专属高昂信号。"
            ),
            "anti_illusion_advice": "永远不要用『她回得快不快、聊得多不多』判断心意，要看她的热情是否具有排他性与稀缺性。",
        })

    if "PUBLIC_BOUNDARY_CUT" in signaling_game["pathology_flags"]:
        discount_factors.append(0.50)
        pathologies.append({
            "code": "PATHOLOGY_02_PUBLIC_CUTTING",
            "flag": "PUBLIC_BOUNDARY_CUT",
            "title": "私下热络与公开场合避嫌的「择偶防线管理」",
            "severity": "CRITICAL",
            "mechanism": (
                "私下独处或线上闲聊时互动密集，但只要有第三人在场（如公共空间、共同圈子场所），"
                "便刻意收敛亲密感、保持社交距离。本质上是在向周围潜在择偶池释放『我目前单身未绑定』的防御信号。"
            ),
            "anti_illusion_advice": "一个真正喜欢你的人，在公共场合藏不住眼神与身体的偏向；公开场合的刻意避嫌，就是最诚实的拒绝。",
        })

    if "SHELF_MENTALITY_EXPOSED" in signaling_game["pathology_flags"]:
        discount_factors.append(0.35)
        pathologies.append({
            "code": "PATHOLOGY_03_INTERMITTENT_SHELF",
            "flag": "SHELF_MENTALITY_EXPOSED",
            "title": "「买方货架心态」与间歇性强化（断联—复联拉扯闭环）",
            "severity": "CRITICAL",
            "mechanism": (
                "对方抱持『喜欢我的人很多、可以随便选』的买方傲慢，将追求者视为货架备选项。"
                "当你感到生理性下头并主动断联抽离时，对方又通过功利性求助（对接人脉/资源）或阶段性主动邀约给你释放微弱希望，"
                "形成心理学上最消耗心神的『间歇性强化 (Intermittent Reinforcement)』成瘾陷阱。"
            ),
            "anti_illusion_advice": "断联后对方若没有带着实质性的情感诚意回归，而是以求助、借资源或闲聊试探破冰，本质只是在清点鱼塘库存。",
        })

    if "ALIBI_CONFORMITY_DEVIATION" in signaling_game["pathology_flags"]:
        discount_factors.append(0.45)
        pathologies.append({
            "code": "PATHOLOGY_04_ALIBI_CONFORMITY",
            "flag": "ALIBI_CONFORMITY_DEVIATION",
            "title": "隐瞒真实行踪的双面人设与底层赛道背离",
            "severity": "HIGH",
            "mechanism": (
                "在你面前用乖巧无害的理由推脱邀约，实则与小团体去酒吧熬夜并因『聚会熬穿』放你鸽子，"
                "事后辩称『去酒吧是为了合群』。无论哪句是真话，『隐瞒行踪 + 靠酒吧熬夜合群』本身即证明你们的核心价值观与人生赛道彻底背离。"
            ),
            "anti_illusion_advice": "不必纠结她具体哪句撒了谎，当一个人需要对你伪装人设、且为了合群流连夜场时，你们早已不在同一个精神维度。",
        })

    if "CORE_NEED_EVASION" in signaling_game["pathology_flags"]:
        discount_factors.append(0.40)
        pathologies.append({
            "code": "PATHOLOGY_05_COMPANIONSHIP_EVASION",
            "flag": "CORE_NEED_EVASION",
            "title": "单向失血的「资源/情绪黑洞」与核心陪伴需求闪避",
            "severity": "CRITICAL",
            "mechanism": (
                f"我方字数投入是其 {quant_state['volume']['char_investment_ratio']} 倍并提供实质资源支持，"
                "但当你袒露脆弱、明确表达『需要陪伴』时，对方却用『免责声明』『把情绪与生活分开』『规律作息、暂时先不讨论』等零成本的"
                "理中客说教将你挡在门外——只享受你的资源与捧场红利，绝不承担任何排他性的情感陪伴责任。"
            ),
            "anti_illusion_advice": "看一个人爱不爱你，不要看她给你回了多长的『人生建议』，要看她在你最需要陪伴时是走向你，还是用大道理把门焊死。",
        })

    multiplier = 1.0
    for df in discount_factors:
        multiplier *= df
    if not discount_factors and quant_state["indices"]["symmetry_index"] >= 65.0:
        multiplier = 1.05
    multiplier = round(max(0.05, min(1.15, multiplier)), 3)

    surface_score = quant_state["indices"]["surface_vitality_score"]
    defiltered_exclusivity_score = round(surface_score * multiplier, 1)
    illusion_gap = round(max(0.0, surface_score - defiltered_exclusivity_score), 1)

    defilter_state = {
        "schema_version": "2.0",
        "node_id": quant_state["node_id"],
        "node_hash": quant_state["node_hash"],
        "surface_vitality_score": surface_score,
        "defilter_multiplier": multiplier,
        "defiltered_exclusivity_score": defiltered_exclusivity_score,
        "illusion_gap": illusion_gap,
        "signaling_game": signaling_game,
        "online_anomalies": online_anomalies,
        "offline_signals": offline_signals,
        "pathology_count": len(pathologies),
        "detected_pathologies": pathologies,
    }

    (state_dir / "defilter_state.json").write_text(
        json.dumps(defilter_state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return defilter_state
