#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/timeline_fsm_node.py
[v2.0 核心深化] 关系时间线状态机与关键拐点归因引擎 (Timeline & Inflection Engine)
将跨平台重排后的时间序列切片映射为 6 个标准关系状态 (FSM States) + 双向同频态，
并通过滑动窗口的累积和检验 (CUSUM Change-Point Detection) 自动定位关键转折点。
全程零文本依赖 (Zero-PII & Zero-Chat-Text)。
"""

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import List, Dict, Any

from ..ingestors.feature_vectorizer import extract_window_metric_slices


FSM_STATE_LABELS = {
    "S0_INITIAL_PROBE": "破冰试探期",
    "S1_ILLUSION_PEAK": "高热滤镜期",
    "S2_ASYMMETRIC_DRAIN": "单向失血期",
    "S3_RUPTURE_FREEZE": "导火索断联期",
    "S4_INTERMITTENT_LURE": "间歇性回捞期",
    "S5_TERMINAL_PIVOT": "终局清醒止损期",
    "S5_SYMMETRIC_GROWTH": "双向正反馈同频期",
}


@dataclass
class TimelineEpoch:
    epoch_id: str
    start_window: str          # 相对时间窗代号，如 "W01" (脱敏，不含真实日期)
    end_window: str            # 如 "W06" 或 "NOW"
    fsm_state: str             # S0 ~ S5 状态码
    msg_density_ratio: float   # 相对基线消息密度
    symmetry_score: float      # 双边对称度 [0.0, 1.0]
    key_trigger_tag: str       # 触发拐点的抽象事件标签 (如 PUBLIC_AVOIDANCE / UTILITARIAN_PING)
    stage_diagnosis: str       # 该阶段核心定性结论


class TimelineFSMNode:
    """基于滑动时间窗的分布式状态机与拐点推导节点（零文本依赖）"""

    @staticmethod
    def detect_cusum_inflections(window_metrics: List[Dict[str, Any]], threshold: float = 0.35) -> List[Dict[str, Any]]:
        """
        基于累积和检验 (CUSUM Change-Point Detection) 识别密度或对称度发生断崖式跳变的拐点纪元。
        """
        if not window_metrics:
            return []
        mean_sym = sum(float(w.get("symmetry_index", 0.5)) for w in window_metrics) / len(window_metrics)
        cusum_pos = 0.0
        cusum_neg = 0.0
        inflections = []
        for idx, win in enumerate(window_metrics):
            sym = float(win.get("symmetry_index", 0.5))
            density = float(win.get("density_ratio", 1.0))
            diff = sym - mean_sym
            cusum_pos = max(0.0, cusum_pos + diff)
            cusum_neg = min(0.0, cusum_neg + diff)
            if abs(cusum_neg) >= threshold or density < 0.15 or density > 1.6:
                inflections.append({
                    "epoch_index": idx + 1,
                    "window": f"{win.get('start_win', '')} - {win.get('end_win', '')}",
                    "cusum_neg": round(cusum_neg, 3),
                    "cusum_pos": round(cusum_pos, 3),
                    "trigger_tag": win.get("offline_event_tag", "NONE"),
                })
        return inflections

    def evaluate_epochs(self, window_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        epochs: List[TimelineEpoch] = []
        for idx, win in enumerate(window_metrics):
            density = float(win.get("density_ratio", 1.0))
            sym = float(win.get("symmetry_index", 0.5))
            init_rate = float(win.get("self_initiation_rate", 0.5))
            trigger = str(win.get("offline_event_tag", "NONE"))
            custom_diag = str(win.get("trigger_attribution", "")).strip()

            if density < 0.15:
                state = "S3_RUPTURE_FREEZE"
                diag = custom_diag or "断崖式冷却/主动抽离：因核心负面信号触发防御性断联"
            elif idx > 0 and epochs[-1].fsm_state == "S3_RUPTURE_FREEZE" and (init_rate < 0.4 or trigger == "UTILITARIAN_PING"):
                state = "S4_INTERMITTENT_LURE"
                diag = custom_diag or "间歇性强化回捞：对方低成本主动破冰（常伴随资源求助或搭子需求），极易诱发沉没成本幻觉"
            elif (
                trigger in ("TERMINAL_PIVOT", "ALIBI_AND_CORE_NEED_EVASION")
                or (idx > 0 and epochs[-1].fsm_state == "S4_INTERMITTENT_LURE" and density <= 0.55 and sym <= 0.30)
            ):
                state = "S5_TERMINAL_PIVOT"
                diag = custom_diag or "终局清醒与止损：识破防御性长文或回避核心诉求，主动锁死精力输出"
            elif density > 1.5 and sym < 0.50:
                state = "S1_ILLUSION_PEAK"
                diag = custom_diag or "高热滤镜期：表层秒回与高频互动掩盖了底层排他性缺失"
            elif init_rate > 0.72 or sym < 0.35:
                state = "S2_ASYMMETRIC_DRAIN"
                diag = custom_diag or "单向失血期：我方承担绝大部分话题发起与情绪托底，边际回报递减"
            elif sym >= 0.78 and density >= 0.90:
                state = "S5_SYMMETRIC_GROWTH"
                diag = custom_diag or "双向正反馈同频期：线上线下行为一致，具备清晰的双向主动与情绪托底"
            else:
                state = "S0_INITIAL_PROBE"
                diag = custom_diag or "常规社交基线交互"

            epochs.append(TimelineEpoch(
                epoch_id=f"EPOCH_{idx+1:02d}",
                start_window=win["start_win"],
                end_window=win["end_win"],
                fsm_state=state,
                msg_density_ratio=round(density, 2),
                symmetry_score=round(sym, 2),
                key_trigger_tag=trigger,
                stage_diagnosis=diag,
            ))

        inflections = self.detect_cusum_inflections(window_metrics)
        current_state = epochs[-1].fsm_state if epochs else "UNKNOWN"
        return {
            "current_fsm_state": current_state,
            "current_fsm_state_cn": FSM_STATE_LABELS.get(current_state, "未知状态"),
            "relapse_loop_count": sum(1 for e in epochs if e.fsm_state == "S4_INTERMITTENT_LURE"),
            "cusum_inflections": inflections,
            "timeline_epochs": [asdict(e) for e in epochs],
        }


def run_timeline_fsm_node(state_dir: Path, personal_mainline: str = "核心系统架构与硬核技术研发") -> Dict[str, Any]:
    """
    运行 v2.0 关系时间线状态机与拐点归因节点，生成并落盘 `state/timeline_state.json`。
    """
    state_dir = Path(state_dir)
    quant = json.loads((state_dir / "quant_state.json").read_text(encoding="utf-8"))
    defilter_path = state_dir / "defilter_state.json"
    defilter = json.loads(defilter_path.read_text(encoding="utf-8")) if defilter_path.exists() else {}
    jev_path = state_dir / "jev_state.json"
    jev = json.loads(jev_path.read_text(encoding="utf-8")) if jev_path.exists() else {}

    offline_signals = defilter.get("offline_signals", {})
    window_metrics = extract_window_metric_slices(quant, offline_signals)

    fsm = TimelineFSMNode()
    fsm_result = fsm.evaluate_epochs(window_metrics)

    verdict_code = jev.get("decision", {}).get("verdict_code", "STOP_AND_PIVOT")
    dev_prob = jev.get("metrics", {}).get("development_probability_pct", 2.4)
    net_jev = jev.get("metrics", {}).get("net_jev_score", -64.8)

    if verdict_code == "STOP_AND_PIVOT":
        rec_develop = False
        rec_banner = "🛑 绝对不建议继续发展（STOP_AND_PIVOT / 立即止损封存）"
        rec_reason = (
            f"贝叶斯真实发展概率仅 {dev_prob}%，净期望值 Net JEV 为 {net_jev}。"
            "对方虽有表层秒回或长文回复，但缺乏排他性高昂信号且触发核心负面边界，继续投入属于纯负期望值内耗。"
        )
    elif verdict_code == "DOWNGRADE_OBSERVE":
        rec_develop = False
        rec_banner = "⚠️ 暂不建议升级投入（DOWNGRADE_OBSERVE / 维持低成本观察）"
        rec_reason = (
            f"当前贝叶斯真实发展概率为 {dev_prob}%（Net JEV = {net_jev}），线上互动流畅但缺乏线下高昂信号检验，"
            "严禁自我感动式单向加码。"
        )
    else:
        rec_develop = True
        rec_banner = "🟢 建议稳步推进发展（INVEST_STEADILY / 双向正反馈同频）"
        rec_reason = (
            f"贝叶斯真实发展概率达 {dev_prob}%，净期望值 Net JEV 为 +{net_jev}，具备高夏普比率的正向期望收益。"
        )

    timeline_state = {
        "schema_version": "2.0",
        "node_id": quant["node_id"],
        "node_hash": quant.get("node_hash", ""),
        "current_fsm_state": fsm_result["current_fsm_state"],
        "current_fsm_state_cn": fsm_result["current_fsm_state_cn"],
        "relapse_loop_count": fsm_result["relapse_loop_count"],
        "cusum_inflections": fsm_result["cusum_inflections"],
        "timeline_epochs": fsm_result["timeline_epochs"],
        "development_recommendation": {
            "recommend_develop": rec_develop,
            "banner": rec_banner,
            "reason": rec_reason,
        },
        "target_mainline": personal_mainline,
    }

    (state_dir / "timeline_state.json").write_text(
        json.dumps(timeline_state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return timeline_state
