#!/usr/bin/env python3
"""Probe candidate contracts to find the Florin Multiply (leverage) contract."""
import json
from web3 import Web3

RPC = "https://rpc.testnet.chain.robinhood.com"
CANDIDATES = [
    "0x90910002956b3C881B74910F5f144b6a73dCcFbe",
    "0x2Ce45DC74397aE3A5082cc822A9A978fd387429b",
    "0xf63a41A0C8fDB81704C92Ba39eAcfB11f8C3FD87",
    "0x6AfC499c52571F03272Fa6a4FBba0b73674f7f4c",
]
# ABI pieces from the Florin frontend (viem parseAbi strings)
ABI = json.loads("""[
{"type":"function","name":"collToken","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"},
{"type":"function","name":"boldToken","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"},
{"type":"function","name":"borrowerOperations","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"},
{"type":"function","name":"exchange","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"},
{"type":"function","name":"flashLoanProvider","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"},
{"type":"function","name":"priceFeed","inputs":[],"outputs":[{"type":"address"}],"stateMutability":"view"},
{"type":"function","name":"priceScale","inputs":[],"outputs":[{"type":"uint256"}],"stateMutability":"view"},
{"type":"function","name":"oracleScale","inputs":[],"outputs":[{"type":"uint256"}],"stateMutability":"view"}
]""")

w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 20}))
assert w3.eth.chain_id == 46630
for addr in CANDIDATES:
    c = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=ABI)
    print("=====", addr)
    for fn in ("collToken", "boldToken", "borrowerOperations", "exchange",
               "flashLoanProvider", "priceFeed", "priceScale", "oracleScale"):
        try:
            print(f"  {fn}: {getattr(c.functions, fn)().call()}")
        except Exception as e:
            print(f"  {fn}: ERR {str(e)[:60]}")
