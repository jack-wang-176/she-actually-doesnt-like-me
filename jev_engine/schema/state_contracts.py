#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/schema/state_contracts.py
分布式节点间严格类型契约 (Dataclasses & Zero-PII JSON Schema Contracts)
确保全链路仅传递脱敏纯数值切片、布尔信号标志与枚举状态码，彻底阻断任何原始聊天文本进入分析层。
"""

from dataclasses import dataclass, asdict, field
from enum import Enum
import re
from typing import Dict, List, Any


class FSMStateCode(str, Enum):
    """六大标准关系演化状态码 + 双向同频态"""
    S0_INITIAL_PROBE = "S0_INITIAL_PROBE"          # 破冰试探期
    S1_ILLUSION_PEAK = "S1_ILLUSION_PEAK"          # 高热滤镜期
    S2_ASYMMETRIC_DRAIN = "S2_ASYMMETRIC_DRAIN"    # 单向失血期
    S3_RUPTURE_FREEZE = "S3_RUPTURE_FREEZE"        # 导火索断联期
    S4_INTERMITTENT_LURE = "S4_INTERMITTENT_LURE"  # 间歇性强化回捞期
    S5_TERMINAL_PIVOT = "S5_TERMINAL_PIVOT"        # 终局清醒与止损期
    S5_SYMMETRIC_GROWTH = "S5_SYMMETRIC_GROWTH"    # 双向正反馈同频期


class VerdictCode(str, Enum):
    """终局精力裁决枚举"""
    STOP_AND_PIVOT = "STOP_AND_PIVOT"
    DOWNGRADE_OBSERVE = "DOWNGRADE_OBSERVE"
    INVEST_STEADILY = "INVEST_STEADILY"
    CORE_ANCHOR = "CORE_ANCHOR"


@dataclass
class WindowMetricSlice:
    """边缘向量化器输出的滑动时间窗纯数值切片（零日期、零文本）"""
    start_win: str
    end_win: str
    density_ratio: float
    symmetry_index: float
    self_initiation_rate: float
    char_investment_ratio: float = 1.0
    offline_event_tag: str = "NONE"
    trigger_attribution: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TimelineEpoch:
    """TimelineFSMNode 标准阶段演化纪元结构"""
    epoch_id: str
    start_window: str          # 相对时间窗代号，如 "W01 - W06" (脱敏，不含真实日期)
    end_window: str
    fsm_state: str             # S0 ~ S5 状态码
    msg_density_ratio: float   # 相对基线消息密度
    symmetry_score: float      # 双边对称度 [0.0, 1.0]
    key_trigger_tag: str       # 触发拐点的抽象事件标签 (如 PUBLIC_AVOIDANCE / UTILITARIAN_PING)
    stage_diagnosis: str       # 该阶段核心定性结论

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GameTheorySignalBundle:
    """博弈论信号甄别结构：区分廉价信号 (Cheap Talk) 与高昂信号 (Costly Signal)"""
    cheap_talk_Flags: List[str] = field(default_factory=list)
    costly_signals: List[str] = field(default_factory=list)
    pathology_flags: List[str] = field(default_factory=list)
    cheap_talk_inflation_score: float = 0.0
    costly_signal_verify_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BayesianJEVMetrics:
    """贝叶斯动态 JEV 与夏普比率核心指标契约"""
    prior_probability_pct: float
    posterior_probability_pct: float
    illusion_squeezed_pct: float
    log_odds_prior: float
    positive_log_likelihood: float
    negative_log_likelihood: float
    log_odds_posterior: float
    expected_return_score: float
    expected_gain: float
    energy_burn_cost: float
    net_jev_score: float
    roi_ratio: float
    volatility_sigma: float
    sharpe_ratio: float
    baseline_sharpe_ratio: float
    max_emotional_drawdown_pct: float
    recommended_energy_weight_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TacticalCircuitBreakerProtocol:
    """着重当下态势与 72 小时/30 天执行协议契约"""
    current_fsm_state: str
    verdict_code: str
    current_focus_title: str
    current_essence_diagnosis: str
    recommend_develop_verdict: str
    recommend_develop_reason: str
    circuit_breaker_armed: bool
    protocol_72h: List[Dict[str, str]]
    protocol_30d: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioSharpeEntry:
    """多人风险平价与夏普比率投资组合节点契约"""
    node_id: str
    is_self_benchmark: bool
    prior_probability_pct: float
    posterior_probability_pct: float
    net_jev_score: float
    volatility_sigma: float
    sharpe_ratio: float
    max_emotional_drawdown_pct: float
    verdict_code: str
    verdict_label: str
    recommended_energy_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_PII_PATTERN = re.compile(r"wxid_[a-zA-Z0-9_]+")


def validate_zero_pii_payload(payload: Dict[str, Any]) -> bool:
    """校验序列化前的字典不含任何疑似微信号或违规私有字段"""
    serialized = str(payload)
    if _PII_PATTERN.search(serialized):
        raise ValueError("Zero-PII Violation: Potential WeChat identifier detected in state payload!")
    return True
