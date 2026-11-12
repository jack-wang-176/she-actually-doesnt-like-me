#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/pipeline.py
[JEV-Mirror v2.0] 分布式节点编排与白皮书渲染管线：
  - 一、核心终局裁决：建不建议继续发展？（贝叶斯后验 P(Develop|E)、Net JEV、Sharpe Ratio、推荐精力权重）
  - 二、关系演进时间线与关键拐点梳理 (Timeline FSM Reconstruction)
  - 三、着重当下：当前态势定性与即刻行动建议 (Current Focus & 72h/30d Tactical Protocol)
  - 四、五维「去滤镜」与博弈论信号甄别 (Signaling Game: Cheap Talk vs Costly Signal)
  - 五、主体性重建与认知失调拆解 (Solace & Agency Rebuilding)
"""

import json
from pathlib import Path
from .ingestors import build_distributed_shards
from .nodes import (
    run_quant_node,
    run_defilter_node,
    run_jev_bayesian_node,
    run_timeline_fsm_node,
    run_tactical_advisor_node,
    run_solace_node,
    run_portfolio_node,
)
from .nodes.timeline_fsm_node import FSM_STATE_LABELS


def render_single_jev_report(state_dir: Path, output_md_path: Path, node_alias: str = None) -> str:
    state_dir = Path(state_dir)
    quant = json.loads((state_dir / "quant_state.json").read_text(encoding="utf-8"))
    defilter = json.loads((state_dir / "defilter_state.json").read_text(encoding="utf-8"))
    jev = json.loads((state_dir / "jev_state.json").read_text(encoding="utf-8"))
    timeline = json.loads((state_dir / "timeline_state.json").read_text(encoding="utf-8"))
    tactical_path = state_dir / "tactical_state.json"
    tactical = (
        json.loads(tactical_path.read_text(encoding="utf-8"))
        if tactical_path.exists()
        else run_tactical_advisor_node(state_dir)
    )
    solace = json.loads((state_dir / "solace_state.json").read_text(encoding="utf-8"))

    display_node = node_alias or quant.get("node_code") or state_dir.parent.name or quant["node_id"]
    m = jev["metrics"]
    d = jev["decision"]

    prior_pct = m.get("prior_probability_pct", 52.0)
    post_pct = m["development_probability_pct"]
    squeezed_pct = m.get("illusion_squeezed_pct", round(max(0.0, prior_pct - post_pct), 1))
    net_jev = m["net_jev_score"]
    sharpe = m.get("sharpe_ratio", -1.85)
    base_sharpe = m.get("baseline_sharpe_ratio", 1.60)
    rec_weight = m.get("recommended_energy_weight_pct", d.get("recommended_energy_weight_pct", 0.0))

    sharpe_str = f"+{sharpe:.2f}" if sharpe > 0 else f"{sharpe:.2f}"
    base_sharpe_str = f"+{base_sharpe:.2f}" if base_sharpe > 0 else f"{base_sharpe:.2f}"
    net_jev_str = f"+{net_jev}" if net_jev > 0 else f"{net_jev}"
    sharpe_cmp = "远低于" if sharpe < 0 else ("低于" if sharpe < base_sharpe else "匹配/优于")

    if post_pct < prior_pct:
        bayesian_note = f"*(表层活跃度先验 `{prior_pct:.1f}%` $\\rightarrow$ 经五维去滤镜与高昂信号缺失修正后挤出 `{squeezed_pct:.1f}%` 滤镜水分)*"
    else:
        bayesian_note = f"*(表层活跃度先验 `{prior_pct:.1f}%` $\\rightarrow$ 经双向高昂信号 Costly Signal 验证后跃升至 `{post_pct:.1f}%`)*"

    lines = [
        "# [JEV-Mirror v2.0] 节点深度诊断与精力裁决白皮书",
        f"> **分析节点代号**：`{display_node}` | **数据抽象层级**：分布式纯数值状态切片 (Zero-PII)",
        "",
        "## 一、 核心终局裁决：建不建议继续发展？",
        f"- **最终结论**：**{d['verdict_label']}**",
        f"- **贝叶斯真实发展概率 $P(\\text{{Develop}} \\mid \\mathcal{{E}})$**：**`{post_pct}%`** {bayesian_note}",
        f"- **净期望值 (Net JEV)**：**`{net_jev_str}`** | **情绪夏普比率 (Sharpe Ratio)**：**`{sharpe_str}`** *({sharpe_cmp}个人硬核研发主线基准 `{base_sharpe_str}`)*",
        f"- **推荐精力分配权重**：**`{rec_weight:.1f}%`**",
        "",
        "## 二、 关系演进时间线与关键拐点梳理 (Timeline FSM Reconstruction)",
        "| 阶段序号 | 相对时间窗 | 状态机定性 (FSM State) | 消息密度比 | 投入对称度 | 核心拐点/触发事件归因 |",
        "| :--- | :--- | :--- | :---: | :---: | :--- |",
    ]

    for ep in timeline.get("timeline_epochs", []):
        fsm_code = ep["fsm_state"]
        fsm_cn = FSM_STATE_LABELS.get(fsm_code, "演化阶段")
        win_str = f"{ep['start_window']} - {ep['end_window']}"
        lines.append(
            f"| **{ep['epoch_id']}** | `{win_str}` | `{fsm_code}` ({fsm_cn}) | "
            f"`{ep['msg_density_ratio']:.2f}x` | `{ep['symmetry_score']:.2f}` | {ep['stage_diagnosis']} |"
        )

    lines.extend([
        "",
        "## 三、 着重当下：当前态势定性与即刻行动建议 (Current Focus & Protocol)",
        "1. **当下核心本质定性**：",
        f"   {tactical['current_essence_diagnosis']}",
        "2. **当下 72 小时硬核止损/执行指令**：",
    ])

    for p_item in tactical.get("protocol_72h", []):
        lines.append(f"   - **{p_item['directive']}**：{p_item['detail']}")

    lines.extend([
        "3. **未来 30 天长周期协议**：",
    ])
    for s30 in tactical.get("protocol_30d", []):
        lines.append(f"   - {s30}")

    sig_game = defilter.get("signaling_game", {})
    lines.extend([
        "",
        "## 四、 博弈论信号甄别与五维「去滤镜」病灶拆解 (Signaling Game & De-filtering)",
        f"- **识别到的廉价信号 (Cheap Talk, 零机会成本)**：{len(sig_game.get('cheap_talk_signals', []))} 项",
    ])
    for ct in sig_game.get("cheap_talk_signals", []):
        lines.append(f"  - `{ct}`")

    lines.append(f"- **验证通过的高昂信号 (Costly Signals, 高机会成本)**：{len(sig_game.get('costly_signals', []))} 项")
    for cs in sig_game.get("costly_signals", []):
        lines.append(f"  - `{cs}`")

    lines.append("")
    if not defilter["detected_pathologies"]:
        lines.append("- ✅ **未检测到显著的假性亲密或养鱼内耗病灶**：双方线上互动与线下高昂信号高度自洽。")
    else:
        for idx, p in enumerate(defilter["detected_pathologies"], 1):
            lines.extend([
                f"### 病灶 {idx}：{p['title']} (`{p['severity']}`)",
                f"- **深层机制剖析**：{p['mechanism']}",
                f"- **去滤镜铁律**：{p['anti_illusion_advice']}",
                "",
            ])

    lines.extend([
        "## 五、 主体性重建与认知失调拆解 (Solace & Agency Rebuilding)",
        f"> 💬 **清醒共情**：{solace['empathy_opening']}",
        "",
    ])
    for item in solace["cognitive_reframe"]:
        lines.append(f"- {item}")

    md_text = "\n".join(lines) + "\n"
    output_md_path = Path(output_md_path)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.write_text(md_text, encoding="utf-8")
    return md_text


def render_portfolio_report(portfolio_data: dict, output_md_path: Path) -> str:
    lines = [
        "# [JEV-Mirror v2.0] 多人风险平价与情绪夏普比率 (Sharpe Ratio) 精力配置报告",
        "",
        "> **零隐私与纯数学分布式抽象说明**：本报告由 `PortfolioAllocatorNode` 仅聚合各自治节点的纯数学状态描述符 (`state/*.json`) 生成，全程不读取、不存储、不生成任何真实对话文本。",
        "",
        "## 一、 建不建议发展 & 风险调整后精力配置矩阵 (Risk-Parity & Sharpe Matrix)",
        "",
        "| 排名 | 评估节点 / 对象 | 先验 $P_0$ $\\rightarrow$ 贝叶斯后验 $P(\\text{Develop}\\mid\\mathcal{E})$ | 净期望值 (Net JEV) | 情绪波动率 $\\sigma$ | **关系夏普比率 (Sharpe)** | 最大回撤 (MDD) | **建不建议发展** | **推荐精力权重** |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :---: |",
    ]

    for idx, item in enumerate(portfolio_data["allocation_matrix"], 1):
        rank_label = "⚓ 基准锚点" if item.get("is_self_benchmark") else f"#{idx - 1}"
        if item.get("is_self_benchmark"):
            dev_banner = "🚀 100% 建议深耕（个人研发基石）"
        elif item["verdict_code"] == "STOP_AND_PIVOT":
            dev_banner = "🛑 绝对不建议发展（立即止损）"
        elif item["verdict_code"] == "DOWNGRADE_OBSERVE":
            dev_banner = "⚠️ 暂不建议升级投入（降级观察）"
        else:
            dev_banner = "🟢 建议稳步推进发展（双向同频）"

        sharpe_val = item.get("sharpe_ratio", 0.0)
        sharpe_str = f"+{sharpe_val:.2f}" if sharpe_val > 0 else f"{sharpe_val:.2f}"
        prior_p = item.get("prior_probability_pct", item["development_probability_pct"])
        post_p = item["development_probability_pct"]

        lines.append(
            f"| {rank_label} | **{item['node_id']}** | `{prior_p:.1f}%` $\\rightarrow$ **`{post_p:.1f}%`** | "
            f"**`{item['net_jev_score']}`** | `{item.get('volatility_sigma', 1.0):.2f}` | **`{sharpe_str}`** | "
            f"`{item.get('max_emotional_drawdown_pct', 0.0):.1f}%` | **{dev_banner}** | **`{item['recommended_energy_pct']}%`** |"
        )

    lines.extend([
        "",
        "## 二、 风险调整后收益推论：当下应该把时间投向哪里？",
        "",
    ])

    pos = portfolio_data.get("positive_return_contacts", [])
    stops = portfolio_data.get("stop_loss_contacts", [])
    self_node = portfolio_data["allocation_matrix"][0]

    lines.append(
        f"- **⚓ 基准无风险收益率 (`{self_node['node_id']}`)**：夏普比率 **`+{self_node['sharpe_ratio']:.2f}`**，推荐配置 **`{self_node['recommended_energy_pct']}%`** 核心精力。投入在个人硬核技术研发（芯片架构、系统工程、核心学业）具备确定性正向复利。"
    )
    if pos:
        lines.append(
            f"- **🟢 具备正向夏普比率、建议稳步推进的节点**：{', '.join(f'`{x}`' for x in pos)}。此类节点线上线下言行一致、具备实质性高昂信号（Costly Signals），可按风险平价权重稳步推进。"
        )
    if stops:
        lines.append(
            f"- **🛑 夏普比率为负或触发熔断、权重强制砍为 0.0% 的节点**：{', '.join(f'`{x}`' for x in stops)}。虽然部分节点曾带来短暂情绪峰值，但伴随极高的回复延迟方差与间歇性强化回撤（高 $\\sigma$），净回报远低于个人主线基准，系统已自动将其精力配额锁死为 `0.0%`。"
        )

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
    run_jev_bayesian_node(state_dir)
    run_timeline_fsm_node(state_dir, personal_mainline=personal_mainline)
    run_tactical_advisor_node(state_dir, personal_mainline=personal_mainline)
    run_solace_node(state_dir, personal_mainline=personal_mainline)
    report_path = reports_dir / "jev_single_report.md"
    render_single_jev_report(state_dir, report_path, node_alias=node_id)
    return report_path
