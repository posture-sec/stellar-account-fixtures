# Signer Structures, Master Key Presence, and Authority

> Tabular breakdown of signer counts, master key weights, presence derivations, and signing authority invariants across all nine fixtures.

## 1. Context and the Presence vs Authority Invariant

Stellar accounts authorize transactions using a cryptographic signer set. Across the nine captures in this corpus, signer configurations range from single-signer accounts to multi-signature arrangements with up to nine signers.

A critical security distinction arises between **signer presence** and **signing authority**:

1. **Signer Presence (`master_is_signer`)**: Defined in `SCHEMA.md:94` and evaluated by `validate.py:158` (lines 177-180), `master_is_signer` checks strictly whether the master public key (`account_id`) appears as an entry in the account's `signers` list. It does **not** check whether that key has a nonzero weight.
2. **Signing Authority**: A signer can sign operations with practical authorization authority only if its assigned weight meets or exceeds the required threshold (low, medium, or high). A master key with weight 0 has zero signing authority, yet it remains present on the account.

For example, in `fixtures/coordinator-data-entry/fixture.toml:5`, the master key appears in the `signers` array with `weight: 0`. It satisfies `master_is_signer` in `validate.py:158`, but has completely surrendered its direct signing power to the eight other configured signers.

Conversely, `fixtures/default-plain/fixture.toml:5` has exactly one signer: the master key with `weight: 1`.

## 2. Comparative Signer Structure Table

| Fixture ID | Total Signers | Master Key Weight | Master Present | Non-Master Signer Weights | Thresholds (L/M/H) | Signer Shape Labels |
|---|---|---|---|---|---|---|
| `asset-heavy-exchange` | 1 | 1 | Yes | None | 0/0/0 | `master_is_signer`, `single_signer` |
| `coordinator-data-entry` | 9 | 0 | Yes | 1, 2, 1, 2, 1, 1, 1, 1 | 2/2/2 | `master_is_signer`, `multi_signer` |
| `default-plain` | 1 | 1 | Yes | None | 0/0/0 | `master_is_signer`, `single_signer` |
| `domain-and-inflation` | 1 | 1 | Yes | None | 0/0/0 | `master_is_signer`, `single_signer` |
| `issuer-auth-required` | 2 | 1 | Yes | 1 | 1/1/1 | `master_is_signer`, `multi_signer` |
| `multisig-custody` | 2 | 2 | Yes | 4 | 2/3/4 | `master_is_signer`, `multi_signer` |
| `sponsored-trustlines` | 2 | 0 | Yes | 2 | 0/1/2 | `master_is_signer`, `multi_signer` |
| `testnet-multisig` | 6 | 0 | Yes | 1, 1, 1, 1, 1 | 3/3/3 | `master_is_signer`, `multi_signer` |
| `whitespace-home-domain` | 1 | 1 | Yes | None | 0/0/0 | `master_is_signer`, `single_signer` |

## 3. Analysis by Signer Configuration

### Single-Signer Baseline (4 Fixtures)
`asset-heavy-exchange`, `default-plain`, `domain-and-inflation`, and `whitespace-home-domain` each have exactly 1 signer: the account master key at weight 1. None have secondary signers. Because total signers equals 1, each emits `single_signer` and `master_is_signer`.

### Active Master Key with Secondary Signers (2 Fixtures)
- `issuer-auth-required`: 2 signers. Master key weight 1, and 1 non-master signer at weight 1. All thresholds set to 1.
- `multisig-custody`: 2 signers. Master key weight 2, and 1 non-master signer at weight 4. Thresholds are tiered at 2 (low), 3 (medium), and 4 (high). The master key can independently authorize low threshold operations, but requires the secondary signer for medium and high operations.

### Weight-Zero Master Key Multi-Signer Accounts (3 Fixtures)
Three fixtures demonstrate master key presence with zero signing authority:
- `coordinator-data-entry`: 9 signers. Master key weight 0; 8 non-master signers with weights 1, 2, 1, 2, 1, 1, 1, 1. Thresholds are 2/2/2.
- `sponsored-trustlines`: 2 signers. Master key weight 0; 1 non-master signer with weight 2. Thresholds are 0/1/2.
- `testnet-multisig`: 6 signers. Master key weight 0; 5 non-master signers each at weight 1. Thresholds are 3/3/3 (requiring 3 of 5 secondary signatures).

In all three fixtures, `validate.py` derives `master_is_signer` because the master key string exists in `signers`, proving to audit tools like Gauge that presence does not imply control.

## 4. Validator Derivation Rules

The validator implements signer evaluation in `validate.py:158` (`shapes_of`):

```python
if not signers:
    found.add("no_signers")
elif len(signers) == 1:
    found.add("single_signer")
else:
    found.add("multi_signer")

if any(signer.get("key") == account_id for signer in signers):
    found.add("master_is_signer")
else:
    found.add("master_absent")
```

The `master_absent` label is emitted only when Horizon completely omits the master key from the `signers` list, which occurs on Stellar when an account master key has been revoked and deleted from ledger state.
