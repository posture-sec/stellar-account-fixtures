# Shape Label Reachability and Protocol Constraints

This document details protocol constraints on Stellar Horizon shape label reachability, explaining why the `no_balances` label is structurally unreachable for live captures and applies strictly to synthetic fixtures.

## 1. The Protocol Constraint on `no_balances`

In `SCHEMA.md` Section 5, `no_balances` is defined as derived when `balances` is an empty list in `account.json`:

```python
# validate.py:184
if not balances:
    found.add("no_balances")
elif len(balances) >= 10:
    found.add("many_balances")
```

On an active Stellar ledger, an account resource with zero balance entries cannot exist. Under Stellar consensus rules:

1. **Base Reserve Requirement**: Creating an account requires a `create_account` operation funding the new account with at least the network base reserve (currently 1 XLM on public and testnet networks).
2. **Native Balance Invariant**: An account cannot exist on ledger without an active native XLM balance entry holding this reserve. Even if all trustlines and pool shares are removed and the balance is reduced to the bare minimum reserve, the native XLM entry remains.
3. **Account Merging**: When an account balance drops below the minimum reserve via an `account_merge` operation, the account entry is deleted from the ledger entirely. Once deleted, Horizon returns HTTP 404 Not Found rather than an account resource with empty balances.

Consequently, every valid HTTP 200 account resource returned by Horizon carries at least one balance item: the native balance (`{"asset_type": "native", ...}`). Even minimal testnet fixtures (such as `fixtures/testnet-multisig`) carry one balance.

Because an account with zero balances cannot be captured from a live network, `no_balances` is unreachable for any captured fixture.

## 2. Synthetic Fixture Role

Although unreachable in live captures, the derivation rule in `validate.py:184` is preserved without alteration.

Synthetic fixtures (`kind = "synthetic"`) allow tool authors and parser implementers to test defensive handling of empty balances arrays without requiring impossible on-chain conditions. Synthetic sidecars declare `kind = "synthetic"` and describe their fabrication in their `scenario` text.

## 3. Reachability of Other Shape Labels

Other shape labels in the vocabulary with specific reachability characteristics include:

- `no_signers`: Horizon omits signers when all signing keys have weight 0 or when master key is revoked without replacement. Such accounts are unrecoverable locked accounts on chain.
- `master_absent`: Achieved when the master key weight is set to 0, causing Horizon to omit the master key from the `signers` list. Rare on mainnet but reachable on live ledgers.
- `blank_home_domain`: Observed in `fixtures/whitespace-home-domain`, where a single space was written to `home_domain`. Distinct from `no_home_domain` (where `home_domain` is omitted or null).
