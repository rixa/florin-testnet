#!/usr/bin/env python3
"""Read-only verification: balances, contract code, pools, quote."""
import sys

from web3 import Web3

sys.path.insert(0, "/home/hatch/workspace/robinhood-dex")
import dex_common as dx

w3 = dx.connect()
print(f"chainId OK: {w3.eth.chain_id}")

print("--- Kontrak (punya code?) ---")
for name, addr in [("WETH", dx.WETH), ("Factory", dx.FACTORY),
                   ("Router", dx.ROUTER), ("QuoterV2", dx.QUOTER),
                   ("PositionManager", dx.POSITION_MANAGER)]:
    print(f"  {name:16}: {dx.has_code(w3, addr)}  {addr}")
for sym, addr in dx.TOKENS.items():
    print(f"  {sym:16}: {dx.has_code(w3, addr)}  {addr}")

dx.print_balances(dx.balances(w3), "Saldo awal")

print("--- Pool WETH/x (fee 0.3%) ---")
for sym in dx.PAIRS:
    pool = dx.get_pool(w3, dx.WETH, dx.TOKENS[sym])
    if pool == "0x0000000000000000000000000000000000000000":
        print(f"  WETH/{sym}: TIDAK ADA POOL")
        continue
    pc = dx.contract(w3, pool, dx.POOL_ABI)
    liq = pc.functions.liquidity().call()
    slot0 = pc.functions.slot0().call()
    print(f"  WETH/{sym}: {pool} liquidity={liq} unlocked={slot0[6]}")

print("--- Quote 0.001 WETH -> TSLA ---")
amt = Web3.to_wei(0.001, "ether")
q = dx.quote(w3, dx.WETH, dx.TOKENS["TSLA"], amt)
print(f"  quote: 0.001 WETH -> {dx.fmt(q)} TSLA")
print("--- Quote 0.001 WETH -> NFLX ---")
q2 = dx.quote(w3, dx.WETH, dx.TOKENS["NFLX"], amt)
print(f"  quote: 0.001 WETH -> {dx.fmt(q2)} NFLX")
print("--- Quote 0.05 TSLA -> WETH ---")
q3 = dx.quote(w3, dx.TOKENS["TSLA"], dx.WETH, int(0.05 * 10**18))
print(f"  quote: 0.05 TSLA -> {dx.fmt(q3)} WETH")
