#!/usr/bin/env python3
"""Sesi pertama DEX Robinhood Testnet (22 Nov 2026):
1. wrap 0.001 ETH -> WETH
2. swap 0.001 WETH -> TSLA (minOut 95% quote)
3. swap 0.05 TSLA -> WETH (minOut 95% quote)
Setiap tx disimulasi dulu; gagal simulasi = berhenti, tidak retry.
"""
import sys

from web3 import Web3

sys.path.insert(0, "/home/hatch/workspace/robinhood-dex")
import dex_common as dx

w3 = dx.connect()
acct = dx.load_account()
print(f"chainId OK: {w3.eth.chain_id} | wallet: {acct.address}")

before = dx.balances(w3)
dx.print_balances(before, "Saldo sebelum sesi")
if before["ETH"] < Web3.to_wei(0.001, "ether"):
    print("ALERT: ETH < 0.001 — berhenti tanpa aksi.")
    sys.exit(1)

results = {}

# 1. Wrap 0.001 ETH -> WETH
weth = dx.contract(w3, dx.WETH, dx.WETH_ABI)
wrap_amt = Web3.to_wei(0.001, "ether")
results["wrap"] = dx.send_tx(w3, acct, weth.functions.deposit(),
                             value=wrap_amt, label="wrap 0.001 ETH -> WETH")

# 2a. Approve router untuk WETH (bila perlu)
r = dx.ensure_allowance(w3, acct, dx.WETH, dx.ROUTER, wrap_amt, "WETH->router")
if r:
    results["approve_weth"] = r

# 2b. Swap 0.001 WETH -> TSLA
results["swap_weth_tsla"] = dx.swap_exact_in(
    w3, acct, dx.WETH, dx.TOKENS["TSLA"], wrap_amt,
    label="swap 0.001 WETH -> TSLA")

# 3a. Approve router untuk TSLA (bila perlu)
tsla_back = int(0.05 * 10**18)
r = dx.ensure_allowance(w3, acct, dx.TOKENS["TSLA"], dx.ROUTER,
                        tsla_back, "TSLA->router")
if r:
    results["approve_tsla"] = r

# 3b. Swap 0.05 TSLA -> WETH
results["swap_tsla_weth"] = dx.swap_exact_in(
    w3, acct, dx.TOKENS["TSLA"], dx.WETH, tsla_back,
    label="swap 0.05 TSLA -> WETH")

after = dx.balances(w3)
dx.print_balances(after, "Saldo setelah sesi")
print("--- Ringkasan tx ---")
for k, v in results.items():
    print(f"  {k}: {v['hash']} (gas {v['gasUsed']}, block {v['block']})")
