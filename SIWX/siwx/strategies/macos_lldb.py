"""Strategy: macOS LLDB breakpoint capture (WeChat 4.1.x).

On macOS WeChat 4.1.x, raw keys are passed to SQLCipher during login/initialization.
When SQLCipher initializes page HMAC keys, it calls CommonCrypto's CCKeyDerivationPBKDF
with rounds=2, passing the 32-byte raw database encryption key as password, and
mac_salt = (salt ^ 0x3a) as salt.

This strategy uses LLDB to attach during WeChat login/startup, capturing:
  1. Direct database encryption keys from CCKeyDerivationPBKDF (rounds=2 or other)
  2. Master passphrase derivations from CCKeyDerivationPBKDF (rounds>=1000)
  3. Raw keys from sqlite3_key / sqlite3_key_v2
Every candidate is immediately verified against page-1 HMAC.
"""
import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path

from siwx import keystore
from siwx.sqlcipher import verify_enc_key

PBKDF2_ITERATIONS = 256000
PBKDF2_DKLEN = 32
PBKDF2_DIGEST = "sha512"


def _version_tuple(v: str):
    """'4.1.8' → (4, 1, 8)；容忍 '4.1.8.106' 与非数字尾巴。"""
    parts = []
    for seg in (v or "").split("."):
        digits = ""
        for ch in seg:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts[:3])


def _wechat_bundle_version():
    """读微信 App Bundle 的版本号。"""
    import plistlib
    candidates = [
        Path("/Applications/WeChat.app/Contents/Info.plist"),
        Path.home() / "Applications" / "WeChat.app" / "Contents" / "Info.plist",
    ]
    for p in candidates:
        try:
            with open(p, "rb") as f:
                v = plistlib.load(f).get("CFBundleShortVersionString")
            if v:
                return str(v)
        except (OSError, ValueError):
            continue
    return None


def _collect_all_page1():
    """收集全机所有微信账号数据库的 salt 与 page1。"""
    try:
        from siwx.discover import find_wechat_data_dirs
        from siwx.sqlcipher import collect_db_files
        all_map = {}
        for _, db_dir in find_wechat_data_dirs():
            for e in collect_db_files(db_dir):
                all_map.setdefault(e.salt_hex, e.page1)
        return all_map
    except Exception:
        return {}


