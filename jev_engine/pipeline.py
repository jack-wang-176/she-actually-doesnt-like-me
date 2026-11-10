#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/pipeline.py
she-dont-love-me 分布式节点编排与报告渲染管线：
  - 突出呈现「建不建议继续发展」的明确裁决
  - 完整输出「全周期时间线演进梳理 (Mermaid + 阶段表)」
  - 着重剖析「当前阶段态势 (Current Window Spotlight)」与「目前可执行建议 (24h / 7d / 30d)」
"""

import json
from pathlib import Path
from .ingestors import build_distributed_shards
from .nodes import (
    run_quant_node,
    run_defilter_node,
    run_jev_node,
    run_timeline_node,
    run_solace_node,
    run_portfolio_node,
)


def render_single_jev_report(state_dir: Path, output_md_path: Path) -> str:
    state_dir = Path(state_dir)
    quant = json.loads((state_dir / "quant_state.json").read_text(encoding="utf-8"))
    defilter = json.loads((state_dir / "defilter_state.json").read_text(encoding="utf-8"))
    jev = json.loads((state_dir / "jev_state.json").read_text(encoding="utf-8"))
    timeline = json.loads((state_dir / "timeline_state.json").read_text(encoding="utf-8"))
    solace = json.loads((state_dir / "solace_state.json").read_text(encoding="utf-8"))

    node_id = quant["node_id"]
    m = jev["metrics"]
    d = jev["decision"]
    rec = timeline["development_recommendation"]
    spot = timeline["current_spotlight"]
    adv = timeline["immediate_advice"]
    vol = quant["volume"]
    dyn = quant["dynamics"]
    lat = quant["latency"]["peer"]

    lines = [
        f"# 《`she-dont-love-me` 单人去滤镜评估与时间线决策报告》 — `{node_id}`",
        "",
        "## 一、 终局裁决：建不建议继续发展？ (Development Recommendation & JEV Verdict)",
        "",
        f"> ### 📢 **核心结论：{rec['banner']}**",
        f"> - **裁决依据**：{rec['reason']}",
        f"> - **是否继续投入精力**：**{d['verdict_label']}**（建议后续主动破冰率控制在 **{d['recommended_self_initiation_pct']}%**）",
        "",
        "| 核心评估维度 | 量化结果 | 深度诊断解读 |",
        "| :--- | :--- | :--- |",
        f"| **建不建议继续发展** | **{rec['banner']}** | {d['action_directive']} |",
        f"| **感情正向发展可能性 $P(\\text{{Develop}})$** | **{m['development_probability_pct']}%** | 经五维去滤镜系数 ($\\alpha={defilter['defilter_multiplier']}$) 校准后的真实发展概率 |",
        f"| **净联合期望值 (Net JEV)** | **{m['net_jev_score']}** (区间 `-100 ~ +100`) | 真实回报分 `{m['expected_return_score']}` vs 情绪损耗成本 `{m['energy_burn_cost']}` (ROI = `{m['roi_ratio']}`) |",
        f"| **表层热度 vs 去滤镜排他分** | `{defilter['surface_vitality_score']}` $\\rightarrow$ **`{defilter['defiltered_exclusivity_score']}`** | **滤镜水分 (Illusion Gap)：`{defilter['illusion_gap']}` 分** |",
        "",
        "## 二、 全周期时间线梳理与阶段演进 (Relationship Timeline & Phase Evolution)",
        "",
        "```mermaid",
        "graph LR",
    ]

    phases = timeline.get("phases", [])
    for idx, p in enumerate(phases):
        short_tag = p["phase_tag"].split("(")[0].replace("🎯 ", "").strip()
        node_code = f"P{idx}"
        label = f"\"{p['period']}<br/>{short_tag}<br/>({p['total_messages']}条 | 字数比{p['char_investment_ratio']}:1)\""
        lines.append(f"    {node_code}[{label}]")
        if idx > 0:
            lines.append(f"    P{idx-1} --> {node_code}")
        if p.get("is_current_window"):
            lines.append(f"    style {node_code} fill:#ffe4e1,stroke:#ff4500,stroke-width:3px")

    lines.extend([
        "```",
        "",
        "| 时间窗口 | 互动总量 (我 / 对方) | 字数投入比 | 我方破冰率 | 阶段定性 | 阶段态势还原 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for p in phases:
        period_str = f"**{p['period']} (当前)**" if p.get("is_current_window") else p["period"]
        lines.append(
            f"| {period_str} | **{p['total_messages']}** ({p['self_messages']} / {p['peer_messages']}) | "
            f"`{p['char_investment_ratio']} : 1` | `{p['self_initiation_pct']}%` | **{p['phase_tag']}** | {p['phase_diagnosis']} |"
        )

    lines.extend([
        "",
        "## 三、 🎯 着重聚焦：当前阶段态势与目前可执行建议 (Current Focus & Immediate Action Plan)",
        "",
        f"### 1. 当前窗口（`{spot['window_period']}`）深度态势剖析",
        f"- **近期互动量趋势**：{spot['volume_trend']}",
        f"- **当前投入失衡度**：当前字数比 **{spot['current_char_ratio']}** ｜ 当前我方主动破冰占比 **{spot['current_self_init_pct']}**",
        f"- **当下真实处境点破**：{spot['core_reality_assessment']}",
        "",
        f"### 2. 目前分步行动建议（核心策略：**{adv['focus_theme']}**）",
        f"- ⏱️ {adv['now_24h']}",
        f"- 📅 {adv['next_7d']}",
        f"- 🚀 {adv['next_30d']}",
        "",
        "## 四、 五维「去滤镜」深层病灶点破 (De-filtering & Pathology Diagnosis)",
        "",
    ])

    if not defilter["detected_pathologies"]:
        lines.append("- ✅ **未检测到显著的假性亲密或养鱼内耗病灶**：双方线上互动与线下边界基本自洽。")
    else:
        for idx, p in enumerate(defilter["detected_pathologies"], 1):
            lines.extend([
                f"### 病灶 {idx}：{p['title']} (`{p['severity']}`)",
                f"- **深层机制剖析**：{p['mechanism']}",
                f"- **去滤镜铁律**：{p['anti_illusion_advice']}",
                "",
            ])

    lines.extend([
        "## 五、 复杂情境心理抚慰与主体性重建 (Solace & Agency Rebuilding)",
        "",
        f"> 💬 **清醒共情**：{solace['empathy_opening']}",
        "",
        "### 认知重构与脱敏要点",
    ])
    for item in solace["cognitive_reframe"]:
        lines.append(f"- {item}")

    lines.extend([
        "",
        f"### 能量迁移协议（锚定主线：`{solace['rebuilding_protocol']['target_mainline']}`）",
        f"- **核心原则**：{solace['rebuilding_protocol']['principle']}",
    ])
    for step in solace["rebuilding_protocol"]["steps"]:
        lines.append(f"- {step}")

    md_text = "\n".join(lines) + "\n"
    output_md_path = Path(output_md_path)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.write_text(md_text, encoding="utf-8")
    return md_text


def render_portfolio_report(portfolio_data: dict, output_md_path: Path) -> str:
    lines = [
        "# 《`she-dont-love-me` 多人横向对比与精力投资组合分配报告》",
        "",
        "> **零隐私与纯数学分布式抽象说明**：本报告由 `PortfolioAllocatorNode` 仅聚合各自治节点的纯数学状态描述符 (`state/*.json`) 生成，全程不读取、不创建任何聊天记录文本。",
        "",
        "## 一、 建不建议发展 & 精力配置总览矩阵 (Development Verdict & Energy Allocation Matrix)",
        "",
        "| 排名 | 评估节点 / 对象 | 表层热度 | 去滤镜系数 ($\\alpha$) | 感情发展可能性 $P(\\text{Develop})$ | 净期望值 (Net JEV) | **建不建议发展** | **推荐精力分配权重** |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for idx, item in enumerate(portfolio_data["allocation_matrix"], 1):
        rank_label = "⚓ 基准锚点" if item.get("is_self_benchmark") else f"#{idx - 1}"
        if item.get("is_self_benchmark"):
            dev_banner = "🚀 100% 建议深耕（个人成长基石）"
        elif item["verdict_code"] == "STOP_AND_PIVOT":
            dev_banner = "❌ 坚决不建议发展（立即止损）"
        elif item["verdict_code"] == "DOWNGRADE_OBSERVE":
            dev_banner = "⚠️ 暂不建议单向发展（降级观察）"
        else:
            dev_banner = "✅ 建议稳步发展（双向正向）"

        lines.append(
            f"| {rank_label} | **{item['node_id']}** | `{item['surface_vitality_score']}` | `{item['defilter_multiplier']}` | "
            f"**{item['development_probability_pct']}%** | **{item['net_jev_score']}** | **{dev_banner}** | **{item['recommended_energy_pct']}%** |"
        )

    lines.extend([
        "",
        "## 二、 目前总体精力分配建议：当下应该把时间投向哪里？",
        "",
    ])

    pos = portfolio_data.get("positive_return_contacts", [])
    stops = portfolio_data.get("stop_loss_contacts", [])

    if pos:
        lines.append(f"- **✅ 建议继续接触/发展的对象**：{', '.join(f'`{x}`' for x in pos)}。此类节点线上线下言行一致、无恶性养鱼或公开避嫌病灶，可按矩阵推荐权重分配日常社交精力。")
    else:
        lines.append("- **✅ 建议继续接触/发展的对象**：当前候选池中**暂无净期望值 (Net JEV) 为正的外部对象**。")

    if stops:
        lines.append(f"- **❌ 坚决不建议发展、必须立即归零的对象**：{', '.join(f'`{x}`' for x in stops)}。经去滤镜节点诊断，此类对象存在严重的『广谱社交错觉』『公开场合避嫌』『货架养鱼心态』或『回避实质陪伴』病灶，继续投入的边际回报为负，推荐精力权重强制锁定为 **0.0%**。")

    self_node = portfolio_data["allocation_matrix"][0]
    lines.extend([
        f"- **🚀 当下最高优先级主线 (`{self_node['node_id']}`)**：配置 **{self_node['recommended_energy_pct']}%** 的核心精力。个人硬核研发与能力进阶具备 **95%+ 的确定性正反馈** 与最高的长期复利（ROI = `{self_node['roi_ratio']}`）。",
        "",
        "## 三、 各候选节点去滤镜画像与目前行动指引",
        "",
    ])

    for item in portfolio_data["allocation_matrix"]:
        if item.get("is_self_benchmark"):
            continue
        p_titles = item.get("pathology_titles", [])
        p_str = "；".join(p_titles) if p_titles else "无显著病灶（双向互动健康）"
        lines.extend([
            f"### 🔹 `{item['node_id']}` — 净期望值 `{item['net_jev_score']}` ｜ 推荐精力 `{item['recommended_energy_pct']}%`",
            f"- **滤镜拆解**：线上表层热度 `{item['surface_vitality_score']}` 分 $\\rightarrow$ 去滤镜后真实排他度 `{item['defiltered_exclusivity_score']}` 分（滤镜水分 `{item.get('illusion_gap', 0.0)}` 分）",
            f"- **识别病灶 ({item['pathology_count']} 项)**：{p_str}",
            f"- **目前建议**：{item['verdict_label']}",
            "",
        ])

    md_text = "\n".join(lines) + "\n"
    output_md_path = Path(output_md_path)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.write_text(md_text, encoding="utf-8")
    return md_text


def run_distributed_node_pipeline(
    node_id: str,
    node_root: Path,
    ingest_from_raw: bool = True,
    personal_mainline: str = "核心系统架构与硬核技术研发",
):
    node_root = Path(node_root)
    raw_dir = node_root / "raw"
    shards_dir = node_root / "shards"
    state_dir = node_root / "state"
    reports_dir = node_root / "reports"

    if ingest_from_raw and raw_dir.exists():
        build_distributed_shards(node_id, raw_dir, shards_dir)

    if (shards_dir / "meta_shard.json").exists() and (shards_dir / "session_shard.json").exists():
        run_quant_node(shards_dir, state_dir)

    if not (state_dir / "quant_state.json").exists():
        raise FileNotFoundError(f"节点 [{node_id}] 缺少 state/quant_state.json 或有效的 shards/ 数据。")

    run_defilter_node(shards_dir, state_dir)
    run_jev_node(state_dir)
    run_timeline_node(state_dir, personal_mainline=personal_mainline)
    run_solace_node(state_dir, personal_mainline=personal_mainline)
    report_path = reports_dir / "jev_single_report.md"
    render_single_jev_report(state_dir, report_path)
    return report_path
