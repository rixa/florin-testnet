#!/usr/bin/env python3
"""Shared helpers for Robinhood Chain Testnet DEX swaps (Uniswap v3, 46630).

Community (unaudited) Uniswap v3 deployment on Robinhood Testnet.
Key handling mirrors florin_common.py / tw.py: key from
~/workspace/testnet-wallet/.key (0600), never printed/logged.
Every send is preceded by an eth_call simulation.
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

# --- Verified on-chain (research pass, re-verify with reads before use) ---
WETH = "0x37E402B8081eFcE1D82A09a066512278006e4691"
FACTORY = "0xFECCB63CD759d768538458Ea56F47eA8004323c1"
ROUTER = "0x1b32F47434a7EF83E97d0675C823E547F9266725"
QUOTER = "0x126f1c1F29A0f49c5D33e0139a5Da1FE25590dB1"
POSITION_MANAGER = "0xBc82a9aA33ff24FCd56D36a0fB0a2105B193A327"

TOKENS = {
    "TSLA": "0xC9f9c86933092BbbfFF3CCb4b105A4A94bf3Bd4E",
    "AMZN": "0x5884aD2f920c162CFBbACc88C9C51AA75eC09E02",
    "NFLX": "0x3b8262A63d25f0477c4DDE23F83cfe22Cb768C93",
    "PLTR": "0x1FBE1a0e43594b3455993B5dE5Fd0A7A266298d0",
    "AMD": "0x71178BAc73cBeb415514eB542a8995b82669778d",
    "USDG": "0x7E955252E15c84f5768B83c41a71F9eba181802F",  # 6 decimals
}
DECIMALS = {"TSLA": 18, "AMZN": 18, "NFLX": 18, "PLTR": 18, "AMD": 18,
            "USDG": 6, "WETH": 18}

FEE = 3000  # 0.3% pools
# Pools with liquidity (all thin, ~0.2 WETH each): WETH/x for the 5 stocks.
PAIRS = ["TSLA", "NFLX", "PLTR", "AMZN", "AMD"]

ERC20_ABI = json.loads(
    '[{"constant":true,"inputs":[{"name":"a","type":"address"}],'
    '"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],'
    '"type":"function"},'
    '{"constant":false,"inputs":[{"name":"s","type":"address"},'
    '{"name":"v","type":"uint256"}],"name":"approve",'
    '"outputs":[{"name":"","type":"bool"}],"type":"function"},'
    '{"constant":true,"inputs":[{"name":"o","type":"address"},'
    '{"name":"s","type":"address"}],"name":"allowance",'
    '"outputs":[{"name":"","type":"uint256"}],"type":"function"},'
    '{"constant":true,"inputs":[],"name":"decimals",'
    '"outputs":[{"name":"","type":"uint8"}],"type":"function"},'
    '{"constant":true,"inputs":[],"name":"symbol",'
    '"outputs":[{"name":"","type":"string"}],"type":"function"}]')

WETH_ABI = json.loads(
    '[{"constant":false,"inputs":[],"name":"deposit","outputs":[],'
    '"payable":true,"stateMutability":"payable","type":"function"},'
    '{"constant":false,"inputs":[{"name":"wad","type":"uint256"}],'
    '"name":"withdraw","outputs":[],"type":"function"},'
    '{"constant":true,"inputs":[{"name":"a","type":"address"}],'
    '"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],'
    '"type":"function"},'
    '{"constant":false,"inputs":[{"name":"s","type":"address"},'
    '{"name":"v","type":"uint256"}],"name":"approve",'
    '"outputs":[{"name":"","type":"bool"}],"type":"function"},'
    '{"constant":true,"inputs":[{"name":"o","type":"address"},'
    '{"name":"s","type":"address"}],"name":"allowance",'
    '"outputs":[{"name":"","type":"uint256"}],"type":"function"}]')

FACTORY_ABI = json.loads(
    '[{"constant":true,"inputs":[{"name":"t0","type":"address"},'
    '{"name":"t1","type":"address"},{"name":"fee","type":"uint24"}],'
    '"name":"getPool","outputs":[{"name":"","type":"address"}],'
    '"type":"function"}]')

# NOTE: this deployment is the CLASSIC v1 SwapRouter, whose
# ExactInputSingleParams includes a `deadline` field (8 fields, not the
# 7-field SwapRouter02 layout). Its bytecode contains "Transaction too old"
# and the exactInputSingle selector (0x414bf389) routes through the
# checkDeadline modifier. Using the 7-field encoding silently shifts every
# field and reverts (empty data) on the WETH pull.
ROUTER_ABI = json.loads(
    '[{"inputs":[{"components":['
    '{"name":"tokenIn","type":"address"},'
    '{"name":"tokenOut","type":"address"},'
    '{"name":"fee","type":"uint24"},'
    '{"name":"recipient","type":"address"},'
    '{"name":"deadline","type":"uint256"},'
    '{"name":"amountIn","type":"uint256"},'
    '{"name":"amountOutMinimum","type":"uint256"},'
    '{"name":"sqrtPriceLimitX96","type":"uint160"}],'
    '"name":"params","type":"tuple"}],'
    '"name":"exactInputSingle",'
    '"outputs":[{"name":"amountOut","type":"uint256"}],'
    '"stateMutability":"payable","type":"function"}]')

# QuoterV2 quoteExactInputSingle takes ONE struct param (flat args revert).
QUOTER_ABI = json.loads(
    '[{"inputs":[{"components":['
    '{"name":"tokenIn","type":"address"},'
    '{"name":"tokenOut","type":"address"},'
    '{"name":"amountIn","type":"uint256"},'
    '{"name":"fee","type":"uint24"},'
    '{"name":"sqrtPriceLimitX96","type":"uint160"}],'
    '"name":"params","type":"tuple"}],'
    '"name":"quoteExactInputSingle",'
    '"outputs":[{"name":"amountOut","type":"uint256"},'
    '{"name":"sqrtPriceX96After","type":"uint160"},'
    '{"name":"initializedTicksCrossed","type":"uint32"},'
    '{"name":"gasEstimate","type":"uint256"}],'
    '"stateMutability":"nonpayable","type":"function"}]')

POOL_ABI = json.loads(
    '[{"constant":true,"inputs":[],"name":"slot0","outputs":['
    '{"name":"sqrtPriceX96","type":"uint160"},'
    '{"name":"tick","type":"int24"},'
    '{"name":"observationIndex","type":"uint16"},'
    '{"name":"observationCardinality","type":"uint16"},'
    '{"name":"observationCardinalityNext","type":"uint16"},'
    '{"name":"feeProtocol","type":"uint8"},'
    '{"name":"unlocked","type":"bool"}],"type":"function"},'
    '{"constant":true,"inputs":[],"name":"liquidity",'
    '"outputs":[{"name":"","type":"uint128"}],"type":"function"},'
    '{"constant":true,"inputs":[],"name":"token0",'
    '"outputs":[{"name":"","type":"address"}],"type":"function"},'
    '{"constant":true,"inputs":[],"name":"token1",'
    '"outputs":[{"name":"","type":"address"}],"type":"function"}]')


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


def contract(w3: Web3, addr: str, abi):
    return w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)


def has_code(w3: Web3, addr: str) -> bool:
    return len(w3.eth.get_code(Web3.to_checksum_address(addr))) > 0


def send_tx(w3: Web3, acct: Account, fn, value: int = 0, label: str = "") -> dict:
    """Simulate with eth_call first, then send. Returns receipt dict."""
    try:
        fn.call({"from": acct.address, "value": value})
    except Exception as e:
        print(f"SIMULASI GAGAL [{label}]: {e}")
        sys.exit(1)
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


def fmt(amount: int, decimals: int = 18) -> str:
    return f"{amount / (10 ** decimals):,.6f}".rstrip("0").rstrip(".")


def balances(w3: Web3) -> dict:
    """Read-only snapshot: ETH, WETH, all stock tokens + USDG."""
    out = {"ETH": w3.eth.get_balance(WALLET)}
    weth = contract(w3, WETH, WETH_ABI)
    out["WETH"] = weth.functions.balanceOf(WALLET).call()
    for sym, addr in TOKENS.items():
        c = contract(w3, addr, ERC20_ABI)
        out[sym] = c.functions.balanceOf(WALLET).call()
    return out


def print_balances(bal: dict, title: str = "Saldo"):
    print(f"--- {title} ---")
    print(f"  ETH : {fmt(bal['ETH'])}")
    print(f"  WETH: {fmt(bal['WETH'])}")
    for sym in TOKENS:
        print(f"  {sym:4}: {fmt(bal[sym], DECIMALS[sym])}")


def get_pool(w3: Web3, token_a: str, token_b: str, fee: int = FEE) -> str:
    factory = contract(w3, FACTORY, FACTORY_ABI)
    return factory.functions.getPool(
        Web3.to_checksum_address(token_a),
        Web3.to_checksum_address(token_b), fee).call()


def quote(w3: Web3, token_in: str, token_out: str, amount_in: int,
          fee: int = FEE) -> int:
    """QuoterV2 quoteExactInputSingle — struct param (single tuple)."""
    q = contract(w3, QUOTER, QUOTER_ABI)
    params = (Web3.to_checksum_address(token_in),
              Web3.to_checksum_address(token_out),
              amount_in, fee, 0)
    out = q.functions.quoteExactInputSingle(params).call()
    return out[0]


def ensure_allowance(w3: Web3, acct: Account, token: str, spender: str,
                     amount: int, label: str, dry_run: bool = False) -> dict | None:
    """Approve spender if current allowance < amount. Returns tx dict or None."""
    c = contract(w3, token, ERC20_ABI)
    cur = c.functions.allowance(acct.address,
                                Web3.to_checksum_address(spender)).call()
    if cur >= amount:
        print(f"[{label}] allowance sudah cukup ({fmt(cur)}), skip approve.")
        return None
    print(f"[{label}] allowance {fmt(cur)} < {fmt(amount)} — approve...")
    if dry_run:
        print("  [dry-run] approve disimulasikan saja, tidak dikirim.")
        c.functions.approve(Web3.to_checksum_address(spender),
                            amount).call({"from": acct.address})
        return None
    return send_tx(w3, acct,
                   c.functions.approve(Web3.to_checksum_address(spender),
                                       amount),
                   label=f"approve {label}")


def swap_exact_in(w3: Web3, acct: Account, token_in: str, token_out: str,
                  amount_in: int, min_pct: float = 0.95,
                  label: str = "", dry_run: bool = False) -> dict | None:
    """Quote, then exactInputSingle with amountOutMinimum = min_pct of quote."""
    q = quote(w3, token_in, token_out, amount_in)
    print(f"[{label}] quote: {fmt(amount_in)} in -> {fmt(q)} out")
    if q == 0:
        print(f"[{label}] quote 0 — batal.")
        return None
    min_out = int(q * min_pct)
    router = contract(w3, ROUTER, ROUTER_ABI)
    deadline = w3.eth.get_block("latest").timestamp + 1800  # v1 router field
    params = (Web3.to_checksum_address(token_in),
              Web3.to_checksum_address(token_out),
              FEE, acct.address, deadline, amount_in, min_out, 0)
    fn = router.functions.exactInputSingle(params)
    if dry_run:
        print(f"  [dry-run] simulasi exactInputSingle (minOut {fmt(min_out)})...")
        sim_out = fn.call({"from": acct.address})
        print(f"  [dry-run] simulasi OK, amountOut {fmt(sim_out)}")
        return {"dry_run": True, "quote": q, "sim_out": sim_out}
    return send_tx(w3, acct, fn, label=label)
