# `she-actually-doesnt-like-me` (JEV-Mirror v2.0) 系统架构与完全脱敏设计文档 (`ARCHITECTURE.md`)

## 一、 总体架构设计原则 (v2.0 Architecture)

1. **事件驱动的有限状态机 + 贝叶斯后验修正 + 风险平价投资组合**：
   - 将原本静态的全局汇总升级为滑动时间窗有限状态机（`TimelineFSMNode`）与 CUSUM 拐点检测；
   - 引入博弈论信号甄别（Cheap Talk vs. Costly Signal）与贝叶斯对数几率更新（`JEVBayesianNode`）；
   - 新增针对当前窗口的战术熔断守护器（`TacticalAdvisorNode`）与多人情绪夏普比率配置器（`PortfolioAllocatorNode`）。
2. **彻底的隐私物理隔离（Zero-PII in Open Source）**：
   - 开源主工程目录下**不存放任何聊天记录、真实姓名/备注、账号 ID 或个人隐私数据**。
   - 所有涉及个人隐私的原始记录、单平台汇总池（`platforms/`）、跨平台身份绑定表（`identity_links.json`）、数据库与密钥均强制隔离在独立的 `_private_vault/` 目录下，并由 `.github/workflows/zero_pii_guard.yml` 在 CI 层强制守卫。

## 二、 分布式分析节点链（v2.0 完整拓扑）

| 节点模块 | 输入契约 | 输出状态描述符 | 核心职责 |
| :--- | :--- | :--- | :--- |
| **`feature_vectorizer.py`** | `quant_state.json` | 内存纯数值切片 `WindowMetricSlice` | 将时间序列脱敏映射为相对时间窗代号（`W01 - W06`）、消息密度比、对称度与波动率 $\sigma$ |
| **`timeline_fsm_node.py`** | `WindowMetricSlice` 列表 | `state/timeline_state.json` | 映射 `S0 ~ S5` 六大标准关系阶段状态，通过 CUSUM 检验自动定位断联与回捞拐点 |
| **`defilter_node.py`** | `quant_state.json` + `offline_signals.json` | `state/defilter_state.json` | 五维去滤镜病灶诊断 + 博弈论廉价信号（Cheap Talk）与高昂信号（Costly Signal）分离 |
| **`jev_bayesian_node.py`** | `quant_state.json` + `defilter_state.json` | `state/jev_state.json` | 贝叶斯先验-似然 Log-Odds 后验概率更新、净期望值 $\text{Net JEV}$ 与情绪夏普比率计算 |
| **`tactical_advisor_node.py`** | `timeline_state.json` + `jev_state.json` | `state/tactical_state.json` | 着重当下态势定性，生成 72 小时硬核熔断指令与 30 天算力重路由协议 |
| **`solace_node.py`** | `defilter_state.json` + `jev_state.json` | `state/solace_state.json` | 主体性重建与认知失调拆解，剥离对方零成本免责长文的伪善滤镜 |
| **`portfolio_node.py`** | 多节点 `state/*.json` + 个人研发基准 | `portfolio_matrix.json` | 计算多人关系夏普比率（Sharpe Ratio）与最大情绪回撤（MDD），自动将负夏普节点权重砍为 `0.0%` |
