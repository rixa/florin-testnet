#!/usr/bin/env python3
"""Shared helpers for Florin testnet execution (Robinhood Testnet 46630 only).

Key handling mirrors tw.py: key from ~/workspace/testnet-wallet/.key (0600),
never printed/logged. Every send is preceded by an eth_call simulation.
"""
import json
import os
import sys

from eth_account import Account
from web3 import Web3

RPC = "https://rpc.testnet.chain.robinhood.com"
CHAIN_ID = 46630
WALLET = "0xc7F389e96c1f6Ba876845581c19031960fF36156"
EXPLORER_TX = "https://explorer.testnet.chain.robinhood.com/tx/"
KEY_FILE = "/home/hatch/workspace/testnet-wallet/.key"
ABI_DIR = "/home/hatch/workspace/florin"

# Florin SPY branch (all verified on-chain / from official frontend config)
SPY = "0x8823b40A23387Df76E127744FFB38b26eB012A5c"
FUSD = "0x1F93dE989cD9D30b2C31F3227769632729858196"
BO = "0xfEa06161DBD14374ee6a746Eae3502A1A6741990"          # BorrowerOperations
TM = "0xc1EbB33678176d7fB5C8FEf3ba5A610d50BAcC63"          # TroveManager
SP = "0x9543b191C66C4FA68b9B7888dF65B661842ACe1B"          # StabilityPool
AP = "0xF00A7eB2CF0D8DEe71788bBB99d57d8A4EF98775"          # ActivePool
ST = "0x83311690476DFa9239b55E732b4b6638a15142dF"          # SortedTroves
HH = "0xcd8bf0cB142d8E612B9685772b2c5439240c1BA5"          # HintHelpers
REG = "0xEB264317B915CB1A8c8e3ca27DD270D947bBA968"         # CollateralRegistry
PRICE_FEED = "0xb7dc3a2596e9a0571b6e104d2f1a3d35b0653862"   # SPYPriceFeed
ZAPPER = "0xf63a41A0C8fDB81704C92Ba39eAcfB11f8C3FD87"       # LeverageZapper (Multiply)
EXCHANGE = "0x6AfC499c52571F03272Fa6a4FBba0b73674f7f4c"     # mock exchange + flash loans

ERC20_ABI = json.loads(
    '[{"constant":true,"inputs":[{"name":"a","type":"address"}],'
    '"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],'
    '"type":"function"},'
    '{"constant":false,"inputs":[{"name":"s","type":"address"},'
    '{"name":"v","type":"uint256"}],"name":"approve",'
    '"outputs":[{"name":"","type":"bool"}],"type":"function"},'
    '{"constant":true,"inputs":[{"name":"o","type":"address"},'
    '{"name":"s","type":"address"}],"name":"allowance",'
    '"outputs":[{"name":"","type":"uint256"}],"type":"function"}]')


def load_account() -> Account:
    if not os.path.exists(KEY_FILE):
        sys.exit("Key belum disiapkan: file .key tidak ada.")
    perm = oct(os.stat(KEY_FILE).st_mode)[-3:]
    if perm != "600":
        sys.exit(f"Izin file .key tidak aman ({perm}); wajib 600. Berhenti.")
    key = open(KEY_FILE).read().strip()
    if not key:
        sys.exit("File .key kosong.")
    acct = Account.from_key(key)
    assert acct.address == WALLET, f"Alamat key {acct.address} != {WALLET}"
    return acct


def connect() -> Web3:
    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 30}))
    cid = w3.eth.chain_id
    if cid != CHAIN_ID:
        sys.exit(f"chainId RPC ({cid}) != {CHAIN_ID}. Berhenti.")
    return w3


def load_abi(w3: Web3, addr: str, fname: str):
    d = json.load(open(os.path.join(ABI_DIR, fname)))
    return w3.eth.contract(address=Web3.to_checksum_address(addr), abi=d["abi"])


def load_abi_json(w3: Web3, addr: str, abi):
    return w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)


def send_tx(w3: Web3, acct: Account, fn, value: int = 0, label: str = "") -> dict:
    """Simulate with eth_call first, then send. Returns receipt dict."""
    # 1. simulation (free, catches reverts before spending gas)
    try:
        fn.call({"from": acct.address, "value": value})
    except Exception as e:
        print(f"SIMULASI GAGAL [{label}]: {e}")
        sys.exit(1)
    # 2. build + send
    tx = fn.build_transaction({
        "from": acct.address,
        "chainId": CHAIN_ID,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "gasPrice": w3.eth.gas_price,
        "value": value,
    })
    tx["gas"] = w3.eth.estimate_gas(tx)
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    hx = h.hex()
    print(f"[{label}] tx terkirim: {hx}")
    print(f"  explorer: {EXPLORER_TX}{hx}")
    rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=180)
    ok = rcpt.status == 1
    print(f"  status: {'SUKSES' if ok else 'GAGAL/REVERT'} | gasUsed: "
          f"{rcpt.gasUsed} | block: {rcpt.blockNumber}")
    if not ok:
        sys.exit(1)
    return {"hash": hx, "gasUsed": rcpt.gasUsed, "block": rcpt.blockNumber}
