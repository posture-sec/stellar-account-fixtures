# Fixture Shape Label Matrix

> This matrix is a static convenience view derived from `python3 validate.py --report`. Sidecar manifests (`fixture.toml`) and underlying raw account bytes remain the authoritative source of truth.

## 1. Context and Purpose

Stellar account fixtures are indexed by machine-readable shape labels derived programmatically from `account.json` by `validate.py:140` (`shapes_of`). The canonical vocabulary of 24 labels is defined in `SCHEMA.md` Section 5.

While each fixture records its own declared labels in `fixture.toml` and `python3 validate.py --report` derives labels dynamically, this document provides a comprehensive static cross-reference matrix across all nine fixtures and all 24 shape labels for consumer developers.

## 2. Complete 9x24 Shape Matrix

| Fixture | `no_signers` | `single_signer` | `multi_signer` | `master_is_signer` | `master_absent` | `thresholds_zero` | `thresholds_nonzero` | `auth_required` | `auth_revocable` | `auth_immutable` | `auth_clawback_enabled` | `no_home_domain` | `blank_home_domain` | `has_home_domain` | `has_inflation` | `no_inflation` | `has_data` | `no_data` | `sponsored` | `not_sponsored` | `sponsoring` | `not_sponsoring` | `no_balances` | `many_balances` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `asset-heavy-exchange` | No | Yes | No | Yes | No | Yes | No | No | No | No | No | No | No | Yes | No | Yes | No | Yes | No | Yes | Yes | No | No | Yes |
| `coordinator-data-entry` | No | No | Yes | Yes | No | No | Yes | No | No | No | No | Yes | No | No | No | Yes | Yes | No | No | Yes | Yes | No | No | No |
| `default-plain` | No | Yes | No | Yes | No | Yes | No | No | No | No | No | Yes | No | No | No | Yes | No | Yes | No | Yes | No | Yes | No | No |
| `domain-and-inflation` | No | Yes | No | Yes | No | Yes | No | No | No | No | No | No | No | Yes | Yes | No | No | Yes | No | Yes | Yes | No | No | No |
| `issuer-auth-required` | No | No | Yes | Yes | No | No | Yes | Yes | No | No | No | Yes | No | No | No | Yes | No | Yes | No | Yes | Yes | No | No | No |
| `multisig-custody` | No | No | Yes | Yes | No | No | Yes | No | No | No | No | Yes | No | No | Yes | No | No | Yes | No | Yes | No | Yes | No | No |
| `sponsored-trustlines` | No | No | Yes | Yes | No | No | Yes | No | No | No | No | No | No | Yes | No | Yes | No | Yes | Yes | No | No | Yes | No | Yes |
| `testnet-multisig` | No | No | Yes | Yes | No | No | Yes | No | No | No | No | Yes | No | No | No | Yes | No | Yes | No | Yes | No | Yes | No | No |
| `whitespace-home-domain` | No | Yes | No | Yes | No | Yes | No | No | No | No | No | No | Yes | No | Yes | No | No | Yes | No | Yes | Yes | No | No | No |

## 3. Vocabulary Breakdown by Functional Category

### Signer Topology
- `single_signer`: 4 fixtures (`asset-heavy-exchange`, `default-plain`, `domain-and-inflation`, `whitespace-home-domain`)
- `multi_signer`: 5 fixtures (`coordinator-data-entry`, `issuer-auth-required`, `multisig-custody`, `sponsored-trustlines`, `testnet-multisig`)
- `master_is_signer`: 9 fixtures (All nine fixtures carry their master key in `signers`)
- `no_signers`: 0 fixtures (Uncovered gap)
- `master_absent`: 0 fixtures (Uncovered gap)

### Thresholds
- `thresholds_zero`: 4 fixtures (`asset-heavy-exchange`, `default-plain`, `domain-and-inflation`, `whitespace-home-domain`)
- `thresholds_nonzero`: 5 fixtures (`coordinator-data-entry`, `issuer-auth-required`, `multisig-custody`, `sponsored-trustlines`, `testnet-multisig`)

### Authorization Flags
- `auth_required`: 1 fixture (`issuer-auth-required`)
- `auth_revocable`: 0 fixtures (Uncovered gap)
- `auth_immutable`: 0 fixtures (Uncovered gap)
- `auth_clawback_enabled`: 0 fixtures (Uncovered gap)

### Home Domain
- `has_home_domain`: 3 fixtures (`asset-heavy-exchange`, `domain-and-inflation`, `sponsored-trustlines`)
- `blank_home_domain`: 1 fixture (`whitespace-home-domain`)
- `no_home_domain`: 5 fixtures (`coordinator-data-entry`, `default-plain`, `issuer-auth-required`, `multisig-custody`, `testnet-multisig`)

### Inflation Destination
- `has_inflation`: 3 fixtures (`domain-and-inflation`, `multisig-custody`, `whitespace-home-domain`)
- `no_inflation`: 6 fixtures (`asset-heavy-exchange`, `coordinator-data-entry`, `default-plain`, `issuer-auth-required`, `sponsored-trustlines`, `testnet-multisig`)

### Account Data Entries
- `has_data`: 1 fixture (`coordinator-data-entry`)
- `no_data`: 8 fixtures (`asset-heavy-exchange`, `default-plain`, `domain-and-inflation`, `issuer-auth-required`, `multisig-custody`, `sponsored-trustlines`, `testnet-multisig`, `whitespace-home-domain`)

### Sponsorship
- `sponsored`: 1 fixture (`sponsored-trustlines`)
- `not_sponsored`: 8 fixtures (`asset-heavy-exchange`, `coordinator-data-entry`, `default-plain`, `domain-and-inflation`, `issuer-auth-required`, `multisig-custody`, `testnet-multisig`, `whitespace-home-domain`)
- `sponsoring`: 5 fixtures (`asset-heavy-exchange`, `coordinator-data-entry`, `domain-and-inflation`, `issuer-auth-required`, `whitespace-home-domain`)
- `not_sponsoring`: 4 fixtures (`default-plain`, `multisig-custody`, `sponsored-trustlines`, `testnet-multisig`)

### Balances
- `many_balances`: 2 fixtures (`asset-heavy-exchange`, `sponsored-trustlines`)
- `no_balances`: 0 fixtures (Uncovered gap)

## 4. Derivation Guarantee

The shape matrix entries above are guaranteed by `validate.py:420` and verified in CI via automated test suites. Any modification to fixture files or derivation logic that causes deviation from this matrix will be rejected by repository verification gates.
