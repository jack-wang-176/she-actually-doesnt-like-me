#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/timeline_node.py
兼容入口：统一路由至 v2.0 关系时间线状态机与关键拐点归因引擎 (timeline_fsm_node.py)。
"""

from pathlib import Path
from .timeline_fsm_node import TimelineEpoch, TimelineFSMNode, run_timeline_fsm_node


def run_timeline_node(state_dir: Path, personal_mainline: str = "核心系统架构与硬核技术研发") -> dict:
    return run_timeline_fsm_node(state_dir, personal_mainline=personal_mainline)


__all__ = ["TimelineEpoch", "TimelineFSMNode", "run_timeline_fsm_node", "run_timeline_node"]
