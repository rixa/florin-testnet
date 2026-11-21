#!/usr/bin/env python3
"""Read-only inspection of Florin contracts on Robinhood Chain Testnet (46630)."""
import json
from web3 import Web3

RPC = "https://rpc.testnet.chain.robinhood.com"
WALLET = "0xc7F389e96c1f6Ba876845581c19031960fF36156"
SP = "0x9543b191C66C4FA68b9B7888dF65B661842ACe1B"
AP = "0xF00A7eB2CF0D8DEe71788bBB99d57d8A4EF98775"
SPY = "0x8823b40A23387Df76E127744FFB38b26eB012A5c"
FUSD = "0x1F93dE989cD9D30b2C31F3227769632729858196"

w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 20}))
print("chainId:", w3.eth.chain_id)
assert w3.eth.chain_id == 46630

def load(addr):
    d = json.load(open(f"/home/hatch/workspace/florin/{addr}.json"))
    return w3.eth.contract(address=Web3.to_checksum_address(addr), abi=d["abi"])

sp = load(SP)
ap = load(AP)
print("StabilityPool.troveManager:", sp.functions.troveManager().call())
print("StabilityPool.activePool:", sp.functions.activePool().call())
print("StabilityPool.collToken:", sp.functions.collToken().call())
print("StabilityPool.boldToken:", sp.functions.boldToken().call())
print("StabilityPool total FUSD deposits:", sp.functions.getTotalBoldDeposits().call() / 1e18)
print("ActivePool.troveManagerAddress:", ap.functions.troveManagerAddress().call())
print("ActivePool.borrowerOperationsAddress:", ap.functions.borrowerOperationsAddress().call())
print("ActivePool.stabilityPool:", ap.functions.stabilityPool().call())
print("ActivePool.collToken:", ap.functions.collToken().call())
print("ActivePool.boldToken:", ap.functions.boldToken().call())
print("ActivePool coll balance (SPY):", ap.functions.getCollBalance().call() / 1e18)
print("ActivePool bold debt (FUSD):", ap.functions.getBoldDebt().call() / 1e18)

erc20 = json.loads('[{"constant":true,"inputs":[{"name":"a","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]')
for sym, addr in (("SPY", SPY), ("FUSD", FUSD)):
    t = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=erc20)
    print(f"wallet {sym} balance:", t.functions.balanceOf(WALLET).call() / 1e18)
print("wallet ETH balance:", w3.eth.get_balance(WALLET) / 1e18)
print("wallet SP deposits:", sp.functions.deposits(WALLET).call())
