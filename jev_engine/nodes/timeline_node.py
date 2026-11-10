#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/timeline_node.py
分布式节点：全周期时间线梳理、当前阶段聚焦与目前行动建议引擎 (TimelineEvolutionNode)
完全基于纯数学抽象状态向量 (monthly_vectors, silence_breaks, quant_state, defilter_state, jev_state) 推演：
  1. 明确给出「建不建议继续发展」的终局裁决 (Development Recommendation)
  2. 梳理全周期时间线演进阶段 (Chronological Phase Breakdown & Mermaid Timeline)
  3. 着重剖析「当前阶段态势 (Current Window Spotlight)」
  4. 给出针对当下的「目前可执行建议 (Immediate 24h / 7d / 30d Action Plan)」
输出：state/timeline_state.json
"""

import json
from pathlib import Path


def _classify_month_phase(ym: str, idx: int, total_months: int, vec: dict, prev_vec: dict, silence_events: list) -> dict:
    total = vec.get("total", 0)
    self_cnt = max(1, vec.get("self_cnt", 0))
    peer_cnt = max(1, vec.get("peer_cnt", 0))
    self_chars = vec.get("self_chars", 0)
    peer_chars = max(1, vec.get("peer_chars", 0))
    char_ratio = round(self_chars / peer_chars, 2)
    self_init_pct = vec.get("self_init_pct", round(self_cnt / max(1, total) * 100.0, 1))

    is_current = (idx == total_months - 1)
    prev_total = prev_vec.get("total", 0) if prev_vec else 0

    if total <= 30:
        phase_tag = "COOLING_OR_BREAK (断联/冰封低谷期)"
        diagnosis = "互动频次跌至冰点，关系处于实质性抽离、防线触发或冷处理阶段。"
    elif prev_total > 0 and prev_total <= 35 and total >= 150:
        phase_tag = "INTERMITTENT_REBOUND (断联后间歇性强化反弹期)"
        diagnosis = "经历低谷或断联后出现报复性高频复联，表层热度激增，极易掩盖未解决的底层边界问题。"
    elif idx == 0:
        phase_tag = "INITIAL_ICEBREAK (初始破冰与探索期)"
        diagnosis = f"建立初期交互基线（月消息 {total} 条，字数投入比 {char_ratio}:1）。"
    elif total >= 500 and char_ratio >= 1.3:
        phase_tag = "HIGH_HEAT_ASYMMETRY (高热假性亲密/单向透支期)"
        diagnosis = f"表面消息量爆发（{total} 条），但我方字数比达 {char_ratio}:1，存在显著的单向情绪供给。"
    elif total >= 400 and 0.8 <= char_ratio <= 1.25:
        phase_tag = "RECIPROCAL_WARMUP (双向高频共振升温期)"
        diagnosis = f"互动高频且投入高度对称（字数比 {char_ratio}:1），属于健康的双向情感升温。"
    else:
        phase_tag = "STEADY_OBSERVATION (常规维持/平台观察期)"
        diagnosis = f"维持日常社交频次（月消息 {total} 条，字数比 {char_ratio}:1）。"

    if is_current:
        phase_tag = f"🎯 CURRENT_WINDOW [{phase_tag.split(' ')[0]}] (当前核心窗口)"

    return {
        "period": ym,
        "is_current_window": is_current,
        "total_messages": total,
        "self_messages": vec.get("self_cnt", 0),
        "peer_messages": vec.get("peer_cnt", 0),
        "char_investment_ratio": char_ratio,
        "self_initiation_pct": self_init_pct,
        "phase_tag": phase_tag,
        "phase_diagnosis": diagnosis,
    }


def run_timeline_node(state_dir: Path, personal_mainline: str = "核心系统架构与硬核技术研发") -> dict:
    state_dir = Path(state_dir)
    quant = json.loads((state_dir / "quant_state.json").read_text(encoding="utf-8"))
    defilter = json.loads((state_dir / "defilter_state.json").read_text(encoding="utf-8"))
    jev = json.loads((state_dir / "jev_state.json").read_text(encoding="utf-8"))

    monthly = quant.get("monthly_vectors", {})
    sorted_months = sorted(monthly.keys())
    silence_breaks = quant.get("dynamics", {}).get("silence_breaks", [])

    phases = []
    prev_vec = None
    for idx, ym in enumerate(sorted_months):
        vec = monthly[ym]
        phase_info = _classify_month_phase(ym, idx, len(sorted_months), vec, prev_vec, silence_breaks)
        phases.append(phase_info)
        prev_vec = vec

    # 如果 monthly_vectors 为空，根据整体统计自动生成合成当前阶段
    if not phases:
        vol = quant["volume"]
        dyn = quant["dynamics"]
        phases.append({
            "period": f"{quant['span']['start_time'][:7]} ~ {quant['span']['end_time'][:7]}",
            "is_current_window": True,
            "total_messages": vol["total_messages"],
            "self_messages": vol["self_messages"],
            "peer_messages": vol["peer_messages"],
            "char_investment_ratio": vol["char_investment_ratio"],
            "self_initiation_pct": dyn["self_initiation_pct"],
            "phase_tag": "🎯 CURRENT_WINDOW (当前综合统计窗口)",
            "phase_diagnosis": f"周期内累计 {vol['total_messages']} 条互动，我方主动破冰率 {dyn['self_initiation_pct']}%，字数比 {vol['char_investment_ratio']}:1。",
        })

    current_phase = phases[-1]
    prev_phase = phases[-2] if len(phases) >= 2 else None

    verdict_code = jev["decision"]["verdict_code"]
    dev_prob = jev["metrics"]["development_probability_pct"]
    net_jev = jev["metrics"]["net_jev_score"]
    illusion_gap = defilter["illusion_gap"]
    pathology_cnt = defilter["pathology_count"]

    # 1. 明确裁决：建不建议发展？(Explicit Development Recommendation)
    if verdict_code == "STOP_AND_PIVOT":
        recommend_develop = False
        recommendation_banner = "❌ 坚决不建议发展（立即止损封存）"
        recommendation_reason = (
            f"去滤镜后正向发展概率仅 {dev_prob}%，净期望值 Net JEV 为 {net_jev}（滤镜水分高达 {illusion_gap} 分，"
            f"触发 {pathology_cnt} 项高危病灶）。继续投入只会加剧单向失血与情绪内耗。"
        )
    elif verdict_code == "DOWNGRADE_OBSERVE":
        recommend_develop = False
        recommendation_banner = "⚠️ 暂不建议单向发展（降级观察，等待对方实质破冰）"
        recommendation_reason = (
            f"当前去滤镜发展概率为 {dev_prob}%（Net JEV = {net_jev}），尚未形成稳定的双向奔赴闭环，"
            "盲目追加投入容易掉入友谊安全区或被动消耗。"
        )
    else:
        recommend_develop = True
        recommendation_banner = "✅ 建议稳步发展（双向同频，具备高正向回报）"
        recommendation_reason = (
            f"去滤镜后发展概率达 {dev_prob}%，净期望值 Net JEV 为 +{net_jev}，线上线下言行一致且互动高度对称，"
            "属于值得投入精力的优质双向关系。"
        )

    # 2. 着重剖析当前态势 (Current Window Spotlight)
    vol_trend_str = "持平"
    if prev_phase:
        diff_msgs = current_phase["total_messages"] - prev_phase["total_messages"]
        vol_trend_str = f"较上一阶段变化 {diff_msgs:+d} 条（上期 {prev_phase['total_messages']} 条 -> 当前 {current_phase['total_messages']} 条）"

    if verdict_code == "STOP_AND_PIVOT":
        current_spotlight = {
            "window_period": current_phase["period"],
            "volume_trend": vol_trend_str,
            "current_char_ratio": f"{current_phase['char_investment_ratio']} : 1",
            "current_self_init_pct": f"{current_phase['self_initiation_pct']}%",
            "core_reality_assessment": (
                f"【当前窗口（{current_phase['period']}）深度透视】：虽然经历前期高热反弹后近期仍有互动，"
                f"但当前窗口我方字数投入比高达 {current_phase['char_investment_ratio']}:1，主动破冰占比 {current_phase['self_initiation_pct']}%。"
                "更重要的是，当前阶段对方已暴露出『回避核心陪伴诉求』『用社交借口掩饰真实夜场行踪』『只给零成本说教而不承担情感责任』的终局底牌。"
                "这意味着关系已彻底触及『伪亲密天花板』——继续聊下去不会带来任何实质性的关系跃迁，只会让你在推拉与自我怀疑中持续失血。"
            ),
        }
        immediate_advice = {
            "focus_theme": f"果断斩断沉没成本，将 100% 能量切回「{personal_mainline}」",
            "now_24h": "【当下 24 小时】：立即停止主动发起任何新话题；若对方发来无关痛痒的日常或表情包，保持礼貌简短（不超过 5 个字）或延迟数小时后客套收尾，绝不借机展开闲聊。",
            "next_7d": "【未来 7 天（戒断反扑期）】：将我方主动破冰率严格锁定为 0%。警惕对方因察觉你冷淡而触发的『间歇性试探』或『功利性求助』——遇到求助一律公事公办或温和婉拒，不提供无偿资源，不写任何长文。",
            "next_30d": f"【未来 30 天（主体性重建期）】：彻底将该节点归档封存，把原本消耗在深夜等待与情绪内耗中的时间，全部转化为「{personal_mainline}」的工程产出与硬核里程碑。",
        }
    elif verdict_code == "DOWNGRADE_OBSERVE":
        current_spotlight = {
            "window_period": current_phase["period"],
            "volume_trend": vol_trend_str,
            "current_char_ratio": f"{current_phase['char_investment_ratio']} : 1",
            "current_self_init_pct": f"{current_phase['self_initiation_pct']}%",
            "core_reality_assessment": (
                f"【当前窗口（{current_phase['period']}）深度透视】：目前互动处于低烈度安全区（月消息 {current_phase['total_messages']} 条，"
                f"我方字数比 {current_phase['char_investment_ratio']}:1）。虽无恶性养鱼或欺瞒信号，但对方的主动性与情绪卷入度尚浅，"
                "当前阶段若由我方单方面高频猛攻，极易打破平衡导致对方开启回避防御。"
            ),
        }
        immediate_advice = {
            "focus_theme": "回收超额需求感，用『镜像对等原则』测试对方真实意愿",
            "now_24h": "【当下 24 小时】：匹配对方的回复字数与时延节奏（字数比严格控制在 1:1 以内），不连发消息、不追问。",
            "next_7d": "【未来 7 天（冷却测试期）】：主动破冰频次降至每周不超过 1-2 次，留出空白窗口观察对方是否会主动找话题破冰。",
            "next_30d": f"【未来 30 天（筛选裁决期）】：保持 80% 精力聚焦于「{personal_mainline}」；若对方在 30 天内展现正向主动并愿意配合轻量级线下见面，再逐步上调互动权重，否则自然淡出。",
        }
    else:
        current_spotlight = {
            "window_period": current_phase["period"],
            "volume_trend": vol_trend_str,
            "current_char_ratio": f"{current_phase['char_investment_ratio']} : 1",
            "current_self_init_pct": f"{current_phase['self_initiation_pct']}%",
            "core_reality_assessment": (
                f"【当前窗口（{current_phase['period']}）深度透视】：当前处于高健康度的双向共振期（月互动 {current_phase['total_messages']} 条，"
                f"字数投入比 {current_phase['char_investment_ratio']}:1，我方破冰占比 {current_phase['self_initiation_pct']}%）。"
                "双方在主动性、情绪承接与线下言行一致性上均表现优异，当前正是从线上高默契转化为线下实质升温的黄金窗口。"
            ),
        }
        immediate_advice = {
            "focus_theme": "把握当前双向高热窗口，从线上共鸣自然升级至线下排他性约会",
            "now_24h": "【当下 24 小时】：在日常高能量对话的高潮处顺势植入一个具体、低防备的线下共同体验锚点（如共同感兴趣的展览、特色餐厅或户外活动）。",
            "next_7d": "【未来 7 天（线下兑现期）】：完成一次高质量一对一线下约会，观察其在公共场合与你并肩同行时的自然度与亲密边界反应。",
            "next_30d": f"【未来 30 天（关系确认期）】：在稳固「{personal_mainline}」主线（60% 精力）的同时，通过 2-3 次连续的正向线下互动完成关系自然升级。",
        }

    timeline_state = {
        "schema_version": "1.0",
        "node_id": quant["node_id"],
        "node_hash": quant["node_hash"],
        "development_recommendation": {
            "recommend_develop": recommend_develop,
            "banner": recommendation_banner,
            "reason": recommendation_reason,
        },
        "phases": phases,
        "current_spotlight": current_spotlight,
        "immediate_advice": immediate_advice,
    }

    (state_dir / "timeline_state.json").write_text(json.dumps(timeline_state, ensure_ascii=False, indent=2), encoding="utf-8")
    return timeline_state
