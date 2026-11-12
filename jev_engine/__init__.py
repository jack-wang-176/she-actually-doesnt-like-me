"""
JEV-Mirror v2.0 (分布式防内耗决策与关系期望值评估框架)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
核心架构 (v2.0 Architecture)：
1. 事件驱动的有限状态机 (Timeline FSM & CUSUM Inflection Engine)
2. 博弈论信号甄别与贝叶斯动态 JEV 裁决器 (Bayesian JEV & Signaling Game)
3. 着重当下处境的战术协议与反间歇性强化熔断器 (Tactical Circuit-Breaker)
4. 风险平价与关系夏普比率投资组合引擎 (Risk-Parity & Relationship Sharpe Portfolio)
5. 严格零隐私泄露架构 (Strict Zero-PII & Zero-Chat-Text)
"""

__version__ = "2.0.0"
__all__ = ["schema", "ingestors", "nodes", "pipeline"]
