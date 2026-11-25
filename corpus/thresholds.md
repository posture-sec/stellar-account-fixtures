# Account Threshold Combinations Matrix

> Comprehensive matrix of low, medium, and high threshold triples across all nine captured fixtures and their validator derivation semantics.

## 1. Context and Protocol Authorization Model

In Stellar protocol operation processing, every operation is categorized into one of three threshold levels:
1. **Low Threshold**: `allow_trust`, `bump_sequence`, `set_trust_line_flags`.
2. **Medium Threshold**: `payment`, `change_trust`, `create_account`, `manage_data`, `manage_buy_offer`, `manage_sell_offer`, `path_payment_strict_receive`, `path_payment_strict_send`.
3. **High Threshold**: `account_merge`, `set_options` (specifically flag updates and signer modifications).

A transaction is valid only when the cumulative weight of valid signatures meets or exceeds the threshold required by each operation within the transaction.

In `SCHEMA.md` Section 5, the schema defines two coarse binary labels for thresholds:
- `thresholds_zero`: All three thresholds are exactly 0.
- `thresholds_nonzero`: Any of the three thresholds is greater than 0.

This document tabulates the exact numeric low, medium, and high threshold triples across the corpus, providing auditing tools and consumers with visibility into specific threshold patterns.

## 2. Comprehensive Threshold Matrix

| Fixture ID | Low (`low_threshold`) | Medium (`med_threshold`) | High (`high_threshold`) | Threshold Triple | Derived Shape Label |
|---|---|---|---|---|---|
| `asset-heavy-exchange` | 0 | 0 | 0 | `0/0/0` | `thresholds_zero` |
| `coordinator-data-entry` | 2 | 2 | 2 | `2/2/2` | `thresholds_nonzero` |
| `default-plain` | 0 | 0 | 0 | `0/0/0` | `thresholds_zero` |
| `domain-and-inflation` | 0 | 0 | 0 | `0/0/0` | `thresholds_zero` |
| `issuer-auth-required` | 1 | 1 | 1 | `1/1/1` | `thresholds_nonzero` |
| `multisig-custody` | 2 | 3 | 4 | `2/3/4` | `thresholds_nonzero` |
| `sponsored-trustlines` | 0 | 1 | 2 | `0/1/2` | `thresholds_nonzero` |
| `testnet-multisig` | 3 | 3 | 3 | `3/3/3` | `thresholds_nonzero` |
| `whitespace-home-domain` | 0 | 0 | 0 | `0/0/0` | `thresholds_zero` |

## 3. Validator Derivation Semantics

`validate.py:162` (lines 181-185) evaluates threshold configuration in `shapes_of`:

```python
keys = ("low_threshold", "med_threshold", "high_threshold")
if any(as_int(thresholds.get(key)) for key in keys):
    found.add("thresholds_nonzero")
else:
    found.add("thresholds_zero")
```

The derivation rule is strictly disjunctive:
- If `low_threshold > 0` or `med_threshold > 0` or `high_threshold > 0`, the validator emits `thresholds_nonzero`.
- Only if all three keys evaluate to 0 (or are absent / unparseable integers) does the validator emit `thresholds_zero`.

## 4. Analysis of Threshold Combinations in the Corpus

The nine fixtures capture six distinct threshold combinations:

### `0/0/0` (4 Fixtures)
- **Fixtures**: `asset-heavy-exchange`, `default-plain`, `domain-and-inflation`, `whitespace-home-domain`
- **Semantics**: Default Horizon account state. Any signer with weight >= 0 satisfies all threshold levels. In single-signer accounts where the master key weight is 1, this constitutes standard authorization.
- **Label**: `thresholds_zero`.

### `1/1/1` (1 Fixture)
- **Fixtures**: `issuer-auth-required`
- **Semantics**: Explicit symmetric threshold setting where low, medium, and high operations each require weight 1.
- **Label**: `thresholds_nonzero`.

### `2/2/2` (1 Fixture)
- **Fixtures**: `coordinator-data-entry`
- **Semantics**: Uniform multisig quorum requiring weight 2 across all operation categories.
- **Label**: `thresholds_nonzero`.

### `2/3/4` (1 Fixture)
- **Fixtures**: `multisig-custody`
- **Semantics**: Stepped / hierarchical threshold structure. Low-impact operations require weight 2; payments and exchange operations require weight 3; critical configuration changes (signers, master key, inflation) require weight 4.
- **Label**: `thresholds_nonzero`.

### `0/1/2` (1 Fixture)
- **Fixtures**: `sponsored-trustlines`
- **Semantics**: Asymmetric threshold setup where low operations are unrestricted (0), medium operations require weight 1, and high operations require weight 2.
- **Label**: `thresholds_nonzero`.

### `3/3/3` (1 Fixture)
- **Fixtures**: `testnet-multisig`
- **Semantics**: High-quorum 3-of-N multisig requiring weight 3 for all operations. Combined with 5 non-master signers of weight 1, this enforces 3-of-5 threshold authorization.
- **Label**: `thresholds_nonzero`.