def extract(ctx) -> int:
    """macOS only: LLDB breakpoint to capture raw keys / passphrase."""
    import sys
    if sys.platform != "darwin":
        return 0

    page1_by_salt = ctx["page1_by_salt"]
    key_map = ctx["key_map"]
    attrib = ctx["attrib"]
    log = ctx["log"]
    dbg = ctx.get("dbg", log)

    bundle_ver = _wechat_bundle_version()
    if bundle_ver is not None:
        log(f"[macos_lldb] 微信版本: {bundle_ver}")

    try:
        result = subprocess.run(["lldb", "--version"], capture_output=True, check=True, timeout=10)
        ver = result.stdout.decode("utf-8", errors="replace").strip()[:100]
        log(f"[macos_lldb] lldb 版本: {ver}")
    except FileNotFoundError:
        log("[macos_lldb] 错误: lldb 未安装 (需要 Xcode Command Line Tools)")
        return 0
    except subprocess.TimeoutExpired:
        log("[macos_lldb] 错误: lldb --version 超时")
        return 0
    except subprocess.CalledProcessError as e:
        log(f"[macos_lldb] 错误: lldb 执行失败: {e}")
        return 0

    try:
        result = subprocess.run(["pgrep", "-x", "WeChat"], capture_output=True, text=True)
        pids = [int(p) for p in result.stdout.split() if p.strip().isdigit()]
    except Exception as e:
        log(f"[macos_lldb] 错误: pgrep 失败: {e}")
        pids = []

    if not pids:
        log("[macos_lldb] 错误: 未检测到 WeChat 进程")
        return 0

    log(f"[macos_lldb] WeChat PIDs: {pids}, 需验证 salt: {len(page1_by_salt)}个")

    entry = len(key_map)
    for pid in pids:
        missing_salts = [s for s in page1_by_salt if s not in key_map]
        if not missing_salts:
            break
        log(f"[macos_lldb] PID={pid}: 开始 LLDB 断点捕获 (待验证 {len(missing_salts)} 个 salt)...")
        candidates = _capture_candidates_via_lldb(pid, missing_salts, log, dbg)
        if not candidates:
            log(f"[macos_lldb] PID={pid}: 未捕获到候选密钥")
            continue

        log(f"[macos_lldb] PID={pid}: 捕获到 {len(candidates)} 个密钥调用候选，开始 HMAC 验证...")

        verified_this_pid = 0
        seen_keys = set()

        all_page1 = _collect_all_page1()
        kstore = keystore.load()
        kstore_changed = False

        for src, rounds, key_hex, salt_hex in candidates:
            if key_hex in seen_keys and not salt_hex:
                continue
            seen_keys.add(key_hex)
            try:
                raw_key = bytes.fromhex(key_hex)
            except ValueError:
                continue

            # 1. 针对 CCKeyDerivationPBKDF 解码出的 salt 直接命中验证
            if salt_hex and salt_hex in page1_by_salt and salt_hex not in key_map:
                if verify_enc_key(raw_key, page1_by_salt[salt_hex]):
                    key_map[salt_hex] = key_hex
                    attrib[salt_hex] = f"macos_lldb_{src}_direct"
                    log(f"  [macos_lldb] salt={salt_hex[:16]}… 已验证 direct (key={key_hex[:8]}…)")
                    verified_this_pid += 1

            # 针对全机其它账号的 direct salt 进行登记
            if salt_hex and salt_hex in all_page1 and salt_hex not in kstore:
                if verify_enc_key(raw_key, all_page1[salt_hex]):
                    keystore.insert(kstore, salt_hex, key_hex, f"macos_lldb_global_direct")
                    kstore_changed = True

            # 2. 原始密钥跨库复用验证（对尚未匹配的 salt 逐个验证）
            for s, page1 in page1_by_salt.items():
                if s not in key_map:
                    if verify_enc_key(raw_key, page1):
                        key_map[s] = key_hex
                        attrib[s] = f"macos_lldb_{src}_raw"
                        log(f"  [macos_lldb] salt={s[:16]}… 已验证 raw (key={key_hex[:8]}…)")
                        verified_this_pid += 1

            # 针对全机库跨库验证保存
            for s, page1 in all_page1.items():
                if s not in kstore:
                    if verify_enc_key(raw_key, page1):
                        keystore.insert(kstore, s, key_hex, f"macos_lldb_global_raw")
                        kstore_changed = True

            # 3. 如果 rounds >= 1000 或可能是 master passphrase，尝试 PBKDF2 派生
            iters_to_try = []
            if rounds and rounds >= 1000:
                iters_to_try.append(rounds)
            if 256000 not in iters_to_try:
                iters_to_try.append(256000)

            for iters in iters_to_try:
                for s, page1 in page1_by_salt.items():
                    if s not in key_map:
                        salt_bytes = bytes.fromhex(s)
                        dk = hashlib.pbkdf2_hmac("sha512", raw_key, salt_bytes, iters, 32)
                        if verify_enc_key(dk, page1):
                            dk_hex = dk.hex()
                            key_map[s] = dk_hex
                            attrib[s] = f"macos_lldb_pbkdf2_{iters}"
                            log(f"  [macos_lldb] salt={s[:16]}… 已验证 pbkdf2_{iters} (key={dk_hex[:8]}…)")
                            verified_this_pid += 1

                for s, page1 in all_page1.items():
                    if s not in kstore:
                        salt_bytes = bytes.fromhex(s)
                        dk = hashlib.pbkdf2_hmac("sha512", raw_key, salt_bytes, iters, 32)
                        if verify_enc_key(dk, page1):
                            keystore.insert(kstore, s, dk.hex(), f"macos_lldb_global_pbkdf2_{iters}")
                            kstore_changed = True

            if len(key_map) >= len(page1_by_salt):
                break

        if kstore_changed:
            try:
                keystore.save(kstore)
                log("[macos_lldb] 已同步写入全机密钥库")
            except Exception as e:
                dbg(f"[macos_lldb] 同步保存密钥库失败: {e}")

        log(f"[macos_lldb] PID={pid}: 成功验证 {verified_this_pid} 个密钥")

    found = len(key_map) - entry
    if found:
        log(f"[macos_lldb] 本轮提取完成: +{found} 个密钥已验证通过！")
    return found


