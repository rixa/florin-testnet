#!/usr/bin/env python3
"""Florin step 1-2: approve SPY + openTrove (100 SPY, 2000 FUSD @ 5%).

Template mengikuti openTrove nyata yang sukses hari ini (tx 0xa3a8cc34...):
coll 100 SPY, debt 2000 FUSD (minimum), rate 5%, maxUpfrontFee 10 FUSD.
Hints dihitung via HintHelpers + SortedTroves (cara yang dipakai frontend).
"""
import json
import random
import sys

sys.path.insert(0, "/home/hatch/workspace/florin")
from florin_common import *  # noqa: E402

COLL = 100 * 10**18
DEBT = 2000 * 10**18
RATE = 5 * 10**16  # 5% per tahun
MAX_FEE = 10 * 10**18  # prediksi fee 2,63 FUSD; batas 10 FUSD
GAS_COMP = 10**15  # 0,001 WETH — liquidator compensation, ditarik openTrove
# (terbukti dari token transfer tx openTrove nyata 0xa3a8cc34...: WETH 0,001
# dari user ke GasPool 0xdc6041cc...). WETH harus di-wrap + approve dulu.
WETH = "0x7943e237c7F95DA44E0301572D358911207852Fa"

WETH_ABI = json.loads(
    '[{"constant":false,"inputs":[],"name":"deposit","outputs":[],'
    '"payable":true,"stateMutability":"payable","type":"function"},'
    '{"constant":true,"inputs":[{"name":"a","type":"address"}],'
    '"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],'
    '"type":"function"},'
    '{"constant":false,"inputs":[{"name":"s","type":"address"},'
    '{"name":"v","type":"uint256"}],"name":"approve",'
    '"outputs":[{"name":"","type":"bool"}],"type":"function"},'
    '{"constant":true,"inputs":[{"name":"o","type":"address"},'
    '{"name":"s","type":"address"}],"name":"allowance",'
    '"outputs":[{"name":"","type":"uint256"}],"type":"function"}]')

acct = load_account()
w3 = connect()
bo = load_abi(w3, BO, BO + ".json")
tm = load_abi(w3, TM, TM + ".json")
st = load_abi(w3, ST, "sortedtroves.json")
hh = load_abi(w3, HH, HH + ".json")
spy = load_abi_json(w3, SPY, ERC20_ABI)
fusd = load_abi_json(w3, FUSD, ERC20_ABI)
weth = load_abi_json(w3, WETH, WETH_ABI)

print("SPY balance:", spy.functions.balanceOf(WALLET).call() / 1e18)
print("FUSD balance:", fusd.functions.balanceOf(WALLET).call() / 1e18)
print("ETH balance:", w3.eth.get_balance(WALLET) / 1e18)
assert spy.functions.balanceOf(WALLET).call() >= COLL, "SPY tidak cukup"

# --- hints ---
seed = random.getrandbits(256)
approx = hh.functions.getApproxHint(0, RATE, 300, seed).call()
approx_hint = approx[0]  # getApproxHint returns (hintId, diff, latestRandomSeed)
upper, lower = st.functions.findInsertPosition(RATE, approx_hint, approx_hint).call()
print("approxHint:", approx_hint)
print("upperHint:", upper)
print("lowerHint:", lower)
print("validInsertPosition:",
      st.functions.validInsertPosition(RATE, upper, lower).call())

# --- ownerIndex + troveId (Liquity V2: troveId = keccak256(owner, ownerIndex)) ---
owner_index = random.getrandbits(63)
trove_id = Web3.solidity_keccak(["address", "uint256"], [WALLET, owner_index])
trove_id_int = int.from_bytes(trove_id, "big")
print("ownerIndex:", owner_index)
print("troveId:", trove_id_int)

fee_pred = hh.functions.predictOpenTroveUpfrontFee(0, DEBT, RATE).call()
print("predicted upfront fee:", fee_pred / 1e18, "FUSD")

# --- 0. WETH gas compensation: wrap 0,001 ETH + approve BO ---
weth_bal = weth.functions.balanceOf(WALLET).call()
print("WETH balance:", weth_bal / 1e18)
if weth_bal < GAS_COMP:
    send_tx(w3, acct, weth.functions.deposit(), value=GAS_COMP,
            label="wrap 0,001 ETH -> WETH")
weth_allow = weth.functions.allowance(WALLET, BO).call()
print("WETH allowance ke BO:", weth_allow / 1e18)
if weth_allow < GAS_COMP:
    send_tx(w3, acct, weth.functions.approve(BO, GAS_COMP),
            label="approve WETH 0,001 ke BO")

# --- 1. approve SPY -> BorrowerOperations (tepat 100 SPY) ---
allow = spy.functions.allowance(WALLET, BO).call()
print("allowance saat ini:", allow / 1e18, "SPY")
if allow < COLL:
    send_tx(w3, acct, spy.functions.approve(BO, COLL), label="approve SPY 100")
else:
    print("allowance sudah cukup, skip approve")

# --- 2. openTrove ---
fn = bo.functions.openTrove(
    WALLET, owner_index, COLL, DEBT, upper, lower, RATE, MAX_FEE,
    "0x0000000000000000000000000000000000000000",
    "0x0000000000000000000000000000000000000000",
    "0x0000000000000000000000000000000000000000",
)
send_tx(w3, acct, fn, label="openTrove 100 SPY / 2000 FUSD @5%")

# --- verifikasi ---
data = tm.functions.getLatestTroveData(trove_id_int).call()
print("trove status:", tm.functions.getTroveStatus(trove_id_int).call(),
      "(0=none, 1=active, 2=closed, 3=liquidated)")
print("latestTroveData (raw):", data)
print("trove debt:", data[0] / 1e18, "FUSD | coll:", data[1] / 1e18,
      "SPY | rate:", data[4] / 1e16, "%")
print("wallet SPY:", spy.functions.balanceOf(WALLET).call() / 1e18)
print("wallet FUSD:", fusd.functions.balanceOf(WALLET).call() / 1e18)
print("wallet WETH:", weth.functions.balanceOf(WALLET).call() / 1e18)
print("wallet ETH:", w3.eth.get_balance(WALLET) / 1e18)
print("TROVE_ID:", trove_id_int)
print("OWNER_INDEX:", owner_index)
