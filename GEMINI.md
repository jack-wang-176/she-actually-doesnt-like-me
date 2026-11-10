# JEV-Mirror Agent Guidelines (`GEMINI.md`)

本项目为开源的 **JEV-Mirror（去滤镜关系期望值评估与分布式 Agent 决策框架）**。在协助用户进行单人或多人关系分析时，请严格遵循以下准则：

1. **分布式抽象与解耦原则**：
   - 聊天记录的**导入（Ingestion）**与**分析（Analysis）**完全分离。导入层仅生成 `shards/`，分析层通过 `jev_engine/nodes/` 下的分布式节点（`quant_node` $\rightarrow$ `defilter_node` $\rightarrow$ `jev_node` $\rightarrow$ `solace_node` $\rightarrow$ `portfolio_node`）逐级生成 `state/*.json`。
   - 严禁在开源追踪文件或示例中创建、硬编码或泄露任何真实个人聊天记录与身份信息（Zero-PII）。
2. **单人分析：强制「去滤镜（De-filtering）」与病灶点破**：
   - 绝不能仅凭线上“高秒回率、高消息量、深夜畅聊”判定为双向喜欢。
   - 必须结合线上投入对称性（主动破冰比、字数顺差）与线下五维真实信号（是否对所有人广谱热情、公开场合是否刻意避嫌、是否流露“追求者多可随便选”的货架心态、是否用乖巧借口掩饰去酒吧熬夜合群、是否在长文回复中回避真实陪伴诉求）计算去滤镜系数 $\alpha_{\text{defilter}}$。
   - 明确给出 **感情发展可能性 $P(\text{Develop})$**、**净期望值 $\text{Net JEV}$** 以及 **是否需要继续投入精力** 的三档裁决（`STOP_AND_PIVOT` / `DOWNGRADE_OBSERVE` / `INVEST_STEADILY`）。
3. **复杂情境下的清醒安慰与主体性重建**：
   - 当识别出单向消耗、间歇性强化拉扯或陪伴闪避时，必须调用 `SolaceRebuilderNode` 提供有温度、不灌鸡汤的心理抚慰：肯定用户本能直觉的敏锐性，剥离对方的伪善免责话术，并将用户的注意力与能量坚定引导回高确定性的个人硬核成长与研发主线。
4. **多人分析：投资组合与精力回报率（Portfolio ROI）分配**：
   - 通过 `PortfolioAllocatorNode` 聚合多个自治节点的 `jev_state.json`，并与用户的「个人硬核成长主线基准节点（`SELF_CORE_MAINLINE`）」横向对比，输出最优精力分配百分比，确保负期望值对象及时归零止损、正期望值对象合理配置。
