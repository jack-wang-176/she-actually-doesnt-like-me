#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_engine/nodes/jev_node.py
兼容入口：统一路由至 v2.0 贝叶斯动态 JEV 与博弈论收益裁决器 (jev_bayesian_node.py)。
"""

from pathlib import Path
from .jev_bayesian_node import JEVBayesianNode, run_jev_bayesian_node


def run_jev_node(state_dir: Path) -> dict:
    return run_jev_bayesian_node(state_dir)


__all__ = ["JEVBayesianNode", "run_jev_bayesian_node", "run_jev_node"]
