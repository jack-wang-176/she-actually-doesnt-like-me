#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/tactical_advisor_node.py
[v2.0 核心深化] 着重“当下内容与目前建议”的战术协议生成与反间歇性强化熔断节点 (Tactical Circuit-Breaker)
根据当前所处的 current_fsm_state、最新时间窗交互特征以及贝叶斯裁决结论，
输出结构化的《当下态势定性与 72 小时/30 天执行协议》(state/tactical_state.json)。
"""

import json
from pathlib import Path
from typing import Dict, Any


class TacticalAdvisorNode:
    """着重当下处境 (Current Context) 的战术决策树与反间歇性强化熔断器"""

    def generate_protocol(
        self,
        quant: Dict[str, Any],
        defilter: Dict[str, Any],
        jev: Dict[str, Any],
        timeline: Dict[str, Any],
        personal_mainline: str = "核心系统架构与硬核技术研发",
    ) -> Dict[str, Any]:
        fsm_state = timeline.get("current_fsm_state", "S5_TERMINAL_PIVOT")
        verdict_code = jev["decision"]["verdict_code"]
        post_prob = jev["metrics"]["development_probability_pct"]
        net_jev = jev["metrics"]["net_jev_score"]
        sharpe = jev["metrics"].get("sharpe_ratio", -1.85)

        if verdict_code == "STOP_AND_PIVOT" or fsm_state in ("S4_INTERMITTENT_LURE", "S2_ASYMMETRIC_DRAIN", "S5_TERMINAL_PIVOT"):
            current_focus_title = "高危情绪反扑 / 沉没成本陷阱期（高外向低排他节点的间歇性强化收尾期）"
            current_essence_diagnosis = (
                "你当前所处的并非“差一点就能走通的暧昧瓶颈”，而是典型的**「高外向低排他节点的间歇性强化收尾期」**。"
                "对方近期哪怕给出长篇文字回复，其核心操作也是通过“免责声明 + 规律作息鸡汤 + 暂不讨论感情”来完成**零成本情绪卸责**——"
                "既维持自己“体面好人”的心理舒适区，又彻底封死承担陪伴责任的可能。"
            )
            recommend_verdict = "绝对不建议发展"
            recommend_reason = f"真实发展率 {post_prob}% (< 5%)，Net JEV = {net_jev}，继续投入属于纯负期望值内耗"
            circuit_breaker_armed = True
            protocol_72h = [
                {
                    "directive": "锁死主动发起率（0% Initiation）",
                    "detail": "不再发起任何日常分享、邀约或情绪倾诉；将自动化提醒或单向资源通道彻底关闭。",
                },
                {
                    "directive": "阻断二次回捞（Anti-Relapse Shield）",
                    "detail": "若后续对方再次因事务求助或寻找日常搭子发起低成本试探，一律采用“延迟 > 6 小时 + 极简客观事务性回复（不超过 10 个字）”，绝不重启情绪窗口。",
                },
                {
                    "directive": "100% 算力重路由（Mainline Re-routing）",
                    "detail": f"将全部心智带宽切回高确定性正向复利的个人硬核工程与研究主线（{personal_mainline}）。",
                },
            ]
            protocol_30d = [
                "物理与注意力彻底隔离：30 天内零主动破冰、零朋友圈情绪投射，彻底度过间歇性强化多巴胺戒断期。",
                f"锚定主线里程碑：将原本分配给该节点的每日时间预算 100% 转化为『{personal_mainline}』的可交付成果。",
            ]
        elif verdict_code == "DOWNGRADE_OBSERVE" or fsm_state == "S0_INITIAL_PROBE":
            current_focus_title = "高滤镜未验真期：线上互动流畅，但缺乏线下公开场合与实质成本付出的交叉检验"
            current_essence_diagnosis = (
                "当前互动处于低烈度安全区，虽无恶性养鱼或底线背离信号，但对方尚未展现出具有高机会成本的排他性投入（Costly Signal）。"
                "此时若单方面高频加码或自我感动式输出，极易打破博弈平衡。"
            )
            recommend_verdict = "暂不建议升级投入"
            recommend_reason = f"当前真实发展率 {post_prob}%，维持低成本观察，严禁自我感动式加码"
            circuit_breaker_armed = False
            protocol_72h = [
                {
                    "directive": "镜像配速法则（Mirror Pacing）",
                    "detail": "字数投入比严格控制在 0.8 ~ 1.2 之间，匹配对方的回复时延，绝不写单向小作文。",
                },
                {
                    "directive": "设置高成本试金石（Costly Signal Probe）",
                    "detail": "通过一次需要对方让渡核心周末时间或公开同行的轻量邀约，检验其真实排他意愿。",
                },
            ]
            protocol_30d = [
                f"维持 80% 算力深耕『{personal_mainline}』，若 30 天内对方无实质性主动破冰与线下履约，自动降级归档。",
            ]
        else:
            current_focus_title = "双向正反馈同频期：线上线下行为一致，具备清晰的双向主动与情绪托底"
            current_essence_diagnosis = (
                f"当前处于高健康度的双向共振期（真实发展率 {post_prob}%，夏普比率 +{sharpe}）。"
                "双方在主动破冰、字数对称度与公开场合边界上高度自洽，具备稳定的正向情绪复利。"
            )
            recommend_verdict = "建议稳步推进发展"
            recommend_reason = f"具备高夏普比率（+{sharpe}）的正向期望收益（Net JEV = +{net_jev}）"
            circuit_breaker_armed = False
            protocol_72h = [
                {
                    "directive": "保持稳定互动节律（Balanced Cadence）",
                    "detail": "维持当前健康的双边破冰比例（45% ~ 55%），保持自然真诚的日常共鸣。",
                },
                {
                    "directive": "推进共同记忆建设（Shared Memory Building）",
                    "detail": "从纯线上交流平滑过渡到高价值的线下共同经历（如共同运动、展览或深度长谈）。",
                },
            ]
            protocol_30d = [
                f"在稳固个人主线『{personal_mainline}』（70% 精力）的基础上，稳步推进关系边界确认。",
            ]

        return {
            "schema_version": "2.0",
            "node_id": quant["node_id"],
            "node_hash": quant.get("node_hash", ""),
            "current_fsm_state": fsm_state,
            "verdict_code": verdict_code,
            "current_focus_title": current_focus_title,
            "current_essence_diagnosis": current_essence_diagnosis,
            "recommend_develop_verdict": recommend_verdict,
            "recommend_develop_reason": recommend_reason,
            "circuit_breaker_armed": circuit_breaker_armed,
            "protocol_72h": protocol_72h,
            "protocol_30d": protocol_30d,
        }


def run_tactical_advisor_node(
    state_dir: Path,
    personal_mainline: str = "核心系统架构与硬核技术研发",
) -> Dict[str, Any]:
    state_dir = Path(state_dir)
    quant = json.loads((state_dir / "quant_state.json").read_text(encoding="utf-8"))
    defilter = json.loads((state_dir / "defilter_state.json").read_text(encoding="utf-8"))
    jev = json.loads((state_dir / "jev_state.json").read_text(encoding="utf-8"))
    timeline = json.loads((state_dir / "timeline_state.json").read_text(encoding="utf-8"))

    advisor = TacticalAdvisorNode()
    tactical_state = advisor.generate_protocol(quant, defilter, jev, timeline, personal_mainline=personal_mainline)
    (state_dir / "tactical_state.json").write_text(
        json.dumps(tactical_state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return tactical_state
