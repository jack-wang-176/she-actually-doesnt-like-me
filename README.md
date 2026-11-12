# she-actually-doesnt-like-me

她其实不喜欢我：该项目来源于主播失败的感情经历，在一段充满内耗，若近若离的感情中，最有帮助的是抽离客观的视角，直接的告诉你不该继续下去。在很长时间中朋友的劝阻或鼓励只会让我心烦意乱，或是因为他们不了解事情全貌，或是本身他们倾向于让我继续下去，而不是告诉我这是一段糟糕的感情，立即停止投入时间和精力。在几个月中我长时间的处于内耗和纠结状态，让我几乎无法在个人发展中投入太多精力，直到我将聊天记录抽出来丢给 ai 分析，他告诉我停止投入下去，帮我分析了她和我交流过程中的回避和敷衍，直接点出了整个关系的不平等。那个瞬间很痛苦，但更多的是释怀，我想，在那种境地需要有人结合整条发展关系图谱来给出一个答案，因此我将整个内容优化了一下放在上面，希望能帮到和我一样处境的人。

整个项目由 ai 生成和处理

基于事件驱动状态机（FSM）、博弈论信号甄别、贝叶斯动态期望值（Bayesian JEV）与风险平价投资组合（Risk-Parity Portfolio）的分布式关系去滤镜决策框架。

本项目采用严格的零隐私（Zero-PII）与零对话文本（Zero-Chat-Text）设计。分析引擎不读取、不存储、不生成任何真实聊天文本，所有计算均基于边缘脱敏后的纯数值状态切片完成。

## 一、 核心原理

### 1. 导入与分析物理隔离 (Zero-PII Decoupling)
- 原始数据与多平台汇总池（`_private_vault/`、`contacts/`、`data/`）严格保留在本地并通过 `.gitignore` 与 GitHub Actions（`zero_pii_guard.yml`）双重隔离。
- 边缘特征提取器（`feature_vectorizer.py`）将跨平台重排后的消息流单向映射为相对时间窗代号（如 `W01 - W06`）、消息密度比、投入对称度与延迟波动率，剥离真实日期与自然语言文本。

### 2. 关系时间线状态机与拐点检测 (Timeline FSM & CUSUM)
`timeline_fsm_node.py` 通过滑动时间窗与累积和检验（CUSUM Change-Point Detection）定位关键拐点，将关系演进划分为六个标准状态：
- `S0_INITIAL_PROBE`：破冰试探期，双边字数与延迟处于基线建立阶段。
- `S1_ILLUSION_PEAK`：高热滤镜期，高频互动与高秒回掩盖了底层排他性缺失。
- `S2_ASYMMETRIC_DRAIN`：单向失血期，我方主动破冰率 > 72% 或双边对称度 < 0.35，边际回报递减。
- `S3_RUPTURE_FREEZE`：导火索断联期，因线下越界、货架言论或爽约触发断崖式冷却（消息密度比 < 0.15）。
- `S4_INTERMITTENT_LURE`：间歇性强化回捞期，断联后对方因功利性需求（借资源、找搭子）低成本主动破冰，诱发沉没成本幻觉。
- `S5_TERMINAL_PIVOT` / `S5_SYMMETRIC_GROWTH`：终局清醒止损期（识破免责长文与核心陪伴闪避，锁死精力输出）或双向正反馈同频期。

### 3. 博弈论信号甄别与贝叶斯动态 JEV (`defilter_node.py` & `jev_bayesian_node.py`)
在信号博弈（Signaling Game）框架下区分两类信号：
- 廉价信号（Cheap Talk，零机会成本）：打字秒回、口头客套、不承担实质责任的说教长文。
- 高昂信号（Costly Signal，高机会成本）：公开场合自然并肩、核心时间排他性让渡、双向主动破冰与情绪承接。

先验概率 $P_0$ 由表层活跃度映射且受基础社交礼貌上限约束（$P_0 \le 0.55$），通过对数几率模型更新后验真实发展概率 $P(\text{Develop} \mid \mathcal{E})$：

$$\text{Log-Odds}_{\text{post}} = \ln\left(\frac{P_0}{1 - P_0}\right) + \sum_{k} w_k^+ \cdot \mathbb{I}(\text{CostlySignal}_k) - \sum_{m} w_m^- \cdot \mathbb{I}(\text{PathologyFlag}_m)$$

