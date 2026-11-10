# AGENTS.md

## Project Overview: JEV-Mirror

- **JEV-Mirror** is an open-source, privacy-first Agent framework for relationship Expected Value (`JEV`) assessment, single-contact de-filtering (`DefilterPathologyNode`), empathetic agency rebuilding (`SolaceRebuilderNode`), and multi-contact energy portfolio allocation (`PortfolioAllocatorNode`).
- **Decoupled Ingestion & Distributed Abstraction**:
  - **Ingestion Layer (`jev_engine/ingestors/`)**: Converts raw chat files into standardized, isolated distributed shards (`shards/meta_shard.json`, `shards/session_shard.json`, `shards/slice_shard.json`).
  - **Analysis Layer (`jev_engine/nodes/`)**: Operates strictly on distributed JSON state descriptors (`state/*.json`) inside each autonomous node directory—never directly coupling to raw chat files or centralized databases.
- **Strict Zero-PII Policy**:
  - Never include real personal names, nicknames, account IDs (`wxid`), school/company names, or private chat transcripts in any tracked file, documentation, template, or example.
  - All private local nodes under `contacts/*/` and databases under `data/` are git-ignored. Use `examples/distributed_nodes/` (which contains pure, synthetic state descriptors without chat logs) for testing and demonstrations.

## Core CLI Commands

- **Run Single-Contact De-filtered JEV Analysis**:
  ```bash
  python3 jev_cli.py analyze --nodes-root examples/distributed_nodes --node Archetype_A_BroadSiren
  ```
- **Run Multi-Contact Portfolio & Energy Allocation Analysis**:
  ```bash
  python3 jev_cli.py portfolio --nodes-root examples/distributed_nodes --output examples/portfolio_output
  ```
- **Ingest Local Raw Chat Logs into Distributed Shards**:
  ```bash
  python3 jev_cli.py ingest --nodes-root contacts --node "<Node_ID>"
  ```
