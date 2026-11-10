#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/portfolio_node.py
分布式节点 5：多人横向评估与精力投资组合分配引擎 (PortfolioAllocatorNode)
核心设计：
  - 采用纯分布式抽象聚合：绝不读取任何联系人的原始聊天记录，仅收集各自治节点的
    `quant_state.json`、`defilter_state.json` 与 `jev_state.json`。
  - 引入「个人硬核发展主线 (SELF_CORE_MAINLINE)」作为基准锚点资产（默认 P=95%, JEV=+82.0），
    回答核心问题：『我应该把宝贵的精力投给哪个人？从哪些人身上能获得正向回报？还是应该全仓个人主线？』
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
    "development_probability_pct": 95.0,
    "expected_return_score": 96.0,
    "energy_burn_cost": 10.0,
    "net_jev_score": 81.2,
    "roi_ratio": 9.12,
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
        if not (q_path.exists() and d_path.exists() and j_path.exists()):
            continue

        q = json.loads(q_path.read_text(encoding="utf-8"))
        d = json.loads(d_path.read_text(encoding="utf-8"))
        j = json.loads(j_path.read_text(encoding="utf-8"))

        candidates.append({
            "node_id": q["node_id"],
            "node_hash": q.get("node_hash", ""),
            "is_self_benchmark": False,
            "surface_vitality_score": d["surface_vitality_score"],
            "defilter_multiplier": d["defilter_multiplier"],
            "defiltered_exclusivity_score": d["defiltered_exclusivity_score"],
            "illusion_gap": d["illusion_gap"],
            "development_probability_pct": j["metrics"]["development_probability_pct"],
            "expected_return_score": j["metrics"]["expected_return_score"],
            "energy_burn_cost": j["metrics"]["energy_burn_cost"],
            "net_jev_score": j["metrics"]["net_jev_score"],
            "roi_ratio": j["metrics"]["roi_ratio"],
            "verdict_code": j["decision"]["verdict_code"],
            "verdict_label": j["decision"]["verdict_label"],
            "continue_investing": j["decision"]["continue_investing"],
            "pathology_count": d["pathology_count"],
            "pathology_titles": [p["title"] for p in d.get("detected_pathologies", [])],
        })

    benchmark = dict(SELF_MAINLINE_BENCHMARK)
    if personal_mainline_name:
        benchmark["node_id"] = f"SELF_MAINLINE ({personal_mainline_name})"

    all_nodes = [benchmark] + sorted(candidates, key=lambda x: x["net_jev_score"], reverse=True)

    # 计算最优精力分配权重 (Optimal Energy Allocation %)
    # 规则：
    # 1. 凡是 STOP_AND_PIVOT 或 net_jev_score <= 0 的对象，精力分配权重强制为 0.0%（坚决止损）
    # 2. 个人硬核成长主线保底配置 >= 60% 权重
    # 3. 剩余权重按正向候选人的 max(0, net_jev_score) 比例分配
    positive_candidates = [c for c in candidates if c["net_jev_score"] > 0 and c["verdict_code"] != "STOP_AND_PIVOT"]
    total_positive_jev = sum(c["net_jev_score"] for c in positive_candidates)

    if not positive_candidates:
        benchmark["recommended_energy_pct"] = 100.0
        for c in candidates:
            c["recommended_energy_pct"] = 0.0
    else:
        social_pool_cap = min(40.0, total_positive_jev * 0.8)
        benchmark["recommended_energy_pct"] = round(100.0 - social_pool_cap, 1)
        for c in candidates:
            if c in positive_candidates:
                c["recommended_energy_pct"] = round(social_pool_cap * (c["net_jev_score"] / total_positive_jev), 1)
            else:
                c["recommended_energy_pct"] = 0.0

    portfolio_summary = {
        "schema_version": "1.0",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_contacts_evaluated": len(candidates),
        "positive_return_contacts": [c["node_id"] for c in positive_candidates],
        "stop_loss_contacts": [c["node_id"] for c in candidates if c["verdict_code"] == "STOP_AND_PIVOT"],
        "allocation_matrix": [benchmark] + sorted(candidates, key=lambda x: x["net_jev_score"], reverse=True),
    }

    (output_dir / "portfolio_matrix.json").write_text(
        json.dumps(portfolio_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return portfolio_summary
