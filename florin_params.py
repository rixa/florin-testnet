#!/usr/bin/env python3
"""Read-only param discovery for Florin SPY branch on Robinhood Testnet (46630)."""
import json
from web3 import Web3

RPC = "https://rpc.testnet.chain.robinhood.com"
BO = "0xfEa06161DBD14374ee6a746Eae3502A1A6741990"
TM = "0xc1EbB33678176d7fB5C8FEf3ba5A610d50BAcC63"
REG = "0xEB264317B915CB1A8c8e3ca27DD270D947bBA968"
HH = "0xcd8bf0cB142d8E612B9685772b2c5439240c1BA5"
PRICEFEEDS = [
    "0x3447c506Ce0936b94eaca091e2Fb2dF1DFa23733",
    "0x5844a1B7901a5D42cC428528F3FA089b88219Ed6",
    "0x54698Ae50ac4609d434630fC02B5bC7954805086",
    "0x07aF1FCA995Fe829085d5C9690706BFB92E76663",
    "0x9371DDeD6Ce9c1DEf218aDFfe99c286B47555076",
    "0xc71640206A66Bc6005BCddAAdE87C415957E6b93",
]

w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 20}))
assert w3.eth.chain_id == 46630

def load(addr, fname=None):
    d = json.load(open(f"/home/hatch/workspace/florin/{fname or addr + '.json'}"))
    return w3.eth.contract(address=Web3.to_checksum_address(addr), abi=d["abi"])

bo = load(BO)
tm = load(TM)
reg = load(REG)
hh = load(HH)

print("BO MCR:", bo.functions.MCR().call() / 1e18)
print("BO CCR:", bo.functions.CCR().call() / 1e18)
print("BO SCR:", bo.functions.SCR().call() / 1e18)
print("BO BCR:", bo.functions.BCR().call() / 1e18)
print("TM sortedTroves:", tm.functions.sortedTroves().call())
print("TM trove count:", tm.functions.getTroveIdsCount().call())
print("TM branch coll (SPY):", tm.functions.getEntireBranchColl().call() / 1e18)
print("TM branch debt (FUSD):", tm.functions.getEntireBranchDebt().call() / 1e18)
print("HH collateralRegistry:", hh.functions.collateralRegistry().call())
print("REG boldToken:", reg.functions.boldToken().call())
print("REG totalCollaterals:", reg.functions.totalCollaterals().call())
for i in range(reg.functions.totalCollaterals().call()):
    print(f"  coll[{i}] token={reg.functions.getToken(i).call()} troveManager={reg.functions.getTroveManager(i).call()}")

pf_abi = json.load(open("/home/hatch/workspace/florin/pricefeed.json"))["abi"]
for pf in PRICEFEEDS:
    c = w3.eth.contract(address=Web3.to_checksum_address(pf), abi=pf_abi)
    try:
        dec = c.functions.decimals().call()
        rd = c.functions.latestRoundData().call()
        print(f"PriceFeed {pf}: decimals={dec} answer={rd[1] / (10 ** dec)} updatedAt={rd[3]}")
    except Exception as e:
        print(f"PriceFeed {pf}: ERROR {e}")

# upfront fee prediction for a 2000 FUSD trove at 5% (collIndex found above; try 0)
try:
    fee = hh.functions.predictOpenTroveUpfrontFee(0, 2000 * 10**18, 5 * 10**16).call()
    print("predicted upfront fee (2000 FUSD @5%):", fee / 1e18, "FUSD")
except Exception as e:
    print("predictOpenTroveUpfrontFee error:", e)
