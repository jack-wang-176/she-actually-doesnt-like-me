#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/export_contact.py
多联系人微信聊天记录导出与档案初始化工具
用法:
  python scripts/export_contact.py "女生备注或昵称" [html|json|both]
  python scripts/export_contact.py --list  # 列出当前解密库中的所有联系人
"""

import os
import sys
import re
import shutil
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
SIWX_DIR = WORKSPACE / "SIWX"
CONTACTS_DIR = WORKSPACE / "contacts"
TEMPLATES_DIR = WORKSPACE / "templates"

sys.path.insert(0, str(SIWX_DIR))
from siwx import exporter, paths


def get_decrypted_accounts():
    out_root = paths.out_root()
    if not (out_root.is_dir() and any(out_root.glob("*/contact/contact.db"))):
        alt_root = WORKSPACE / "SIWX" / "output"
        if alt_root.is_dir() and any(alt_root.glob("*/contact/contact.db")):
            out_root = alt_root
    if not out_root.is_dir():
        return []
    return [d for d in out_root.iterdir() if d.is_dir() and (d / "contact" / "contact.db").is_file()]


def init_contact_dossier(contact_name):
    """为新联系人创建标准一人一档目录 (raw / profile / reports) 并从 templates 初始化模板"""
    contact_root = CONTACTS_DIR / contact_name
    raw_dir = contact_root / "raw"
    profile_dir = contact_root / "profile"
    reports_dir = contact_root / "reports"

    raw_dir.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    now_str = datetime.now().strftime("%Y-%m-%d")
    template_mapping = {
        TEMPLATES_DIR / "her_profile.template.md": profile_dir / "her_profile.md",
        TEMPLATES_DIR / "interaction_red_flags.template.md": profile_dir / "interaction_red_flags.md",
        TEMPLATES_DIR / "shared_memories.template.md": profile_dir / "shared_memories.md",
        TEMPLATES_DIR / "master_roadmap.template.md": reports_dir / "master_roadmap.md",
    }

    for tpl_path, dest_path in template_mapping.items():
        if tpl_path.is_file() and not dest_path.exists():
            content = tpl_path.read_text(encoding="utf-8")
            content = content.replace("{{CONTACT_NAME}}", contact_name).replace("{{CREATED_AT}}", now_str)
            dest_path.write_text(content, encoding="utf-8")

    return contact_root


def export_target_chat(target_remark, export_fmt="both"):
    accounts = get_decrypted_accounts()
    if not accounts:
        print("[-] 未找到已解密的微信账号数据，请先执行: python SIWX/run.py decrypt")
        return False

    found_chat = None
    matched_display = target_remark
    target_acc_dir = None
    target_account = None

    for acc_dir in accounts:
        acc_wxid = acc_dir.name
        contact_db_path = acc_dir / "contact" / "contact.db"
        try:
            conn = sqlite3.connect(contact_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for tbl in ["contact", "Friend"]:
                if tbl in tables:
                    cols = [c[1] for c in cursor.execute(f"PRAGMA table_info({tbl})").fetchall()]
                    remark_col = "remark" if "remark" in cols else ("Remark" if "Remark" in cols else None)
                    user_col = "username" if "username" in cols else ("m_nsUsrName" if "m_nsUsrName" in cols else "userName")
                    nick_col = "nick_name" if "nick_name" in cols else ("nickname" if "nickname" in cols else ("NickName" if "NickName" in cols else None))

                    for row in cursor.execute(f"SELECT * FROM {tbl}").fetchall():
                        r_dict = dict(row)
                        rem = str(r_dict.get(remark_col, "") or "").strip() if remark_col else ""
                        nick = str(r_dict.get(nick_col, "") or "").strip() if nick_col else ""
                        usr = str(r_dict.get(user_col, "") or "").strip() if user_col else ""

                        norm_target = re.sub(r"\s+", "", target_remark).lower()
                        norm_rem = re.sub(r"\s+", "", rem).lower()
                        norm_nick = re.sub(r"\s+", "", nick).lower()

                        if (norm_target and norm_target in norm_rem) or (norm_target and norm_target in norm_nick) or (norm_target == usr.lower()):
                            found_chat = usr
                            matched_display = rem or nick or target_remark
                            target_acc_dir = acc_dir
                            target_account = acc_wxid
                            print(f"[+] 找到目标联系人: 备注='{rem}', 昵称='{nick}', wxid='{usr}'")
                            break
                if found_chat:
                    break
            conn.close()
        except Exception as e:
            print(f"[-] 查询 {contact_db_path} 失败: {e}")
        if found_chat:
            break

    if not found_chat:
        print(f"[-] 在解密数据中未找到匹配 '{target_remark}' 的联系人。")
        return False

    contact_root = init_contact_dossier(matched_display)
    raw_dir = contact_root / "raw"

    fmts = ["html", "json"] if export_fmt in ("all", "both") else [export_fmt]
    for f in fmts:
        print(f"[*] 正在导出 {f.upper()} 格式聊天记录到 {raw_dir} ...")
        res = exporter.run_export(
            acc_out_dir=target_acc_dir,
            account=target_account,
            chat=found_chat,
            display=matched_display,
            fmt=f,
            want_messages=True,
            want_media=True,
            want_voice=True,
            want_avatars=True,
            export_root=CONTACTS_DIR,
            pack="folder",
            folder_name=f"{matched_display}/raw"
        )
        print(f"[✓] {f.upper()} 导出完成: {res}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Export WeChat chat logs into contacts/<name>/raw/")
    parser.add_argument("contacts", nargs="*", help="一个或多个联系人的备注名/昵称/wxid")
    parser.add_argument("--fmt", default="both", choices=["html", "json", "both"], help="导出格式 (默认: both)")
    parser.add_argument("--init-only", metavar="NAME", help="仅初始化指定联系人的目录结构与档案模板")
    args = parser.parse_args()

    if args.init_only:
        root = init_contact_dossier(args.init_only)
        print(f"[✓] 已初始化联系人档案目录: {root}")
        return 0

    if not args.contacts:
        parser.print_help()
        return 1

    for c in args.contacts:
        export_target_chat(c, export_fmt=args.fmt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
