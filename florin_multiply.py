#!/usr/bin/env python3
"""Florin step 4: Multiply — loop posisi ke 6x via LeverageZapper.

Alur terbukti dari tx nyata (0x0e76ab76...):
  1. setAddManager(troveId, zapper)
  2. setRemoveManagerWithReceiver(troveId, zapper, zapper)
  3. leverUpTrove((troveId, flashLoanAmount, boldAmount, maxUpfrontFee)), value 0

Quote direplikasi dari frontend (fungsi b di chunk /multiply):
  _ = ceil(r * price / oracleScale)      -> nilai FUSD dari r SPY
  M = ceil(_ * 10050 / 10000)            -> boldAmount (markup 0,5%)
  N = floor(M * oracleScale / price)     -> SPY hasil swap
  syarat: saldo SPY exchange >= r + N
Target leverage 6x dihitung dari ekuitas saat ini, sudah memperhitungkan
markup 0,5% + upfront fee atas utang baru.
"""
import json
import sys

sys.path.insert(0, "/home/hatch/workspace/florin")
from florin_common import *  # noqa: E402

TROVE_ID = 23144040790677890663749532939310680646351511784076625317485735632441035687281
RATE = 5 * 10**16
TARGET_LEV = 6.0

ZAPPER_ABI = json.loads("""[
{"type":"function","name":"leverUpTrove","inputs":[{"name":"params","type":"tuple","components":[
{"name":"troveId","type":"uint256"},{"name":"flashLoanAmount","type":"uint256"},
{"name":"boldAmount","type":"uint256"},{"name":"maxUpfrontFee","type":"uint256"}]}],
"outputs":[],"stateMutability":"nonpayable","type":"function"},
{"type":"function","name":"collToken","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"},
{"type":"function","name":"boldToken","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"},
{"type":"function","name":"borrowerOperations","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"},
{"type":"function","name":"exchange","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"},
{"type":"function","name":"flashLoanProvider","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"}
]""")
EXCH_ABI = json.loads("""[
{"type":"function","name":"priceFeed","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"},
{"type":"function","name":"priceScale","inputs":[],"outputs":[{"type":"uint256"}],"stateMutability":"view"},
{"type":"function","name":"oracleScale","inputs":[],"outputs":[{"type":"uint256"}],"stateMutability":"view"}
]""")
FEED_ABI = json.loads("""[
{"type":"function","name":"latestRoundData","inputs":[],"outputs":[
{"name":"","type":"uint80"},{"name":"","type":"int256"},{"name":"","type":"uint256"},
{"name":"","type":"uint256"},{"name":"","type":"uint80"}],"stateMutability":"view","type":"function"}
]""")

acct = load_account()
w3 = connect()
bo = load_abi(w3, BO, BO + ".json")
tm = load_abi(w3, TM, TM + ".json")
hh = load_abi(w3, HH, HH + ".json")
zapper = load_abi_json(w3, ZAPPER, ZAPPER_ABI)
spy = load_abi_json(w3, SPY, ERC20_ABI)
exch = load_abi_json(w3, EXCHANGE, EXCH_ABI)

# --- verifikasi deployment zapper (cara frontend) ---
assert zapper.functions.collToken().call().lower() == SPY.lower()
assert zapper.functions.boldToken().call().lower() == FUSD.lower()
assert zapper.functions.borrowerOperations().call().lower() == BO.lower()
assert zapper.functions.exchange().call().lower() == EXCHANGE.lower()
assert zapper.functions.flashLoanProvider().call().lower() == EXCHANGE.lower()
print("zapper terverifikasi: coll/bold/BO/exchange/flashLoanProvider cocok")

# --- state trove saat ini ---
d = tm.functions.getLatestTroveData(TROVE_ID).call()
debt, coll = d[0], d[1]
pf = load_abi(w3, PRICE_FEED, "0xb7dc3a2596e9a0571b6e104d2f1a3d35b0653862.json")
price = pf.functions.lastGoodPrice().call()  # 18 desimal
print(f"trove: coll {coll/1e18} SPY | debt {debt/1e18} FUSD | SPY ${price/1e18}")
equity = coll * price // 10**18 - debt
print(f"ekuitas: {equity/1e18} FUSD | leverage saat ini: "
      f"{(coll*price//10**18)/equity:.3f}x | ICR: "
      f"{tm.functions.getCurrentICR(TROVE_ID, price).call()/1e18:.2f}")

