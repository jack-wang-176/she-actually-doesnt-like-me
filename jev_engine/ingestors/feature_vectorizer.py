#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/ingestors/feature_vectorizer.py
边缘脱敏特征提取器 (Edge Zero-PII Feature Vectorizer)：
  在本地边缘侧将原始记录或月度统计单向哈希/向量化为纯数值滑动时间窗切片 (window_metrics)，
  彻底剥离真实日期时间戳与自然语言文本，仅输出相对时间窗代号 (如 W01 - W06)、消息密度比、
  双边对称度 [0.0, 1.0]、主动破冰率 [0.0, 1.0] 与抽象拐点事件标签。
"""

import hashlib
import math
from typing import Dict, List, Any
from ..schema.state_contracts import WindowMetricSlice, validate_zero_pii_payload


def hash_identity_token(raw_identifier: str, salt: str = "jev_v2_zero_pii") -> str:
    """单向不可逆哈希，用于将本地标识符映射为匿名节点 Hash"""
    digest = hashlib.sha256(f"{salt}:{raw_identifier}".encode("utf-8")).hexdigest()
    return f"node_{digest[:12]}"


def extract_window_metric_slices(quant_state: Dict[str, Any], offline_signals: Dict[str, bool] = None) -> List[Dict[str, Any]]:
    """
    将 quant_state 中的预置 window_metrics 或 monthly_vectors 转换为标准化的脱敏纯数值时间窗切片。
    如果节点已提供显式的 v2.0 `window_metrics` 切片，则直接规范化输出；
    否则从 `monthly_vectors` 自动计算相对基线密度比、双边对称度与抽象事件标签。
    """
    offline_signals = offline_signals or {}

    if "window_metrics" in quant_state and isinstance(quant_state["window_metrics"], list) and quant_state["window_metrics"]:
        slices = []
        for win in quant_state["window_metrics"]:
            s = WindowMetricSlice(
                start_win=str(win.get("start_win", "W01")),
                end_win=str(win.get("end_win", "NOW")),
                density_ratio=round(float(win.get("density_ratio", 1.0)), 2),
                symmetry_index=round(float(win.get("symmetry_index", 0.5)), 2),
                self_initiation_rate=round(float(win.get("self_initiation_rate", 0.5)), 2),
                char_investment_ratio=round(float(win.get("char_investment_ratio", 1.0)), 2),
                offline_event_tag=str(win.get("offline_event_tag", "NONE")),
                trigger_attribution=str(win.get("trigger_attribution", "")),
            )
            slices.append(s.to_dict())
        validate_zero_pii_payload({"slices": slices})
        return slices

    monthly = quant_state.get("monthly_vectors", {})
    sorted_keys = sorted(monthly.keys())
    if not sorted_keys:
        sym_norm = round(min(1.0, max(0.0, quant_state.get("indices", {}).get("symmetry_index", 50.0) / 100.0)), 2)
        init_rate = round(quant_state.get("dynamics", {}).get("self_initiation_pct", 50.0) / 100.0, 2)
        char_ratio = round(float(quant_state.get("volume", {}).get("char_investment_ratio", 1.0)), 2)
        return [
            WindowMetricSlice(
                start_win="W01",
                end_win="NOW",
                density_ratio=1.0,
                symmetry_index=sym_norm,
                self_initiation_rate=init_rate,
                char_investment_ratio=char_ratio,
                offline_event_tag="BASELINE_WINDOW",
                trigger_attribution="常规社交基线观测窗口",
            ).to_dict()
        ]

    totals = [max(1, monthly[k].get("total", 0)) for k in sorted_keys]
    baseline_msgs = max(1.0, sum(totals) / len(totals))

    slices: List[Dict[str, Any]] = []
    week_cursor = 1
    for idx, k in enumerate(sorted_keys):
        vec = monthly[k]
        total = vec.get("total", 0)
        self_chars = vec.get("self_chars", 0)
        peer_chars = max(1, vec.get("peer_chars", 1))
        char_ratio = round(self_chars / peer_chars, 2)
        init_rate = round(vec.get("self_init_pct", 50.0) / 100.0, 2)
        density = round(total / baseline_msgs, 2)

        # 将字数失衡与破冰失衡映射为 [0.0, 1.0] 的双边对称度
        init_penalty = abs(init_rate - 0.5) * 1.1
        char_penalty = min(0.45, abs(char_ratio - 1.0) * 0.22)
        sym_score = round(max(0.10, min(0.98, 1.0 - init_penalty - char_penalty)), 2)

        w_start = f"W{week_cursor:02d}"
        w_end = "NOW" if idx == len(sorted_keys) - 1 else f"W{week_cursor + 3:02d}"
        week_cursor += 4

        tag = "NONE"
        attr = "常规社交基线交互"
        if density < 0.15:
            tag = "DEFENSIVE_RUPTURE_FREEZE"
            attr = "主动抽离断联并缺席关键节点，开启自我保护防御机制"
        elif idx > 0 and slices[-1]["density_ratio"] < 0.15 and init_rate < 0.45:
            tag = "UTILITARIAN_PING"
            attr = "对方以功利性资源求助破冰并阶段性主动约见，诱发沉没成本幻觉与二次内耗"
        elif idx == len(sorted_keys) - 1 and offline_signals.get("companionship_evasion"):
            tag = "ALIBI_AND_CORE_NEED_EVASION"
            attr = "暴露借口掩饰夜间社交鸽约 + 长文客套说教却精准闪避核心陪伴诉求，彻底看清底牌"

        slices.append(
            WindowMetricSlice(
                start_win=w_start,
                end_win=w_end,
                density_ratio=density,
                symmetry_index=sym_score,
                self_initiation_rate=init_rate,
                char_investment_ratio=char_ratio,
                offline_event_tag=tag,
                trigger_attribution=attr,
            ).to_dict()
        )

    validate_zero_pii_payload({"slices": slices})
    return slices


def compute_latency_volatility(quant_state: Dict[str, Any], window_slices: List[Dict[str, Any]]) -> float:
    """
    计算情绪与交互波动率 sigma_volatility：
    由回复延迟方差、阶段消息密度剧烈震荡（忽冷忽热）与间歇性强化频次共同决定。
    """
    densities = [w.get("density_ratio", 1.0) for w in window_slices] or [1.0]
    mean_d = sum(densities) / len(densities)
    var_d = sum((d - mean_d) ** 2 for d in densities) / max(1, len(densities))
    density_std = math.sqrt(var_d)

    peer_lat = quant_state.get("latency", {}).get("peer", {})
    mean_sec = float(peer_lat.get("mean_sec", 120.0))
    median_sec = max(1.0, float(peer_lat.get("median_sec", 30.0)))
    latency_skew = min(2.5, max(0.2, (mean_sec / median_sec) * 0.18))

    silence_cnt = len(quant_state.get("dynamics", {}).get("silence_breaks", []))
    relapse_penalty = silence_cnt * 0.45

    sigma = round(max(0.35, min(3.50, 0.45 + density_std * 1.15 + latency_skew + relapse_penalty)), 2)
    return sigma
