#!/usr/bin/env python3
"""Florin step 5-6: deposit FUSD ke Stability Pool + Manage (add/withdraw coll).

  5. approve FUSD -> SP, provideToSP(1000 FUSD, false)
  6. approve SPY -> BO (1 SPY), addColl(1 SPY), withdrawColl(1 SPY)
     (round trip: posisi akhir sama seperti sebelum Manage)
"""
import sys

sys.path.insert(0, "/home/hatch/workspace/florin")
from florin_common import *  # noqa: E402

TROVE_ID = 23144040790677890663749532939310680646351511784076625317485735632441035687281
SP_AMOUNT = 1000 * 10**18
COLL_RT = 1 * 10**18  # 1 SPY untuk demo add/withdraw

acct = load_account()
w3 = connect()
bo = load_abi(w3, BO, BO + ".json")
tm = load_abi(w3, TM, TM + ".json")
sp = load_abi(w3, SP, SP + ".json")
spy = load_abi_json(w3, SPY, ERC20_ABI)
fusd = load_abi_json(w3, FUSD, ERC20_ABI)

print("wallet FUSD:", fusd.functions.balanceOf(WALLET).call() / 1e18)
print("wallet SPY:", spy.functions.balanceOf(WALLET).call() / 1e18)
print("SP deposit saat ini:",
      sp.functions.getCompoundedBoldDeposit(WALLET).call() / 1e18, "FUSD")

# --- 5. Stability Pool ---
allow = fusd.functions.allowance(WALLET, SP).call()
if allow < SP_AMOUNT:
    send_tx(w3, acct, fusd.functions.approve(SP, SP_AMOUNT),
            label="approve FUSD 1000 ke StabilityPool")
send_tx(w3, acct, sp.functions.provideToSP(SP_AMOUNT, False),
        label="provideToSP 1000 FUSD")
print("SP deposit sekarang:",
      sp.functions.getCompoundedBoldDeposit(WALLET).call() / 1e18, "FUSD")
print("wallet FUSD:", fusd.functions.balanceOf(WALLET).call() / 1e18)

# --- 6a. Manage: add 1 SPY ---
allow_spy = spy.functions.allowance(WALLET, BO).call()
if allow_spy < COLL_RT:
    send_tx(w3, acct, spy.functions.approve(BO, COLL_RT),
            label="approve SPY 1 ke BO")
d0 = tm.functions.getLatestTroveData(TROVE_ID).call()
send_tx(w3, acct, bo.functions.addColl(TROVE_ID, COLL_RT),
        label="addColl 1 SPY")
d1 = tm.functions.getLatestTroveData(TROVE_ID).call()
print(f"coll: {d0[1]/1e18} -> {d1[1]/1e18} SPY")

# --- 6b. Manage: withdraw 1 SPY ---
send_tx(w3, acct, bo.functions.withdrawColl(TROVE_ID, COLL_RT),
        label="withdrawColl 1 SPY")
d2 = tm.functions.getLatestTroveData(TROVE_ID).call()
print(f"coll: {d1[1]/1e18} -> {d2[1]/1e18} SPY")
print("wallet SPY:", spy.functions.balanceOf(WALLET).call() / 1e18)

# --- status akhir ---
pf = load_abi(w3, PRICE_FEED, "0xb7dc3a2596e9a0571b6e104d2f1a3d35b0653862.json")
price = pf.functions.lastGoodPrice().call()
debt, coll = d2[0], d2[1]
eq = coll * price // 10**18 - debt
print("=== STATUS AKHIR ===")
print(f"trove: coll {coll/1e18} SPY | debt {debt/1e18} FUSD | "
      f"leverage {(coll*price//10**18)/eq:.3f}x | "
      f"ICR {tm.functions.getCurrentICR(TROVE_ID, price).call()/1e18:.3f}")
print(f"SP deposit: {sp.functions.getCompoundedBoldDeposit(WALLET).call()/1e18} FUSD")
print(f"wallet: SPY {spy.functions.balanceOf(WALLET).call()/1e18} | "
      f"FUSD {fusd.functions.balanceOf(WALLET).call()/1e18} | "
      f"ETH {w3.eth.get_balance(WALLET)/1e18}")