# --- quote dari exchange (cara frontend) ---
feed_addr = exch.functions.priceFeed().call()
pscale = exch.functions.priceScale().call()
oscale = exch.functions.oracleScale().call()
feed = load_abi_json(w3, feed_addr, FEED_ABI)
f = feed.functions.latestRoundData().call()[1]
assert f > 0
x = f * pscale  # harga x oracleScale
ex_spy = spy.functions.balanceOf(EXCHANGE).call()
print(f"exchange oracle: ${f/oscale} | SPY di exchange: {ex_spy/1e18}")

# --- hitung r untuk target leverage ---
# biaya: markup swap 0,5% + upfront fee ~ rate*7/365 atas utang baru
fee_frac_num = RATE * 7  # fee = M * RATE * 7 / 365 / 1e18
# E' = E - r*P*(0.005 + fee_frac*1.005); C'*P = 6*E'
# r*P = (6E - C*P) / (1 + 6*(0.005 + fee_frac*1.005))
P = price
CP = coll * P // 10**18
num = int(TARGET_LEV * equity) - CP
fee_frac = RATE * 7 / 365 / 10**18
denom = 1 + TARGET_LEV * (0.005 + fee_frac * 1.005)
r_value = int(num / denom)  # nilai FUSD dari r SPY
r = r_value * 10**18 // P
print(f"r (flash loan SPY): {r/1e18}")
# quote persis cara frontend
quoted = (r * x + oscale - 1) // oscale
M = (quoted * 10050 + 10000 - 1) // 10000
N = M * oscale // x
print(f"quotedInput: {quoted/1e18} FUSD | boldAmount M: {M/1e18} FUSD | "
      f"swapOutput N: {N/1e18} SPY")
assert ex_spy >= r + N, "likuiditas SPY exchange tidak cukup"
fee_pred = hh.functions.predictAdjustTroveUpfrontFee(0, TROVE_ID, M).call()
max_fee = max(int(fee_pred * 1.5), 500 * 10**18)
print(f"prediksi upfront fee: {fee_pred/1e18} FUSD | maxUpfrontFee: "
      f"{max_fee/1e18} FUSD")

# --- 1+2. set manager (skip kalau sudah) ---
add_mgr = bo.functions.addManagerOf(TROVE_ID).call()
mgr, recv = bo.functions.removeManagerReceiverOf(TROVE_ID).call()
print(f"addManager: {add_mgr} | removeManager: {mgr} | receiver: {recv}")
if add_mgr.lower() != ZAPPER.lower():
    send_tx(w3, acct, bo.functions.setAddManager(TROVE_ID, ZAPPER),
            label="setAddManager -> zapper")
if mgr.lower() != ZAPPER.lower() or recv.lower() != ZAPPER.lower():
    send_tx(w3, acct,
            bo.functions.setRemoveManagerWithReceiver(TROVE_ID, ZAPPER, ZAPPER),
            label="setRemoveManagerWithReceiver -> zapper")

# --- 3. leverUpTrove ---
params = (TROVE_ID, r, M, max_fee)
send_tx(w3, acct, zapper.functions.leverUpTrove(params),
        label=f"leverUpTrove ke ~{TARGET_LEV}x")

# --- verifikasi ---
d2 = tm.functions.getLatestTroveData(TROVE_ID).call()
debt2, coll2 = d2[0], d2[1]
eq2 = coll2 * price // 10**18 - debt2
lev2 = (coll2 * price // 10**18) / eq2
print(f"SETELAH MULTIPLY: coll {coll2/1e18} SPY | debt {debt2/1e18} FUSD")
print(f"ekuitas {eq2/1e18} | leverage {lev2:.3f}x | ICR "
      f"{tm.functions.getCurrentICR(TROVE_ID, price).call()/1e18:.3f}")
print("wallet SPY:", spy.functions.balanceOf(WALLET).call() / 1e18)
fusd = load_abi_json(w3, FUSD, ERC20_ABI)
print("wallet FUSD:", fusd.functions.balanceOf(WALLET).call() / 1e18)
print("wallet ETH:", w3.eth.get_balance(WALLET) / 1e18)
json.dump({"troveId": str(TROVE_ID), "ownerIndex": 7309087378285118429},
          open("/home/hatch/workspace/florin/state.json", "w"))
