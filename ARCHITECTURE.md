# `she-dont-love-me` 系统架构与完全脱敏设计文档 (`ARCHITECTURE.md`)

## 一、 总体架构设计原则

1. **彻底的隐私物理隔离（Zero-PII in Open Source）**：
   - 开源主工程目录下**不存放任何聊天记录、真实姓名/备注、账号 ID 或个人隐私数据**。
   - 所有涉及个人隐私的原始记录、单平台汇总池（`platforms/`）、跨平台身份绑定表（`identity_links.json`）、数据库与密钥均强制隔离在独立的 `_private_vault/` 目录下（由 `.gitignore` 严格排除，并可独立作为私有 Git 仓库维护）。
2. **导入（Ingestion）与分析（Analysis）完全解耦**：
   - 导入层只负责多平台数据清洗、幂等去重与时间线重排，输出标准化的分布式微切片（`shards/`）；
   - 分析层由 5 个独立的分布式状态节点（`Quant` $\rightarrow$ `Defilter` $\rightarrow$ `JEV` $\rightarrow$ `Solace` $\rightarrow$ `Portfolio`）组成，节点之间仅通过轻量级状态描述符（`state/*.json`）通信，**分析引擎与多人投资组合器全程零接触原始对话文本**。

---

## 二、 多平台汇总、手动关系连接与实时重排三层设计

由于现实中聊天记录往往分布在微信、QQ、Telegram 等多个平台，且存在分批导出或实时增量更新，直接对单一文件做静态分析会导致严重的视角缺失或时序错乱。本系统在 `jev_engine/ingestors/multi_platform_sync.py` 中实现了三层分布式汇聚架构：

### 1. 第一层：单平台总体聊天记录汇总 (`PlatformAggregator`)
- **存储结构**：`_private_vault/platforms/<platform>/<account_id>/pool.json`
- **幂等增量更新机制**：
  - 每条导入消息基于 `(platform, account_id, timestamp, is_self, content)` 计算 20 位 SHA-1 唯一指纹 `msg_uid`。
  - 当实时增量消息或重叠批次导入时，自动通过哈希表 $O(1)$ 过滤重复记录，仅追加新消息并更新单平台水位线 `watermark_ts`。

### 2. 第二层：上层手动跨平台关系连接 (`IdentityLinkRegistry`)
- **存储结构**：`_private_vault/identity_links.json`
- **显式身份绑定**：
  - 不同平台的账号体系完全异构，系统提供 `link-identity` 接口由用户手动指定映射关系（例如将 `wechat:acc_a` 与 `qq:acc_b` 显式连接到统一分析节点 `Candidate_01`）。

### 3. 第三层：跨平台增量汇聚与最终时间线重排 (`TimelineReconciler`)
- **全局确定性重排（Global Deterministic Reordering）**：
  - 当任意绑定平台有新消息更新时，`reconcile` 拉取该节点名下所有平台的 `pool.json`；
  - 以 `(timestamp, platform, msg_uid)` 为复合排序键执行多路归并重排（Multi-way Merge-Sort），解决跨平台并发消息或延迟到达批次的乱序问题；
  - 自动统计同一会话窗口内的**跨平台无缝切换次数（`cross_platform_switches`）**，输出重排后的统一时间线切片 `shards/unified_timeline_shard.json` 及下游分析所需的 `meta_shard.json`、`session_shard.json`、`slice_shard.json`。

---

## 三、 分布式分析节点链（单人去滤镜 + 多人精力分配）

| 节点名称 | 输入状态 | 输出状态 | 核心职责 |
| :--- | :--- | :--- | :--- |
| **`QuantFeatureNode`** | `shards/*.json` | `state/quant_state.json` | 计算表层活跃度评分（`surface_vitality_score`）、投入对称性指数（`symmetry_index`）、主动破冰比、字数投入顺差与回复时延分布 |
| **`DefilterPathologyNode`** | `quant_state.json` + `offline_signals.json` | `state/defilter_state.json` | 执行五维去滤镜校准（广谱社交错觉、公开场合避嫌、货架养鱼心态、借口合群背离、陪伴诉求闪避），计算去滤镜乘数 $\alpha$ 与滤镜水分（`illusion_gap`） |
| **`JEVDecisionNode`** | `quant_state.json` + `defilter_state.json` | `state/jev_state.json` | 计算感情发展可能性 $P(\text{Develop})$、真实回报 $V(\text{Return})$、损耗成本 $C(\text{Burn})$ 与净期望值 $\text{Net JEV}$，给出明确精力裁决 |
| **`SolaceRebuilderNode`** | `defilter_state.json` + `jev_state.json` | `state/solace_state.json` | 在复杂内耗或止损场景下，提供去鸡汤的清醒心理抚慰、直觉正名与个人硬核主线能量迁移协议 |
| **`PortfolioAllocatorNode`** | 多个节点的 `state/*.json` + 个人主线基准 | `portfolio_matrix.json` | 横向对比所有候选人与个人成长主线的净期望值和 ROI，计算最优精力分配权重百分比 |
