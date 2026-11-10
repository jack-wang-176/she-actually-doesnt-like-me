#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev_cli.py
she-dont-love-me (去滤镜关系期望值评估与多平台分布式 Agent 决策框架) 统一命令行入口
"""

import argparse
import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE))

from jev_engine.ingestors import (
    IdentityLinkRegistry,
    PlatformAggregator,
    TimelineReconciler,
    build_distributed_shards,
)
from jev_engine.nodes import (
    run_defilter_node,
    run_jev_node,
    run_portfolio_node,
    run_solace_node,
    run_timeline_node,
)
from jev_engine.pipeline import (
    render_portfolio_report,
    render_single_jev_report,
    run_distributed_node_pipeline,
)


def cmd_ingest_platform(args):
    agg = PlatformAggregator(Path(args.platforms_root))
    res = agg.ingest_to_platform_pool(args.platform, args.account, Path(args.source))
    print(
        f"[✓] 单平台汇总更新完成 [{res['platform']}:{res['account_id']}] -> "
        f"新增 {res['added']} 条, 幂等跳过重复 {res['duplicates_skipped']} 条, "
        f"池内总计 {res['total_in_pool']} 条 (水位线 ts={res['watermark_ts']})"
    )
    return 0


def cmd_link_identity(args):
    reg = IdentityLinkRegistry(Path(args.registry))
    entry = reg.bind_account(args.node, args.platform, args.account, alias_note=args.note or "")
    linked_str = ", ".join(f"{a['platform']}:{a['account_id']}" for a in entry["linked_accounts"])
    print(f"[✓] 上层关系连接已更新: 节点 [{args.node}] <-> [{linked_str}]")
    return 0


def cmd_reconcile(args):
    reconciler = TimelineReconciler(
        platforms_root=Path(args.platforms_root),
        registry_path=Path(args.registry),
        nodes_root=Path(args.nodes_root),
    )
    res = reconciler.reconcile_node_timeline(args.node)
    print(
        f"[✓] 跨平台时间线全局重排完成: 节点 [{res['node_id']}] -> "
        f"共重排 {res['total_reordered_messages']} 条消息, "
        f"会话内跨平台切换 {res['cross_platform_switches']} 次, "
        f"分布式切片已输出至: {res['shards_dir']}"
    )
    return 0


def cmd_ingest(args):
    node_root = Path(args.nodes_root) / args.node
    raw_dir = Path(args.raw_dir) if args.raw_dir else (node_root / "raw")
    shards_dir = node_root / "shards"
    res = build_distributed_shards(args.node, raw_dir, shards_dir)
    if not res:
        print(f"[-] 未在 {raw_dir} 中找到可导入的聊天记录文件。")
        return 1
    print(f"[✓] 节点 [{args.node}] 导入完成，分布式切片已生成至: {shards_dir}")
    return 0


def cmd_analyze(args):
    node_root = Path(args.nodes_root) / args.node
    state_dir = node_root / "state"
    shards_dir = node_root / "shards"
    reports_dir = node_root / "reports"

    if args.set_signal:
        state_dir.mkdir(parents=True, exist_ok=True)
        sig_path = state_dir / "offline_signals.json"
        current = json.loads(sig_path.read_text(encoding="utf-8")) if sig_path.exists() else {}
        for item in args.set_signal:
            if "=" in item:
                k, v = item.split("=", 1)
                current[k.strip()] = v.strip().lower() in ("1", "true", "yes", "y")
        sig_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")

    if (shards_dir / "meta_shard.json").exists():
        report_path = run_distributed_node_pipeline(
            args.node,
            node_root,
            ingest_from_raw=not args.skip_ingest,
            personal_mainline=args.mainline,
        )
    elif (state_dir / "quant_state.json").exists():
        run_defilter_node(shards_dir, state_dir)
        run_jev_node(state_dir)
        run_timeline_node(state_dir, personal_mainline=args.mainline)
        run_solace_node(state_dir, personal_mainline=args.mainline)
        report_path = reports_dir / "jev_single_report.md"
        render_single_jev_report(state_dir, report_path)
    else:
        print(f"[-] 节点 [{args.node}] 既无 shards/ 也无预置 state/quant_state.json。")
        return 1

    print(f"[✓] 单人去滤镜 JEV 与时间线评估完成！报告路径: {report_path}")
    return 0


def cmd_portfolio(args):
    nodes_root = Path(args.nodes_root)
    if not nodes_root.is_dir():
        print(f"[-] 节点根目录不存在: {nodes_root}")
        return 1

    state_dirs = []
    for d in sorted(nodes_root.iterdir()):
        if d.is_dir() and not d.name.startswith((".", "_")):
            s_dir = d / "state"
            if (s_dir / "quant_state.json").exists():
                run_defilter_node(d / "shards", s_dir)
                run_jev_node(s_dir)
                run_timeline_node(s_dir, personal_mainline=args.mainline)
                run_solace_node(s_dir, personal_mainline=args.mainline)
                render_single_jev_report(s_dir, d / "reports" / "jev_single_report.md")
                state_dirs.append(s_dir)

    if not state_dirs:
        print(f"[-] 在 {nodes_root} 下未找到任何包含 state/quant_state.json 的分布式节点。")
        return 1

    out_dir = Path(args.output)
    portfolio_data = run_portfolio_node(state_dirs, out_dir, personal_mainline_name=args.mainline)
    out_md = out_dir / "portfolio_allocation_report.md"
    render_portfolio_report(portfolio_data, out_md)
    print(f"[✓] 多人横向对比与精力分配报告已生成: {out_md.resolve()}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="she-dont-love-me: Multi-Platform & Distributed Relationship EV Framework")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plat = sub.add_parser("ingest-platform", help="第一层：单平台总体聊天记录汇总（支持增量去重与水位线更新）")
    p_plat.add_argument("--platform", required=True, help="平台名称 (如 wechat, qq, telegram, imessage, xiaohongshu)")
    p_plat.add_argument("--account", required=True, help="该平台下的对方账号标识")
    p_plat.add_argument("--source", required=True, help="原始聊天记录文件或目录路径")
    p_plat.add_argument("--platforms-root", default="_private_vault/platforms", help="单平台汇总池根目录 (默认隔离在 _private_vault/platforms)")

    p_link = sub.add_parser("link-identity", help="第二层：手动指定上层跨平台关系连接 (绑定同一人的多个平台账号)")
    p_link.add_argument("--node", required=True, help="统一联系人节点代号 (如 Candidate_01)")
    p_link.add_argument("--platform", required=True, help="平台名称 (如 wechat, qq)")
    p_link.add_argument("--account", required=True, help="该平台下的账号标识")
    p_link.add_argument("--note", help="可选备注说明")
    p_link.add_argument("--registry", default="_private_vault/identity_links.json", help="关系连接注册表路径")

    p_rec = sub.add_parser("reconcile", help="第三层：拉取绑定平台池，执行实时增量合并与跨平台最终时间线重排")
    p_rec.add_argument("--node", required=True, help="统一联系人节点代号 (Node_ID)")
    p_rec.add_argument("--platforms-root", default="_private_vault/platforms", help="单平台汇总池根目录")
    p_rec.add_argument("--registry", default="_private_vault/identity_links.json", help="关系连接注册表路径")
    p_rec.add_argument("--nodes-root", default="_private_vault/contacts", help="输出分布式 shards 的节点根目录")

    p_ing = sub.add_parser("ingest", help="快捷单目录导入：将 raw/ 直接转换为分布式切片 (shards/)")
    p_ing.add_argument("--node", required=True, help="联系人节点代号")
    p_ing.add_argument("--nodes-root", default="_private_vault/contacts", help="节点根目录 (默认: _private_vault/contacts)")
    p_ing.add_argument("--raw-dir", help="原始聊天记录目录 (默认: <nodes-root>/<node>/raw)")

    p_ana = sub.add_parser("analyze", help="单人去滤镜 JEV 评估、时间线梳理与当前建议分析")
    p_ana.add_argument("--node", required=True, help="联系人节点代号")
    p_ana.add_argument("--nodes-root", default="examples/distributed_nodes", help="节点根目录 (默认: examples/distributed_nodes)")
    p_ana.add_argument("--skip-ingest", action="store_true", help="跳过原始文件导入，直接基于已有分布式状态计算")
    p_ana.add_argument("--set-signal", nargs="*", help="设置线下校准信号 key=true/false")
    p_ana.add_argument("--mainline", default="核心系统架构与硬核技术研发", help="个人硬核发展主线名称")

    p_port = sub.add_parser("portfolio", help="多人横向 JEV 对比与精力投资组合分配")
    p_port.add_argument("--nodes-root", default="examples/distributed_nodes", help="包含多个自治节点的根目录")
    p_port.add_argument("--output", default="examples/portfolio_output", help="多人对比报告输出目录")
    p_port.add_argument("--mainline", default="核心系统架构与硬核技术研发", help="个人硬核发展主线名称")

    args = parser.parse_args()
    if args.cmd == "ingest-platform":
        return cmd_ingest_platform(args)
    if args.cmd == "link-identity":
        return cmd_link_identity(args)
    if args.cmd == "reconcile":
        return cmd_reconcile(args)
    if args.cmd == "ingest":
        return cmd_ingest(args)
    if args.cmd == "analyze":
        return cmd_analyze(args)
    if args.cmd == "portfolio":
        return cmd_portfolio(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
