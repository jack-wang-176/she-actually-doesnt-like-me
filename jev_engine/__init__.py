"""
JEV-Mirror (去滤镜关系期望值评估与分布式 Agent 分析框架)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
核心理念：
1. 导入与分析解耦 (Decoupled Ingestion & Analysis)：
   导入层仅负责将原始聊天记录转化为标准化、脱敏的分布式切片 (Distributed Shards)，
   分析层绝不直接耦合原始数据库或聊天导出工具。
2. 分布式节点抽象 (Distributed Node Abstraction)：
   每个联系人是一个独立的自治状态节点 (Autonomous Contact Node)，通过标准 JSON 状态描述符
   (quant_state -> defilter_state -> jev_state -> solace_state) 逐级抽象，最后由
   PortfolioAllocatorNode 在不读取任何原始消息的前提下完成多人横向精力分配与回报率评估。
"""

__version__ = "1.0.0"
__all__ = ["ingestors", "nodes", "pipeline"]
