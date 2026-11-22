# Stellar Horizon Balance Types and Liquidity Pool Shares

This document details the observed balance schema structures in the corpus, comparing standard asset balances with liquidity pool share balances introduced in Stellar Protocol 18.

## 1. Observed Balance Schema Types

Across the corpus, four distinct asset types are encountered in `balances` arrays:

| `asset_type` | Schema Discriminator | Defining Properties | Example Fixture |
|---|---|---|---|
| `native` | `asset_type: "native"` | `balance`, `buying_liabilities`, `selling_liabilities` | `fixtures/default-plain` |
| `credit_alphanum4` | `asset_type: "credit_alphanum4"` | `asset_code` (1 to 4 chars), `asset_issuer`, `balance`, `limit` | `fixtures/asset-heavy-exchange` |
| `credit_alphanum12` | `asset_type: "credit_alphanum12"` | `asset_code` (5 to 12 chars), `asset_issuer`, `balance`, `limit` | `fixtures/asset-heavy-exchange` |
| `liquidity_pool_shares` | `asset_type: "liquidity_pool_shares"` | `liquidity_pool_id` (64 hex chars), `balance`, `limit`, auth flags | `fixtures/liquidity-pool-share` |

## 2. Anatomy of a Liquidity Pool Share Balance

In `fixtures/liquidity-pool-share/account.json:20`, a live liquidity pool share entry appears as follows:

```json
{
  "asset_type": "liquidity_pool_shares",
  "balance": "205288.9366234",
  "is_authorized": false,
  "is_authorized_to_maintain_liabilities": false,
  "last_modified_ledger": 57850755,
  "limit": "922337203685.4775807",
  "liquidity_pool_id": "00465688fe1e1ac17d6a03e639bfeb5072ce2cc74c74cb876c4a1f46bb369aa0"
}
```

### Key Differences from Issued Assets

1. **No `asset_code` or `asset_issuer`**:
   Unlike classic credit assets, a liquidity pool balance does not originate from a single issuing account and has no ticker code. Instead, ownership is tied to an Automated Market Maker (AMM) pool identified by `liquidity_pool_id`.

2. **Parser Vulnerability**:
   Consumer parsers (e.g., in security auditing or portfolio tools) that inspect balances using logic such as:
   ```python
   # Vulnerable pattern assuming all non-native balances have an issuer
   if balance["asset_type"] != "native":
       issuer = balance["asset_issuer"]
       code = balance["asset_code"]
   ```
   will crash with a `KeyError` when encountering `liquidity_pool_shares`.

3. **Pool Linkage**:
   The `liquidity_pool_id` is a SHA-256 hash identifying the constant-product pool reserves on ledger, queryable via Horizon endpoint `GET /liquidity_pools/{liquidity_pool_id}`.

## 3. Shape Label Derivation

In `validate.py:183`, `shapes_of()` iterates over the balances array:

```python
# validate.py:183
if not balances:
    found.add("no_balances")
elif len(balances) >= 10:
    found.add("many_balances")
```

The presence of `liquidity_pool_shares` entries contributes to the total balance count (`many_balances` when total balances reach 10 or more) without interfering with native or custom balance derivation rules.
