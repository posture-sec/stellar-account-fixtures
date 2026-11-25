# Balance counts and asset types

> Balance counts, asset types and trustline boundaries across the twelve fixtures, counted from each `account.json` `balances` array.

## 1. Total balances versus trustlines

`balances` in an account resource lists every balance the account holds, and the native lumen balance is one of those entries. The array length is therefore the number of balances, not the number of trustlines:

```
trustlines (non-native entries) = total balances - native balances
```

Every capture in this corpus has exactly one native entry, so an account with N balances holds N-1 trustlines. The native entry is the last element of `balances` in all twelve files. A consumer should not rely on that position, because the schema does not promise it, and should select the native entry by `asset_type`.

The validator counts total balances, not trustlines. The `many_balances` label below uses the array length, which includes the native entry.

## 2. The twelve fixtures

| Fixture | Network | Total balances | Native | `credit_alphanum4` | `credit_alphanum12` | Trustlines | Distinct issuers | `many_balances` |
|---|---|---|---|---|---|---|---|---|
| `asset-heavy-exchange` | public | 37 | 1 | 29 | 7 | 36 | 35 | yes |
| `coordinator-data-entry` | public | 3 | 1 | 2 | 0 | 2 | 2 | no |
| `default-plain` | public | 5 | 1 | 3 | 1 | 4 | 4 | no |
| `domain-and-inflation` | public | 5 | 1 | 2 | 2 | 4 | 4 | no |
| `issuer-auth-required` | public | 3 | 1 | 1 | 1 | 2 | 2 | no |
| `multisig-custody` | public | 5 | 1 | 2 | 2 | 4 | 2 | no |
| `null-home-domain` | public | 1 | 1 | 0 | 0 | 0 | 0 | no |
| `sponsored-trustlines` | public | 17 | 1 | 10 | 6 | 16 | 15 | yes |
| `ten-balances-boundary` | public | 10 | 1 | 6 | 3 | 9 | 9 | yes |
| `unnormalized-home-domain` | public | 1 | 1 | 0 | 0 | 0 | 0 | no |
| `testnet-multisig` | testnet | 1 | 1 | 0 | 0 | 0 | 0 | no |
| `testnet-plain` | testnet | 1 | 1 | 0 | 0 | 0 | 0 | no |
| `testnet-sponsored` | testnet | 2 | 1 | 1 | 0 | 1 | 1 | no |
| `whitespace-home-domain` | public | 5 | 1 | 3 | 1 | 4 | 4 | no |
| **All fourteen** | | **96** | **14** | **59** | **23** | **82** | | **3 of 14** |

"Distinct issuers" counts different `asset_issuer` values among the trustlines of one account. It is lower than the trustline count when one issuer supplies more than one asset, as in `multisig-custody` where four trustlines come from two issuers. `asset-heavy-exchange` holds 36 trustlines from 35 issuers.

Counts are taken directly from the `balances` arrays in `fixtures/<id>/account.json`. The test for this document recomputes every number in the table from those files, so a re-capture that changes a count fails the test until this file is updated.

## 3. Asset types

Exactly three `asset_type` values appear across the 96 balance entries:

| `asset_type` | Meaning | Entries | Carries `asset_code`, `asset_issuer`, `limit` |
|---|---|---|---|
| `native` | the lumen balance | 14 | no |
| `credit_alphanum4` | an issued asset whose code is 1 to 4 characters | 59 | yes |
| `credit_alphanum12` | an issued asset whose code is 5 to 12 characters | 23 | yes |

Reading notes:

- A native entry has only `asset_type`, `balance`, `buying_liabilities` and `selling_liabilities`. Code that reads `asset_code` or `asset_issuer` without checking `asset_type` first will meet a missing key on the native entry.
- An issued entry additionally carries `asset_code`, `asset_issuer`, `limit`, `is_authorized`, `is_authorized_to_maintain_liabilities` and `last_modified_ledger`.
- Amounts such as `balance` and `limit` are decimal strings with seven fractional digits. They are not numbers, and a parser should not convert them to floating point.
- Horizon can also return `liquidity_pool_shares` entries for pool trustlines. None of the twelve fixtures contains one, so this corpus says nothing about their shape. If a future capture contains an `asset_type` outside the three above, check Horizon's documentation for the account resource before documenting it here.

## 4. The `many_balances` boundary

`many_balances` is derived when `balances` has 10 or more entries, native included. The rule is in the shape vocabulary of [SCHEMA.md](../SCHEMA.md#5-the-shape-vocabulary) (the `many_balances` row, line 166) and in `shapes_of` in `validate.py` (lines 204 to 209).

```python
raw_balances = account.get("balances")
balances = len(raw_balances) if isinstance(raw_balances, list) else 0
if balances == 0:
    found.add("no_balances")
if balances >= 10:
    found.add("many_balances")
```

Consequences worth knowing:

- The threshold is on total balances, so an account with 9 trustlines plus the native balance is the smallest account that carries the label, and `ten-balances-boundary` is exactly that account. An account with 10 trustlines has 11 balances and also carries it.
- A value that is not a list reads as zero balances, so a malformed `balances` field derives `no_balances` rather than raising.
- Three fixtures carry the label: `asset-heavy-exchange` (37 balances), `sponsored-trustlines` (17) and `ten-balances-boundary` (exactly 10). The last one sits on the boundary, so a parser that sets the threshold one too high is caught. The other side is not covered: the largest fixture without the label has 5 balances, so no fixture holds 9, and a parser that sets the threshold one too low would not be caught by this corpus.
- `no_balances` (an empty list) has no capture. Every account read for this corpus carries at least its native balance, which `README.md` records under its coverage gaps.

## 5. Related documents

- [SCHEMA.md](../SCHEMA.md) section 2 for how `account.json` is stored, and section 5 for the label table.
- [shape-matrix.md](shape-matrix.md) for which fixture carries `many_balances` alongside the other labels.
- [provenance.md](provenance.md) for the ledger and capture time behind each count.
