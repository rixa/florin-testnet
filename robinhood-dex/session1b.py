#!/usr/bin/env python3
"""Sesi pertama DEX, lanjutan (22 Nov 2026): wrap + approve WETH sudah
sukses di session1.py; swap pertama gagal simulasi karena ABI router
salah (7-field SwapRouter02 vs 8-field v1 dengan deadline). Sudah
diperbaiki di dex_common.py. Langkah ini:
1. swap 0.001 WETH -> TSLA (minOut 95% quote)
2. approve TSLA -> router (bila perlu)
3. swap 0.05 TSLA -> WETH (minOut 95% quote)
"""
import sys

from web3 import Web3

sys.path.insert(0, "/home/hatch/workspace/robinhood-dex")
import dex_common as dx

w3 = dx.connect()
acct = dx.load_account()
print(f"chainId OK: {w3.eth.chain_id} | wallet: {acct.address}")

before = dx.balances(w3)
dx.print_balances(before, "Saldo sebelum lanjutan")
if before["ETH"] < Web3.to_wei(0.001, "ether"):
    print("ALERT: ETH < 0.001 — berhenti tanpa aksi.")
    sys.exit(1)

results = {}
wrap_amt = Web3.to_wei(0.001, "ether")
assert before["WETH"] >= wrap_amt, "WETH kurang — wrap belum terjadi?"

# 1. Swap 0.001 WETH -> TSLA
results["swap_weth_tsla"] = dx.swap_exact_in(
    w3, acct, dx.WETH, dx.TOKENS["TSLA"], wrap_amt,
    label="swap 0.001 WETH -> TSLA")

# 2. Approve router untuk TSLA (bila perlu)
tsla_back = int(0.05 * 10**18)
r = dx.ensure_allowance(w3, acct, dx.TOKENS["TSLA"], dx.ROUTER,
                        tsla_back, "TSLA->router")
if r:
    results["approve_tsla"] = r

# 3. Swap 0.05 TSLA -> WETH
results["swap_tsla_weth"] = dx.swap_exact_in(
    w3, acct, dx.TOKENS["TSLA"], dx.WETH, tsla_back,
    label="swap 0.05 TSLA -> WETH")

after = dx.balances(w3)
dx.print_balances(after, "Saldo setelah sesi")
print("--- Ringkasan tx ---")
for k, v in results.items():
    print(f"  {k}: {v['hash']} (gas {v['gasUsed']}, block {v['block']})")
