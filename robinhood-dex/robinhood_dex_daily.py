#!/usr/bin/env python3
"""Sesi harian DEX Robinhood Testnet (Uniswap v3, chainId 46630).

Rotasi 5 hari berdasarkan tanggal: WETH <-> TSLA / NFLX / PLTR / AMZN / AMD.
Tiap sesi: 1-3 tx kecil (wrap bila perlu + swap keluar + swap balik sebagian).

Pengaman (mirip florin_daily.py):
- ETH < 0.001 -> cetak ALERT, keluar tanpa mengirim apa pun.
- ETH < 0.002 saat WETH kurang -> ALERT, keluar (tidak bisa wrap aman).
- Gagal simulasi pada satu aksi -> aksi itu di-skip, TIDAK pernah di-retry.
- --dry-run: simulasi saja, tidak ada tx yang dikirim.

Jalankan: ~/workspace/testnet-wallet/.venv/bin/python robinhood_dex_daily.py [--dry-run]
"""
import argparse
import sys
from datetime import date

from web3 import Web3

sys.path.insert(0, "/home/hatch/workspace/robinhood-dex")
import dex_common as dx

SWAP_WETH = Web3.to_wei(0.001, "ether")   # 0.001 WETH per swap keluar
BACK_AMT = int(0.05 * 10**18)             # 0.05 unit saham swap balik
MIN_ETH = Web3.to_wei(0.001, "ether")
WRAP_RESERVE = Web3.to_wei(0.002, "ether")


def try_action(fn, label):
    """Jalankan satu aksi; gagal simulasi/error -> skip, lanjut ke aksi lain."""
    try:
        return fn()
    except (Exception, SystemExit) as e:
        print(f"[SKIP] {label}: {e}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dry = args.dry_run

    w3 = dx.connect()
    acct = dx.load_account()
    pair = dx.PAIRS[date.today().toordinal() % len(dx.PAIRS)]
    print(f"chainId OK: {w3.eth.chain_id} | wallet: {acct.address}")
    print(f"Pasangan hari ini: WETH <-> {pair}"
          f"{' [DRY-RUN]' if dry else ''}")

    bal = dx.balances(w3)
    dx.print_balances(bal, "Saldo awal")
    if bal["ETH"] < MIN_ETH:
        print("ALERT: ETH < 0.001 — sesi dibatalkan, tidak ada tx dikirim.")
        sys.exit(1)

    stock = dx.TOKENS[pair]

    # 1. Pastikan WETH cukup (wrap 0.001 ETH bila perlu)
    if bal["WETH"] < SWAP_WETH:
        if bal["ETH"] < WRAP_RESERVE:
            print("ALERT: ETH < 0.002 dan WETH kurang — tidak bisa wrap "
                  "aman. Sesi dibatalkan.")
            sys.exit(1)
        weth = dx.contract(w3, dx.WETH, dx.WETH_ABI)
        if dry:
            print("[dry-run] simulasi wrap 0.001 ETH -> WETH...")
            weth.functions.deposit().call(
                {"from": acct.address, "value": SWAP_WETH})
            print("[dry-run] simulasi wrap OK")
        else:
            try_action(
                lambda: dx.send_tx(w3, acct, weth.functions.deposit(),
                                   value=SWAP_WETH,
                                   label="wrap 0.001 ETH -> WETH"),
                "wrap ETH -> WETH")
            bal = dx.balances(w3)

    # 2. Approve router untuk WETH (bila perlu)
    try_action(lambda: dx.ensure_allowance(
        w3, acct, dx.WETH, dx.ROUTER, SWAP_WETH, "WETH->router",
        dry_run=dry), "approve WETH")

    # 3. Swap 0.001 WETH -> saham hari ini
    if dry:
        # Di dry-run, approve tidak benar-benar terkirim, jadi simulasi
        # swap bisa gagal di allowance on-chain — cukup validasi quote.
        try:
            q = dx.quote(w3, dx.WETH, stock, SWAP_WETH)
            print(f"[dry-run] quote 0.001 WETH -> {dx.fmt(q)} {pair} "
                  f"(minOut 95% = {dx.fmt(int(q * 0.95))})")
        except Exception as e:
            print(f"[SKIP] quote WETH->{pair}: {e}")
    else:
        try_action(lambda: dx.swap_exact_in(
            w3, acct, dx.WETH, stock, SWAP_WETH,
            label=f"swap 0.001 WETH -> {pair}"), f"swap WETH->{pair}")

    # 4. Approve router untuk saham (bila perlu) + swap balik 0.05 saham
    try_action(lambda: dx.ensure_allowance(
        w3, acct, stock, dx.ROUTER, BACK_AMT, f"{pair}->router",
        dry_run=dry), f"approve {pair}")
    if dry:
        try:
            q = dx.quote(w3, stock, dx.WETH, BACK_AMT)
            print(f"[dry-run] quote 0.05 {pair} -> {dx.fmt(q)} WETH")
        except Exception as e:
            print(f"[SKIP] quote {pair}->WETH: {e}")
    else:
        try_action(lambda: dx.swap_exact_in(
            w3, acct, stock, dx.WETH, BACK_AMT,
            label=f"swap 0.05 {pair} -> WETH"), f"swap {pair}->WETH")

    dx.print_balances(dx.balances(w3), "Saldo akhir")
    print("Sesi harian selesai.")


if __name__ == "__main__":
    main()
