#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/jev_node.py
分布式节点 3：JEV (Joint Expected Value) 感情发展可能性与精力投入裁决节点
仿照量化金融/博弈论中的 EV (Expected Value) 期望值评估范式，计算：
  - 感情发展可能性 P(Develop) ∈ [0%, 100%]
  - 真实正向回报值 V(Return) ∈ [0, 100]
  - 精力与情绪损耗成本 C(Burn) ∈ [0, 100]
  - 净联合期望值 Net JEV = (P(Develop) * V(Return)) - C(Burn)
  - 明确精力投入裁决 (Explicit Verdict)：
      * STOP_AND_PIVOT    (🛑 立即止损 · 停止投入精力，100% 转回个人硬核主线)
      * DOWNGRADE_OBSERVE (⚠️ 降级观察 · 停止单向输出与资源供给，仅做对等回应)
      * INVEST_STEADILY   (🟢 值得投入 · 双向奔赴信号健康，稳步推进线下关系)
输出：state/jev_state.json
"""

import json
from pathlib import Path


def run_jev_node(state_dir: Path) -> dict:
    state_dir = Path(state_dir)
    quant = json.loads((state_dir / "quant_state.json").read_text(encoding="utf-8"))
    defilter = json.loads((state_dir / "defilter_state.json").read_text(encoding="utf-8"))

    surface_score = quant["indices"]["surface_vitality_score"]
    symmetry_score = quant["indices"]["symmetry_index"]
    defilter_mult = defilter["defilter_multiplier"]
    pathology_cnt = defilter["pathology_count"]
    critical_cnt = sum(1 for p in defilter["detected_pathologies"] if p["severity"] == "CRITICAL")

    # 1. 感情发展可能性 P(Develop) (0% ~ 100%)
    raw_prob = (0.55 * surface_score + 0.45 * symmetry_score) * defilter_mult
    if critical_cnt >= 2:
        raw_prob = min(raw_prob, 8.0)
    elif critical_cnt == 1:
        raw_prob = min(raw_prob, 22.0)
    dev_prob_pct = round(max(1.0, min(95.0, raw_prob)), 1)

    # 2. 真实情感与成长回报值 V(Return) (0 ~ 100)
    # 考量对方主动破冰占比、双向对称性、以及是否真正承接陪伴需求
    peer_init_pct = quant["dynamics"]["peer_initiation_pct"]
    base_return = (peer_init_pct * 1.1) + (symmetry_score * 0.45)
    real_return_score = round(max(5.0, min(100.0, base_return * defilter_mult)), 1)

    # 3. 精力与情绪损耗成本 C(Burn) (0 ~ 100)
    # 单向字数比越高、主动破冰越失衡、触发的间歇性强化/病灶越多，损耗成本越剧烈
    char_ratio = quant["volume"]["char_investment_ratio"]
    self_init_pct = quant["dynamics"]["self_initiation_pct"]
    asymmetry_burn = max(0.0, (self_init_pct - 50.0) * 0.7) + max(0.0, (char_ratio - 1.0) * 18.0)
    pathology_burn = pathology_cnt * 14.0 + critical_cnt * 8.0
    burn_cost_score = round(min(100.0, max(10.0, asymmetry_burn + pathology_burn)), 1)

    # 4. 净联合期望值 Net JEV (-100 ~ +100)
    expected_gain = round((dev_prob_pct / 100.0) * real_return_score, 1)
    net_jev_score = round(expected_gain - burn_cost_score, 1)
    roi_ratio = round(expected_gain / max(1.0, burn_cost_score), 2)

    # 5. 明确精力投入裁决 (Explicit Energy Investment Verdict)
    if dev_prob_pct < 25.0 or net_jev_score < -15.0 or critical_cnt >= 1:
        verdict_code = "STOP_AND_PIVOT"
        verdict_label = "🛑 立即止损 · 停止投入精力（转向个人硬核主线）"
        continue_investing = False
        recommended_init_pct = 0.0
        action_directive = (
            "明确结论：【不需要、也不应该继续投入任何精力】。这段关系去滤镜后的正向发展概率仅为 "
            f"{dev_prob_pct}%，净期望值 JEV 为 {net_jev_score}（严重负收益）。"
            "请立即将主动发起话题率降至 0%，停止提供任何无偿资源与长文情绪价值，将 100% 的时间与多巴胺收回个人硬核技术与成长主线。"
        )
    elif dev_prob_pct < 55.0 or net_jev_score < 10.0:
        verdict_code = "DOWNGRADE_OBSERVE"
        verdict_label = "⚠️ 降级观察 · 停止单向输出（等待对方实质投入）"
        continue_investing = False
        recommended_init_pct = 20.0
        action_directive = (
            "明确结论：【暂停单向追加精力，转入低成本观察期】。当前去滤镜发展概率为 "
            f"{dev_prob_pct}%，净期望值 JEV 为 {net_jev_score}。"
            "建议将字数比严格控制在 1:1 以内，不再主动发长文或单向迁就，观察对方是否愿意主动破冰并兑现线下排他性陪伴。"
        )
    else:
        verdict_code = "INVEST_STEADILY"
        verdict_label = "🟢 值得投入 · 稳步推进线下关系"
        continue_investing = True
        recommended_init_pct = 50.0
        action_directive = (
            "明确结论：【值得继续投入精力】。当前去滤镜发展概率达 "
            f"{dev_prob_pct}%，净期望值 JEV 为 +{net_jev_score}（正向回报周期）。"
            "双方线上线下言行一致、互动对称，建议通过共同兴趣自然转入高频线下约会。"
        )

    jev_state = {
        "schema_version": "1.0",
        "node_id": quant["node_id"],
        "node_hash": quant["node_hash"],
        "metrics": {
            "development_probability_pct": dev_prob_pct,
            "expected_return_score": real_return_score,
            "expected_gain": expected_gain,
            "energy_burn_cost": burn_cost_score,
            "net_jev_score": net_jev_score,
            "roi_ratio": roi_ratio,
        },
        "decision": {
            "verdict_code": verdict_code,
            "verdict_label": verdict_label,
            "continue_investing": continue_investing,
            "recommended_self_initiation_pct": recommended_init_pct,
            "action_directive": action_directive,
        },
    }

    (state_dir / "jev_state.json").write_text(json.dumps(jev_state, ensure_ascii=False, indent=2), encoding="utf-8")
    return jev_state
