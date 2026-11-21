#!/usr/bin/env python3
"""Florin: sesi harian ringan (1x sehari, 1-2 tx gas-only).

Rotasi 4 hari berdasarkan hari dalam tahun — semua aksi gas-only, tanpa
biaya tambahan (tanpa ubah interest rate, tanpa leverage baru, tanpa pinjam):
  hari 0: SP cycle — withdraw 10 FUSD dari SP lalu deposit 10 FUSD lagi
  hari 1: collateral round trip — addColl 0,1 SPY lalu withdrawColl 0,1 SPY
  hari 2: klaim yield SP — provideToSP(1 FUSD, doClaim=True)
  hari 3: campuran — withdraw 5 FUSD dari SP + addColl 0,1 SPY

Pengaman (hard stop, tanpa aksi on-chain):
  - trove tidak aktif (ke-liquidasi / ke-close) -> ALERT, berhenti
  - ICR < 1.15 -> ALERT, skip farming hari itu (deleverage butuh keputusan user)
  - saldo ETH < 0.001 -> ALERT, skip (gas menipis)
Log tiap run: hidden_files goal testnet-wallet (florin-daily-log.jsonl).
Pakai --dry-run untuk simulasi saja (eth_call, tanpa kirim tx).
"""
import json
import os
import sys
from datetime import date

sys.path.insert(0, "/home/hatch/workspace/florin")
from florin_common import *  # noqa: E402

TROVE_ID = 23144040790677890663749532939310680646351511784076625317485735632441035687281
ICR_ALERT = 1.15
ETH_MIN = 0.001
LOG_PATH = ("/home/hatch/workspace/goals/testnet-wallet-for-sepolia-and-base-sepolia-tasks"
            "/hidden_files/florin-daily-log.jsonl")
DRY = "--dry-run" in sys.argv

acct = load_account()
w3 = connect()
bo = load_abi(w3, BO, BO + ".json")
tm = load_abi(w3, TM, TM + ".json")
sp = load_abi(w3, SP, SP + ".json")
spy = load_abi_json(w3, SPY, ERC20_ABI)
fusd = load_abi_json(w3, FUSD, ERC20_ABI)
pf = load_abi(w3, PRICE_FEED, "0xb7dc3a2596e9a0571b6e104d2f1a3d35b0653862.json")

log = {"date": date.today().isoformat(), "dry_run": DRY, "actions": []}


def act(label, fn):
    """Kirim tx (atau simulasi saja di dry-run); catat hasilnya."""
    try:
        if DRY:
            fn.call({"from": WALLET})
            print(f"[DRY-RUN OK] {label} (simulasi lolos)")
            log["actions"].append({"label": label, "tx": None, "dry_run": True})
            return True
        r = send_tx(w3, acct, fn, label=label)
        log["actions"].append({"label": label, "tx": r["hash"]})
        return True
    except (Exception, SystemExit) as e:  # send_tx memanggil sys.exit(1) saat gagal
        print(f"[GAGAL] {label}: {e}")
        log["actions"].append({"label": label, "tx": None, "error": str(e)[:200]})
        return False


def ensure_allowance(token, spender, amount, label):
    if token.functions.allowance(WALLET, spender).call() < amount:
        act(label, token.functions.approve(spender, amount))


def finish(status):
    log["status"] = status
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(log) + "\n")
    print("STATUS:", status)
    sys.exit(0 if status in ("done", "dry_run_ok") else 1)


# --- pengaman ---
d = tm.functions.getLatestTroveData(TROVE_ID).call()
status = tm.functions.getTroveStatus(TROVE_ID).call()
price = pf.functions.lastGoodPrice().call()
debt, coll = d[0], d[1]
icr = tm.functions.getCurrentICR(TROVE_ID, price).call() / 1e18 if status == 1 else 0
eth_bal = w3.eth.get_balance(WALLET) / 1e18
log.update({"trove_status": status, "icr": round(icr, 4),
            "coll_spy": coll / 1e18, "debt_fusd": debt / 1e18,
            "spy_price": price / 1e18, "eth": eth_bal,
            "sp_deposit": sp.functions.getCompoundedBoldDeposit(WALLET).call() / 1e18})
print(f"trove status={status} | coll {coll/1e18} SPY | debt {debt/1e18} FUSD "
      f"| ICR {icr:.3f} | SPY ${price/1e18} | ETH {eth_bal}")

if status != 1:
    print("ALERT: trove tidak aktif lagi (status != 1) — mungkin ke-liquidasi.")
    finish("alert_trove_inactive")
if icr < ICR_ALERT:
    print(f"ALERT: ICR {icr:.3f} di bawah {ICR_ALERT} — farming di-skip, "
          "butuh keputusan user (deleverage / tambah collateral).")
    finish("alert_icr_low")
if eth_bal < ETH_MIN:
    print(f"ALERT: saldo ETH {eth_bal} di bawah {ETH_MIN} — gas menipis.")
    finish("alert_low_eth")

# --- rotasi aksi ---
day = date.today().timetuple().tm_yday % 4
print(f"rotasi hari ini: {day}")
if day == 0:
    act("withdrawFromSP 10 FUSD", sp.functions.withdrawFromSP(10 * 10**18, False))
    ensure_allowance(fusd, SP, 10 * 10**18, "approve FUSD 10 ke SP")
    act("provideToSP 10 FUSD", sp.functions.provideToSP(10 * 10**18, False))
elif day == 1:
    ensure_allowance(spy, BO, 10**17, "approve SPY 0.1 ke BO")
    act("addColl 0.1 SPY", bo.functions.addColl(TROVE_ID, 10**17))
    act("withdrawColl 0.1 SPY", bo.functions.withdrawColl(TROVE_ID, 10**17))
elif day == 2:
    ensure_allowance(fusd, SP, 1 * 10**18, "approve FUSD 1 ke SP")
    act("provideToSP 1 FUSD + claim", sp.functions.provideToSP(1 * 10**18, True))
else:
    act("withdrawFromSP 5 FUSD", sp.functions.withdrawFromSP(5 * 10**18, False))
    ensure_allowance(spy, BO, 10**17, "approve SPY 0.1 ke BO")
    act("addColl 0.1 SPY", bo.functions.addColl(TROVE_ID, 10**17))

finish("dry_run_ok" if DRY else "done")
