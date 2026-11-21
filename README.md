# Florin testnet scripts — Robinhood Chain Testnet (46630)

Scripts for [Florin](https://florin.so), a Liquity V2 friendly fork: a lending
market for tokenized equities on Robinhood Chain Testnet. Deposit SPY as
collateral, borrow FUSD, lever up via the LeverageZapper, and deposit FUSD
into the Stability Pool.

**Testnet only. No real funds. Everything here runs against chainId 46630,
and every send is simulated with `eth_call` before it is broadcast.**

## Scripts

| File | What it does |
|---|---|
| `florin_common.py` | Shared helpers: RPC, contract addresses, key loading, `send_tx()` (simulate-then-send) |
| `florin_open.py` | Wrap ETH → WETH, approve, open a trove (SPY collateral, FUSD debt) |
| `florin_multiply.py` | `leverUpTrove` via the LeverageZapper (flash loan) |
| `florin_sp_manage.py` | Deposit to / withdraw from the Stability Pool |
| `florin_daily.py` | Daily session: 4-day rotation of small gas-only actions, with ICR / ETH guards |
| `florin_inspect.py` | Read trove, price feed and pool state |
| `florin_params.py` | Read protocol parameters (MCR, CCR, MIN_DEBT, …) |
| `probe_multiply.py` | Probe Multiply parameters before executing |

Contract ABIs (Blockscout exports) live in the `0x….json` files; `state.json`
holds the active trove id.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install web3 eth-account
```

Create the key file (testnet key only, never a mainnet key):

```bash
echo -n '<testnet-private-key>' > ~/.key   # or any path, 0600 permissions
chmod 600 <key-file>
```

Then edit `KEY_FILE`, `ABI_DIR` and `WALLET` at the top of
`florin_common.py` to match your machine. The key file is never committed
(see `.gitignore`).

## Usage

```bash
.venv/bin/python florin_open.py        # open a trove
.venv/bin/python florin_multiply.py    # lever up via the zapper
.venv/bin/python florin_sp_manage.py   # Stability Pool
.venv/bin/python florin_daily.py       # daily rotation session
.venv/bin/python florin_daily.py --dry-run   # simulate only, no tx
```

## Safety notes

- `florin_common.connect()` asserts chainId **46630** and refuses to run
  anywhere else.
- `send_tx()` simulates every call first; a reverting simulation aborts
  before any gas is spent.
- `florin_daily.py` stops with an alert (no corrective action) if the trove
  is inactive, ICR drops below 1.15, or ETH runs below 0.001.
- The faucet at faucet.florin.so gives 100 testnet SPY per address per 2h.

## Contracts (Robinhood Testnet, SPY branch)

| | |
|---|---|
| SPY | `0x8823b40A23387Df76E127744FFB38b26eB012A5c` |
| FUSD | `0x1F93dE989cD9D30b2C31F3227769632729858196` |
| BorrowerOperations | `0xfEa06161DBD14374ee6a746Eae3502A1A6741990` |
| TroveManager | `0xc1EbB33678176d7fB5C8FEf3ba5A610d50BAcC63` |
| StabilityPool | `0x9543b191C66C4FA68b9B7888dF65B661842ACe1B` |
| LeverageZapper | `0xf63a41A0C8fDB81704C92Ba39eAcfB11f8C3FD87` |
| SPYPriceFeed | `0xb7dc3a2596e9a0571b6e104d2f1a3d35b0653862` |

Protocol params: MCR 110%, CCR 130%, MIN_DEBT 2,000 FUSD, gas compensation
0.001 WETH.
