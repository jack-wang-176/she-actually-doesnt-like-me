#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/portfolio_node.py
[v2.0 深化] 引入夏普比率 (Relationship Sharpe Ratio) 与情绪最大回撤 (Max Emotional Drawdown, MDD)
的多人风险平价精力配置引擎 (PortfolioAllocatorNode)。

核心公式：
  Sharpe_i = (E[R_i] - R_base) / sigma_volatility_i
  - 凡是夏普比率为负 (Sharpe_i < 0) 或触发 STOP_AND_PIVOT 的节点，精力配置权重自动砍为 0.0%。
  - 直观量化将内耗精力重路由至个人硬核研发主线 (SELF_CORE_MAINLINE) 或正向同频节点的确定性增益。
"""

import json
from datetime import datetime
from pathlib import Path


SELF_MAINLINE_BENCHMARK = {
    "node_id": "SELF_CORE_MAINLINE (个人硬核成长/研发主线)",
    "is_self_benchmark": True,
    "surface_vitality_score": 90.0,
    "defilter_multiplier": 1.0,
    "defiltered_exclusivity_score": 90.0,
    "prior_probability_pct": 95.0,
    "development_probability_pct": 95.0,
    "illusion_squeezed_pct": 0.0,
    "expected_return_score": 96.0,
    "energy_burn_cost": 10.0,
    "net_jev_score": 81.2,
    "roi_ratio": 9.12,
    "volatility_sigma": 0.25,
    "sharpe_ratio": 1.60,
    "max_emotional_drawdown_pct": 3.5,
    "verdict_code": "CORE_ANCHOR",
    "verdict_label": "🚀 确定性基石 · 核心精力配置锚点",
    "pathology_count": 0,
}


def run_portfolio_node(state_dirs: list, output_dir: Path, personal_mainline_name: str = None) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    candidates = []
    for s_dir in state_dirs:
        s_dir = Path(s_dir)
        q_path = s_dir / "quant_state.json"
        d_path = s_dir / "defilter_state.json"
        j_path = s_dir / "jev_state.json"
        t_path = s_dir / "timeline_state.json"
        if not (q_path.exists() and d_path.exists() and j_path.exists()):
            continue

        q = json.loads(q_path.read_text(encoding="utf-8"))
        d = json.loads(d_path.read_text(encoding="utf-8"))
        j = json.loads(j_path.read_text(encoding="utf-8"))
        t = json.loads(t_path.read_text(encoding="utf-8")) if t_path.exists() else {}

        m = j["metrics"]
        candidates.append({
            "node_id": q["node_id"],
            "node_hash": q.get("node_hash", ""),
            "is_self_benchmark": False,
            "current_fsm_state": t.get("current_fsm_state", "UNKNOWN"),
            "surface_vitality_score": d["surface_vitality_score"],
            "defilter_multiplier": d["defilter_multiplier"],
            "defiltered_exclusivity_score": d["defiltered_exclusivity_score"],
            "illusion_gap": d["illusion_gap"],
            "prior_probability_pct": m.get("prior_probability_pct", m["development_probability_pct"]),
            "development_probability_pct": m["development_probability_pct"],
            "illusion_squeezed_pct": m.get("illusion_squeezed_pct", 0.0),
            "expected_return_score": m["expected_return_score"],
            "energy_burn_cost": m["energy_burn_cost"],
            "net_jev_score": m["net_jev_score"],
            "roi_ratio": m["roi_ratio"],
            "volatility_sigma": m.get("volatility_sigma", 1.0),
            "sharpe_ratio": m.get("sharpe_ratio", 0.0),
            "max_emotional_drawdown_pct": m.get("max_emotional_drawdown_pct", 20.0),
            "verdict_code": j["decision"]["verdict_code"],
            "verdict_label": j["decision"]["verdict_label"],
            "continue_investing": j["decision"]["continue_investing"],
            "pathology_count": d["pathology_count"],
            "pathology_titles": [p["title"] for p in d.get("detected_pathologies", [])],
        })

    benchmark = dict(SELF_MAINLINE_BENCHMARK)
    if personal_mainline_name:
        benchmark["node_id"] = f"SELF_CORE_MAINLINE ({personal_mainline_name})"

    # 风险平价与夏普比率截断规则：
    # 凡是 sharpe_ratio < 0 或 net_jev_score <= 0 或 STOP_AND_PIVOT 的节点，权重强制砍为 0.0%
    positive_sharpe_candidates = [
        c for c in candidates
        if c["sharpe_ratio"] > 0 and c["net_jev_score"] > 0 and c["verdict_code"] != "STOP_AND_PIVOT"
    ]
    total_positive_sharpe = sum(c["sharpe_ratio"] for c in positive_sharpe_candidates)

    if not positive_sharpe_candidates:
        benchmark["recommended_energy_pct"] = 100.0
        for c in candidates:
            c["recommended_energy_pct"] = 0.0
    else:
        social_pool_cap = min(35.0, total_positive_sharpe * 18.0)
        benchmark["recommended_energy_pct"] = round(100.0 - social_pool_cap, 1)
        for c in candidates:
            if c in positive_sharpe_candidates:
                c["recommended_energy_pct"] = round(social_pool_cap * (c["sharpe_ratio"] / total_positive_sharpe), 1)
            else:
                c["recommended_energy_pct"] = 0.0

    sorted_candidates = sorted(candidates, key=lambda x: (x["sharpe_ratio"], x["net_jev_score"]), reverse=True)

    portfolio_summary = {
        "schema_version": "2.0",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "baseline_sharpe_ratio": benchmark["sharpe_ratio"],
        "total_contacts_evaluated": len(candidates),
        "positive_return_contacts": [c["node_id"] for c in positive_sharpe_candidates],
        "stop_loss_contacts": [c["node_id"] for c in candidates if c["recommended_energy_pct"] == 0.0],
        "allocation_matrix": [benchmark] + sorted_candidates,
    }

    (output_dir / "portfolio_matrix.json").write_text(
        json.dumps(portfolio_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return portfolio_summary
