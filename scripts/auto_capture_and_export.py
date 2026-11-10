#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/auto_capture_and_export.py
一键抓取密钥、解密、持久化备份并批量导出一个或多个女生聊天记录到 contacts/<备注名>/
用法:
  python scripts/auto_capture_and_export.py "女生A备注" "女生B备注"
"""

import sys
import time
import shutil
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
SIWX_DIR = WORKSPACE / "SIWX"
PYTHON_BIN = WORKSPACE / ".venv" / "bin" / "python"
KEYSTORE_BACKUP_DIR = WORKSPACE / "data" / "keystore"

sys.path.insert(0, str(SIWX_DIR))
from siwx import keystore


def backup_keys():
    k_path = keystore.store_path()
    if k_path.is_file():
        KEYSTORE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_dest = KEYSTORE_BACKUP_DIR / "keystore_backup.json"
        shutil.copy2(k_path, backup_dest)
        print(f"[✓] 密钥已长久备份至: {backup_dest}")
        return True
    return False


def check_keystore():
    store = keystore.load()
    return len(store) if store else 0


def run_step(cmd_list, desc):
    print(f"\n[*] 正在执行: {desc}")
    res = subprocess.run(cmd_list)
    return res.returncode == 0


def main():
    targets = sys.argv[1:]
    if not targets:
        print("用法: python scripts/auto_capture_and_export.py <联系人备注1> [联系人备注2 ...]")
        print("示例: python scripts/auto_capture_and_export.py \"女生A\" \"女生B\"")
        return 1

    print("=" * 64)
    print(f" 微信密钥捕获、数据库解密与多女生聊天归档助手 (目标: {', '.join(targets)}) ")
    print("=" * 64)

    current_keys = check_keystore()
    if current_keys > 0:
        print(f"[+] 当前本地密钥库已有 {current_keys} 条已验证密钥！无需重新抓取。")
        backup_keys()
    else:
        print("[!] 当前密钥库为空，需在微信登录期间捕获 passphrase。")
        subprocess.run(["killall", "WeChat"], capture_output=True)
        time.sleep(1)
        subprocess.run(["open", "/Applications/WeChat.app"])

        wechat_pid = None
        for _ in range(15):
            res = subprocess.run(["pgrep", "-x", "WeChat"], capture_output=True, text=True)
            pids = [int(p) for p in res.stdout.split() if p.strip().isdigit()]
            if pids:
                wechat_pid = pids[0]
                break
            time.sleep(1)

        if not wechat_pid:
            print("[-] 未能检测到微信进程启动，请手动打开微信后再试。")
            return 1

        print(f"[+] 检测到微信已启动 (PID={wechat_pid})，请在 60 秒内点击确认登录微信...")
        subprocess.run([str(PYTHON_BIN), str(SIWX_DIR / "run.py"), "keys", "extract"])

        if check_keystore() == 0:
            print("\n[-] 本次未捕获到密钥，请重试。")
            return 1
        backup_keys()

    # 2. 数据库解密
    run_step([str(PYTHON_BIN), str(SIWX_DIR / "run.py"), "decrypt"], "解密微信本地数据库")

    # 3. 逐个导出联系人到 contacts/<备注名>/raw/ 并运行量化分析
    for target in targets:
        run_step(
            [str(PYTHON_BIN), str(WORKSPACE / "scripts" / "export_contact.py"), target, "--fmt", "both"],
            f"导出「{target}」聊天记录与初始化档案"
        )
        run_step(
            [str(PYTHON_BIN), str(WORKSPACE / "scripts" / "quant_slicer.py"), "--contact", target],
            f"生成「{target}」量化体检与高能切片"
        )

    backup_keys()
    print("\n[✓] 全部联系人导出与初始化分析已完成！请前往 contacts/ 目录查看。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