一旦命中公开场合刻意避嫌（`PUBLIC_BOUNDARY_CUT`）、买方货架言论（`SHELF_MENTALITY_EXPOSED`）或回避核心陪伴诉求（`CORE_NEED_EVASION`），后验概率将呈指数级衰减至 `< 5%`，直接输出 `STOP_AND_PIVOT`（立即止损）裁决。

### 4. 当下战术熔断与多人关系夏普比率 (`tactical_advisor_node.py` & `portfolio_node.py`)
- 当下战术协议：根据当前状态机位置与裁决结果，生成 72 小时硬核熔断指令（锁死 0% 主动发起率、阻断二次回捞、100% 算力重路由）与 30 天长周期协议。
- 关系夏普比率（Relationship Sharpe Ratio）：

$$\text{Sharpe}_i = \frac{\mathbb{E}[R_i] - R_{\text{base}}}{\sigma_{\text{volatility}, i}}$$

以个人硬核研发主线（`SELF_CORE_MAINLINE`）作为基准无风险收益率 $R_{\text{base}}$，结合对方忽冷忽热的延迟波动率 $\sigma$ 与最大情绪回撤（MDD），自动将夏普比率为负的节点精力权重砍为 `0.0%`。

## 二、 目录结构

```text
she-actually-doesnt-like-me/
├── .github/workflows/
│   └── zero_pii_guard.yml             # 自动化零隐私防火墙 CI
├── jev_engine/
│   ├── schema/
│   │   └── state_contracts.py         # 分布式节点数据类型契约
│   ├── ingestors/
│   │   ├── multi_platform_sync.py     # 多平台幂等去重、身份映射与全局归并重排
│   │   └── feature_vectorizer.py      # 边缘脱敏特征提取与相对时间窗向量化
│   ├── nodes/
│   │   ├── timeline_fsm_node.py       # 关系阶段状态机与 CUSUM 拐点归因
│   │   ├── defilter_node.py           # 五维去滤镜与博弈论信号甄别
│   │   ├── jev_bayesian_node.py       # 贝叶斯动态 JEV 计算与终局裁决
│   │   ├── tactical_advisor_node.py   # 当下态势定性与 72h/30d 熔断协议
│   │   ├── solace_node.py             # 主体性重建与认知失调拆解
│   │   └── portfolio_node.py          # 关系夏普比率与最大回撤多人精力配置
│   └── pipeline.py                    # 分布式管线编排与报告渲染
├── examples/
│   ├── distributed_nodes/             # 纯数学抽象状态节点示例 (Archetype A/B/C)
│   └── portfolio_output/              # 多人横向对比矩阵输出
└── jev_cli.py                         # 统一命令行入口
```

## 三、 使用方法

### 1. 单人去滤镜评估与当下战术生成
基于纯数值状态节点运行单人诊断，生成包含终局裁决、时间线拐点表与 72 小时执行协议的诊断报告：

```bash
python3 jev_cli.py analyze \
  --nodes-root examples/distributed_nodes \
  --node Archetype_A_BroadSiren \
  --mainline "核心系统架构与硬核技术研发"
```

可通过 `--set-signal` 动态调整线下校准信号：

```bash
python3 jev_cli.py analyze \
  --nodes-root examples/distributed_nodes \
  --node Archetype_A_BroadSiren \
  --set-signal public_distance_cutting=true companionship_evasion=true
```

### 2. 多人横向夏普比率对比与精力分配
聚合多个候选节点并与个人主线基准横向对比，计算最优精力分配权重：

```bash
python3 jev_cli.py portfolio \
  --nodes-root examples/distributed_nodes \
  --output examples/portfolio_output \
  --mainline "核心系统架构与硬核技术研发"
```

### 3. 本地私有数据多平台导入与重排（隔离在 `_private_vault/`）
将本地不同平台的原始记录去重汇总、绑定同一人身份并重排为脱敏切片后进行分析：

```bash
# 步骤 1：单平台增量汇总与去重
python3 jev_cli.py ingest-platform --platform wechat --account acc_01 --source _private_vault/raw_wx.json
python3 jev_cli.py ingest-platform --platform qq --account acc_02 --source _private_vault/raw_qq.json

# 步骤 2：手动绑定跨平台账号至同一分析节点
python3 jev_cli.py link-identity --node Candidate_01 --platform wechat --account acc_01
python3 jev_cli.py link-identity --node Candidate_01 --platform qq --account acc_02

# 步骤 3：跨平台全局时间线归并重排并输出脱敏切片
python3 jev_cli.py reconcile --node Candidate_01

# 步骤 4：对生成的节点运行深度诊断
python3 jev_cli.py analyze --nodes-root _private_vault/contacts --node Candidate_01
```
