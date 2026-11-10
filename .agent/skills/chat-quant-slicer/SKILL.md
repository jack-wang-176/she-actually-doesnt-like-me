---
name: chat-quant-slicer
description: >-
  聊天记录量化统计与高能切片分析 Skill。解析 raw_data/ 下的聊天记录（JSON/CSV/TXT/SQLite），
  统计按周/月的消息频次、双方主动开场比、平均回复时间差、字数投入比、深夜畅聊频次，
  并抽取出升温最快与降温最明显的关键对话切片。
---

# chat-quant-slicer

## 核心职责
1. **数据源标准化**：读取 `raw_data/` 目录中的各类原始聊天记录（MemoTrace、WeChatMsg、SIWX、NapCat、CSV、TXT 等），统一转换为标准消息流。
2. **硬核指标量化计算**：
   - 消息总数与活跃天数。
   - 主动发起话题比例（定义为对话静止超过 2~4 小时后重新发起发言）。
   - 话题终结率（连续对话中最后发送消息的一方）。
   - 回复延迟（平均时延、秒回率 < 30s、轮回率 > 2h）。
   - 字数投入比与长消息频次（单条 > 50 字）。
   - 深夜互动频次（22:00 ~ 02:00 高频窗口）。
   - 表情包、图片与语音占比。
   - 关系热度与时延走势（按周 / 月动态分布）。
3. **高能对话切片抽取**：
   - Top 5 升温关键切片（深夜深聊、高频秒回、长文情绪共鸣）。
   - Top 5 降温/潜在冲突切片（时延陡增、敷衍单字、单向追问断流）。
4. **指标持久化**：
   - 保存量化结果到 `reports/quant_metrics.json`。
   - 生成人类可读报告 `reports/quant_summary.md`。
   - 写入 SQLite 数据库 `data/chat_metrics.db`。

## 执行方法
直接运行量化分析脚本：
```bash
python scripts/quant_slicer.py
```
若需要指定特定文件：
```bash
python scripts/quant_slicer.py --input raw_data/your_chat_file.json
```
