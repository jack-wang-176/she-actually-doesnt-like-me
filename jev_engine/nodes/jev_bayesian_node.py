#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/jev_bayesian_node.py
[v2.0 核心深化] 博弈论信号甄别与贝叶斯动态 JEV 裁决器 (Bayesian JEV & Game Theory Node)

数学模型：
  1. 先验概率 P_0：由表层互动活跃度 (Surface Vitality) 转换而来，但受限于基础社交礼貌上限 (P_0 <= 0.55)。
  2. 贝叶斯对数几率后验更新 (Log-Odds Update)：
     Log-Odds_post = ln(P_0 / (1 - P_0)) + sum_k w_k^+ * I(CostlySignal_k) - sum_m w_m^- * I(PathologyFlag_m)
  3. 风险调整后夏普比率 (Relationship Sharpe Ratio)：
     Sharpe_i = (E[R_i] - R_base) / sigma_volatility
输出：state/jev_state.json
"""

import json
import math
from pathlib import Path
from typing import Dict, Any

from ..ingestors.feature_vectorizer import extract_window_metric_slices, compute_latency_volatility


POSITIVE_COSTLY_WEIGHTS = {
    "PUBLIC_CO_PRESENCE": 0.95,
    "EXCLUSIVE_TIME_YIELD": 0.85,
    "RECIPROCAL_INITIATION_AND_CARE": 0.78,
}

NEGATIVE_PATHOLOGY_WEIGHTS = {
    "BROAD_SOCIAL_WARMTH": 0.45,
    "PUBLIC_BOUNDARY_CUT": 0.98,
    "SHELF_MENTALITY_EXPOSED": 0.88,
    "ALIBI_CONFORMITY_DEVIATION": 0.52,
    "CORE_NEED_EVASION": 0.954,
}

BASELINE_MAINLINE_SHARPE = 1.60
BASELINE_RISK_FREE_RETURN = 32.0


class JEVBayesianNode:
    """贝叶斯动态 JEV 与博弈论收益裁决引擎"""

    def evaluate(self, quant: Dict[str, Any], defilter: Dict[str, Any]) -> Dict[str, Any]:
        surface_score = float(quant["indices"]["surface_vitality_score"])
        symmetry_score = float(quant["indices"]["symmetry_index"])
        defilter_mult = float(defilter["defilter_multiplier"])

        # 1. 先验概率 P_0：由表层活跃度映射，受基础社交礼貌上限 (<= 0.55) 约束
        p0 = min(0.55, max(0.08, round(surface_score * 0.00587, 3)))
        prior_prob_pct = round(p0 * 100.0, 1)
        log_odds_prior = math.log(p0 / (1.0 - p0))

        sig_game = defilter.get("signaling_game", {})
        costly_signals = sig_game.get("costly_signals", [])
        pathology_flags = sig_game.get("pathology_flags", [])

        pos_ll = 0.0
        for cs in costly_signals:
            code = cs.split(" ")[0].strip()
            pos_ll += POSITIVE_COSTLY_WEIGHTS.get(code, 0.50)

        neg_ll = 0.0
        for pf in pathology_flags:
            neg_ll += NEGATIVE_PATHOLOGY_WEIGHTS.get(pf, 0.50)

        # 若无显著病灶但互动频率偏低/对称度一般，根据对称度微调似然
        if not pathology_flags and not costly_signals:
            sym_delta = (symmetry_score - 65.0) * 0.015
            pos_ll += max(0.0, sym_delta)
            neg_ll += max(0.0, -sym_delta)

        log_odds_post = log_odds_prior + pos_ll - neg_ll
        post_prob = 1.0 / (1.0 + math.exp(-log_odds_post))
        post_prob_pct = round(max(0.5, min(96.0, post_prob * 100.0)), 1)
        squeezed_pct = round(max(0.0, prior_prob_pct - post_prob_pct), 1)

        # 2. 真实情感回报 V(Return) 与情绪内耗成本 C(Burn)
        peer_init_pct = float(quant["dynamics"]["peer_initiation_pct"])
        base_return = (peer_init_pct * 1.1) + (symmetry_score * 0.48)
        real_return_score = round(max(8.3, min(98.0, base_return * min(1.1, defilter_mult + 0.05))), 1)

        char_ratio = float(quant["volume"]["char_investment_ratio"])
        self_init_pct = float(quant["dynamics"]["self_initiation_pct"])
        pathology_cnt = int(defilter.get("pathology_count", 0))
        critical_cnt = sum(1 for p in defilter.get("detected_pathologies", []) if p.get("severity") == "CRITICAL")

        asymmetry_burn = max(0.0, (self_init_pct - 50.0) * 0.55) + max(0.0, (char_ratio - 1.0) * 14.5)
        pathology_burn = pathology_cnt * 6.28
        burn_cost_score = round(min(100.0, max(8.0, asymmetry_burn + pathology_burn)), 1)

        expected_gain = round((post_prob_pct / 100.0) * real_return_score, 1)
        net_jev_score = round(expected_gain - burn_cost_score, 1)
        roi_ratio = round(expected_gain / max(1.0, burn_cost_score), 2)

        # 3. 情绪波动率 sigma 与关系夏普比率 (Relationship Sharpe Ratio)
        window_slices = extract_window_metric_slices(quant, defilter.get("offline_signals", {}))
        sigma_vol = compute_latency_volatility(quant, window_slices)
        sharpe_ratio = round((net_jev_score - BASELINE_RISK_FREE_RETURN) / (sigma_vol * 14.95), 2)

        # 情绪最大回撤 (Max Emotional Drawdown, MDD %)
        densities = [w.get("density_ratio", 1.0) for w in window_slices] or [1.0]
        peak_d = max(densities)
        trough_d = min(densities)
        mdd_pct = round(min(99.0, max(5.0, ((peak_d - trough_d) / max(0.1, peak_d)) * 100.0)), 1)

        # 4. 终局裁决与推荐权重
        if post_prob_pct < 15.0 or net_jev_score < -15.0 or critical_cnt >= 1:
            verdict_code = "STOP_AND_PIVOT"
            verdict_label = "🛑 绝对不建议继续发展（STOP_AND_PIVOT / 立即止损封存）"
            continue_investing = False
            recommended_init_pct = 0.0
            recommended_weight_pct = 0.0
            action_directive = (
                f"贝叶斯后验发展率仅 {post_prob_pct}%（挤出 {squeezed_pct}% 滤镜水分），"
                f"净期望值 Net JEV 为 {net_jev_score}，夏普比率 {sharpe_ratio}。立即启动零主动熔断，推荐精力权重锁死为 0.0%。"
            )
        elif post_prob_pct < 55.0 or net_jev_score < 15.0 or sharpe_ratio < 0.0:
            verdict_code = "DOWNGRADE_OBSERVE"
            verdict_label = "⚠️ 暂不建议升级投入（DOWNGRADE_OBSERVE / 维持低成本观察）"
            continue_investing = False
            recommended_init_pct = 20.0
            recommended_weight_pct = 0.0 if sharpe_ratio < 0 else 5.0
            action_directive = (
                f"贝叶斯后验发展率为 {post_prob_pct}%，净期望值 Net JEV 为 {net_jev_score}（夏普比率 {sharpe_ratio}）。"
                "执行镜像配速法则，字数投入比严格控制在 0.8 ~ 1.2 之间，严禁自我感动式加码。"
            )
        else:
            verdict_code = "INVEST_STEADILY"
            verdict_label = "🟢 建议稳步推进发展（INVEST_STEADILY / 双向正反馈同频）"
            continue_investing = True
            recommended_init_pct = 50.0
            recommended_weight_pct = 30.0
            action_directive = (
                f"贝叶斯后验发展率达 {post_prob_pct}%，净期望值 Net JEV 为 +{net_jev_score}（夏普比率 +{sharpe_ratio}）。"
                "双方具备清晰的双向高昂信号（Costly Signals），建议稳步推进高价值线下共同经历。"
            )

        return {
            "schema_version": "2.0",
            "node_id": quant["node_id"],
            "node_hash": quant.get("node_hash", ""),
            "bayesian_update": {
                "prior_probability_pct": prior_prob_pct,
                "posterior_probability_pct": post_prob_pct,
                "illusion_squeezed_pct": squeezed_pct,
                "log_odds_prior": round(log_odds_prior, 3),
                "positive_log_likelihood": round(pos_ll, 3),
                "negative_log_likelihood": round(neg_ll, 3),
                "log_odds_posterior": round(log_odds_post, 3),
            },
            "metrics": {
                "prior_probability_pct": prior_prob_pct,
                "development_probability_pct": post_prob_pct,
                "illusion_squeezed_pct": squeezed_pct,
                "expected_return_score": real_return_score,
                "expected_gain": expected_gain,
                "energy_burn_cost": burn_cost_score,
                "net_jev_score": net_jev_score,
                "roi_ratio": roi_ratio,
                "volatility_sigma": sigma_vol,
                "sharpe_ratio": sharpe_ratio,
                "baseline_sharpe_ratio": BASELINE_MAINLINE_SHARPE,
                "max_emotional_drawdown_pct": mdd_pct,
                "recommended_energy_weight_pct": recommended_weight_pct,
            },
            "decision": {
                "verdict_code": verdict_code,
                "verdict_label": verdict_label,
                "continue_investing": continue_investing,
                "recommended_self_initiation_pct": recommended_init_pct,
                "recommended_energy_weight_pct": recommended_weight_pct,
                "action_directive": action_directive,
            },
        }


def run_jev_bayesian_node(state_dir: Path) -> Dict[str, Any]:
    state_dir = Path(state_dir)
    quant = json.loads((state_dir / "quant_state.json").read_text(encoding="utf-8"))
    defilter = json.loads((state_dir / "defilter_state.json").read_text(encoding="utf-8"))

    node = JEVBayesianNode()
    jev_state = node.evaluate(quant, defilter)
    (state_dir / "jev_state.json").write_text(
        json.dumps(jev_state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return jev_state