def _build_lldb_script(pid: int, target_salts: list) -> str:
    """渲染 LLDB 内嵌 Python 脚本。"""
    target_salts_repr = repr(set(target_salts))
    script = f"""
import lldb, time, sys, traceback

pid = {pid}
target_salts = {target_salts_repr}

def _reg(frame, names):
    for n in names:
        r = frame.FindRegister(n)
        if r and r.IsValid():
            return r.GetValueAsUnsigned()
    return None

def _main():
    debugger = lldb.SBDebugger.Create()
    debugger.SetAsync(False)
    target = debugger.CreateTarget("")
    if not target:
        print("FAIL:CreateTarget")
        return

    error = lldb.SBError()
    process = target.AttachToProcessWithID(debugger.GetListener(), pid, error)
    if error.Fail() or not process.IsValid():
        print(f"FAIL:Attach:{{error}}")
        return

    bp_key = target.BreakpointCreateByName("sqlite3_key")
    bp_v2 = target.BreakpointCreateByName("sqlite3_key_v2")
    bp_cc = target.BreakpointCreateByName("CCKeyDerivationPBKDF")
    n_loc = (bp_key.GetNumLocations() + bp_v2.GetNumLocations() + bp_cc.GetNumLocations())

    if n_loc == 0:
        for mod in target.module_iter():
            for fn in ["sqlite3_key", "sqlite3_key_v2"]:
                try:
                    sc_list = mod.FindSymbols(fn)
                except Exception as e:
                    print(f"SYMERR:{{fn}}:{{type(e).__name__}}: {{e}}")
                    continue
                if not sc_list:
                    continue
                for i in range(sc_list.GetSize()):
                    sym = sc_list.GetContextAtIndex(i).symbol
                    if not sym:
                        continue
                    sa = sym.addr
                    if sa and sa.IsValid():
                        la = sa.GetLoadAddress(target)
                        if la != lldb.LLDB_INVALID_ADDRESS:
                            target.BreakpointCreateByAddress(la)
                            n_loc += 1

    print(f"BP:{{n_loc}}")
    if n_loc == 0:
        try:
            process.Detach()
        except Exception as e:
            print(f"WARN:DetachFail:{{type(e).__name__}}: {{e}}")
        print("FAIL:NoSymbol")
        return

    debugger.SetAsync(True)
    listener = debugger.GetListener()
    process.Continue()

    deadline = time.time() + 60
    dead = False
    hits = 0
    captured_salts = set()
    last_hit_time = 0
    ev = lldb.SBEvent()

    while time.time() < deadline and not dead:
        while listener.WaitForEvent(1, ev):
            if lldb.SBProcess.EventIsProcessEvent(ev):
                st = lldb.SBProcess.GetStateFromEvent(ev)
                if st in (lldb.eStateExited, lldb.eStateCrashed,
                          lldb.eStateDetached, lldb.eStateUnloaded):
                    dead = True
                    print(f"PROCESS_DEAD:{{st}}")
                    break
        if dead:
            break
        if process.GetState() != lldb.eStateStopped:
            # 捕获到目标后若爆发期结束 (4 秒静默) 提前退出，无需死等 60 秒
            if len(captured_salts) > 0 and last_hit_time > 0 and (time.time() - last_hit_time) >= 4.0:
                print(f"BURST_DONE:{{len(captured_salts)}}")
                break
            continue

        for thread in process:
            if thread.GetStopReason() != lldb.eStopReasonBreakpoint:
                continue
            hits += 1
            stop_id = thread.GetStopReasonDataAtIndex(0)
            frame = thread.GetFrameAtIndex(0)

            if stop_id == bp_cc.GetID():
                pw = _reg(frame, ["x1", "rsi"])
                plen = _reg(frame, ["x2", "rdx"])
                salt_ptr = _reg(frame, ["x3", "rcx"])
                salt_len = _reg(frame, ["x4", "r8"])
                rounds = _reg(frame, ["x6"])
                if rounds is None:
                    sp = _reg(frame, ["rsp"])
                    if sp:
                        rounds = process.ReadUnsignedFromMemory(sp + 8, 8, error)
                if rounds is not None:
                    rounds &= 0xFFFFFFFF
                if salt_len is not None:
                    salt_len &= 0xFFFFFFFF

                if plen == 32 and pw:
                    mem_err = lldb.SBError()
                    data = process.ReadMemory(pw, 32, mem_err)
                    if not mem_err.Fail() and len(data) == 32:
                        key_hex = data.hex()
                        salt_hex = ""
                        if salt_ptr and salt_len == 16:
                            sdata = process.ReadMemory(salt_ptr, 16, mem_err)
                            if not mem_err.Fail() and len(sdata) == 16:
                                db_salt = bytes([b ^ 0x3a for b in sdata]).hex()
                                salt_hex = db_salt
                        print(f"CANDIDATE:cc:{{rounds}}:{{key_hex}}:{{salt_hex}}")
                        last_hit_time = time.time()
                        if salt_hex:
                            captured_salts.add(salt_hex)
                else:
                    print(f"HIT:cc rounds={{rounds}} plen={{plen}} pw={{bool(pw)}}")

            elif stop_id in (bp_key.GetID(), bp_v2.GetID()):
                is_v2 = (stop_id == bp_v2.GetID())
                if is_v2:
                    pKey_val = _reg(frame, ["rdx", "x2"])
                    nKey_val = _reg(frame, ["rcx", "x3"])
                else:
                    pKey_val = _reg(frame, ["rsi", "x1"])
                    nKey_val = _reg(frame, ["rdx", "x2"])
                if nKey_val is not None:
                    nKey_val &= 0xFFFFFFFF
                if pKey_val and nKey_val == 32:
                    mem_err = lldb.SBError()
                    data = process.ReadMemory(pKey_val, 32, mem_err)
                    if not mem_err.Fail() and len(data) == 32:
                        print(f"CANDIDATE:sqlite3:0:{{data.hex()}}:")
                        last_hit_time = time.time()

        if target_salts and target_salts.issubset(captured_salts):
            print(f"ALL_TARGETS_FOUND:{{len(captured_salts)}}")
            break

        try:
            process.Continue()
        except Exception:
            break

    try:
        if process.IsValid():
            process.Detach()
    except Exception as e:
        print(f"WARN:DetachFail:{{type(e).__name__}}: {{e}}")

try:
    _main()
except SystemExit:
    raise
except Exception as e:
    traceback.print_exc(file=sys.stdout)
    print(f"FAIL:ScriptError:{{type(e).__name__}}: {{e}}")
"""
    return script


