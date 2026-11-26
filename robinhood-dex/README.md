# Robinhood DEX — daily swap scripts (testnet)

Scripts for the daily swap routine on the community Uniswap v3 deployment on
**Robinhood Chain Testnet** (chainId 46630). Testnet only — no real funds.

## What it does

`robinhood_dex_daily.py` runs one small session per day on a 5-day rotation
(TSLA, NFLX, PLTR, AMZN, AMD):

1. Wrap 0.001 ETH to WETH if the WETH balance is short.
2. Swap 0.001 WETH → Stock Token.
3. Swap 0.05 Stock Token back → WETH.

Safety rails: if ETH drops below 0.001 the session prints an ALERT and sends
nothing; a failed simulation skips that action (never retried).

## Contracts (community deployment, unaudited)

- SwapRouter: `0x1b32F47434a7EF83E97d0675C823E547F9266725`
  (classic v1 `exactInputSingle` struct — includes `deadline`)
- Factory: `0xFECCB63CD759d768538458Ea56F47eA8004323c1`
- QuoterV2: `0x126f1c1F29A0f49c5D33e0139a5Da1FE25590dB1`
- WETH9: `0x37E402B8081eFcE1D82A09a066512278006e4691`
- Pools: 0.3% WETH against TSLA / NFLX / PLTR / AMZN / AMD (thin, ~0.2 WETH each)

## Files

- `dex_common.py` — shared helpers: RPC, contract ABIs, account loading, swap helpers
- `robinhood_dex_daily.py` — the daily session (rotation + safety rails)
- `session1.py`, `session1b.py` — first manual sessions (22 Nov 2026)
- `verify.py` — read-only balance/pool checks

## Key handling

The private key is read from `~/workspace/testnet-wallet/.key` (mode 600) at
runtime and is never printed, logged, or committed. The wallet is a dedicated
testnet-only wallet. Never reuse it on mainnet.

## Run

```bash
python robinhood_dex_daily.py
```

Requires `web3` and `eth-account`, plus a funded testnet wallet
(0.01 testnet ETH from the Robinhood faucet covers ~10 sessions).