def _lldb_cmd_prefix(log) -> list:
    """选择与微信进程架构一致的 lldb 启动前缀。"""
    try:
        r = subprocess.run(["sysctl", "-n", "hw.optional.arm64"],
                           capture_output=True, text=True, timeout=5)
        if r.stdout.strip() != "1":
            return []
        wx = "/Applications/WeChat.app/Contents/MacOS/WeChat"
        if os.path.exists(wx):
            r = subprocess.run(["lipo", "-archs", wx],
                               capture_output=True, text=True, timeout=5)
            if "arm64" not in r.stdout:
                return []
        log("[macos_lldb] Apple Silicon: 强制以 arm64 启动 lldb")
        return ["arch", "-arm64"]
    except Exception:
        return []


def _capture_candidates_via_lldb(pid: int, target_salts: list, log, dbg=None) -> list:
    """运行 LLDB 断点捕获并收集候选密钥。"""
    dbg = dbg or log
    script = _build_lldb_script(pid, target_salts)
    script_path = None
    candidates = []

    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name

        result = subprocess.run(
            _lldb_cmd_prefix(log)
            + ["lldb", "-b", "-O", f"command script import {script_path}"],
            capture_output=True, text=True, timeout=90)

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("CANDIDATE:"):
                parts = line.split(":")
                # CANDIDATE:src:rounds:key_hex:salt_hex
                if len(parts) >= 5:
                    src = parts[1]
                    try:
                        rounds = int(parts[2]) if parts[2] not in ("None", "") else 0
                    except ValueError:
                        rounds = 0
                    key_hex = parts[3].lower()
                    salt_hex = parts[4].lower()
                    candidates.append((src, rounds, key_hex, salt_hex))
            elif line.startswith("ALL_TARGETS_FOUND:"):
                log(f"[macos_lldb] 所有目标 salt ({line.split(':')[1]}个) 均已捕获！")
            elif line.startswith("BURST_DONE:"):
                log(f"[macos_lldb] 登录爆发期捕获结束 (共 {line.split(':')[1]} 个目标库)")
            elif line.startswith("BP:"):
                log(f"[macos_lldb] 断点位置数: {line[3:]}")
            elif line.startswith("FAIL:"):
                log(f"[macos_lldb] LLDB: {line}")
            elif line.startswith("WARN:"):
                log(f"[macos_lldb] ⚠ {line[5:]}")
            elif line.startswith("HIT:"):
                dbg(f"[macos_lldb] {line}")
            elif line.startswith("PROCESS_DEAD:"):
                log(f"[macos_lldb] 微信进程已退出: {line[13:]}")
            elif line.startswith("Traceback") or line.startswith("  File"):
                log(f"[macos_lldb] 脚本异常: {line}")
            else:
                dbg(f"[macos_lldb] {line[:120]}")

        if result.stderr:
            err = result.stderr.strip()[:4000]
            if err:
                dbg(f"[macos_lldb] stderr: {err}")
    except subprocess.TimeoutExpired:
        log("[macos_lldb] 错误: LLDB 捕获超时 (90s)")
    except Exception as e:
        log(f"[macos_lldb] 错误: {e}")
    finally:
        if script_path:
            try:
                os.unlink(script_path)
            except OSError:
                pass

    return candidates
