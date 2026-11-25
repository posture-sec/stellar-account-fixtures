# Ledger Age and Freshness Analysis

This document provides a comparative analysis of capture ledger heights across the
Stellar account fixtures corpus measured against the canonical network root documents:
- `corpus/root-public.json` (`core_latest_ledger`: 65282680)
- `corpus/root-testnet.json` (`core_latest_ledger`: 5535136)

## 1. Specification and Integrity Contract

Under `SCHEMA.md:60`, every captured fixture sidecar must specify `ledger` as a
positive integer matching the `last_modified_ledger` returned by Horizon. This is
enforced in `validate.py:279`, which checks that `ledger` is an integer strictly
greater than zero.

While the validator enforces positive integer validity, it does not restrict how far
in the past a capture ledger may sit relative to the network head. This document
quantifies ledger age deltas so consumers can evaluate specimen freshness.

## 2. Capture Ledger Age Audit

The table below calculates the exact ledger delta (`delta = head_ledger - capture_ledger`)
and estimated elapsed time based on Stellar's canonical 5-second ledger closing target.

| Fixture ID | Network | Capture Ledger | Root Head Ledger | Ledger Delta | Estimated Age |
|---|---|---|---|---|---|
| `asset-heavy-exchange` | `public` | 65266866 | 65282680 | 15814 | ~22.0 hours |
| `coordinator-data-entry` | `public` | 65282653 | 65282680 | 27 | ~2.3 minutes |
| `default-plain` | `public` | 65266813 | 65282680 | 15867 | ~22.0 hours |
| `domain-and-inflation` | `public` | 65266813 | 65282680 | 15867 | ~22.0 hours |
| `issuer-auth-required` | `public` | 65266862 | 65282680 | 15818 | ~22.0 hours |
| `multisig-custody` | `public` | 65266865 | 65282680 | 15815 | ~22.0 hours |
| `sponsored-trustlines` | `public` | 65110665 | 65282680 | 172015 | ~9.95 days |
| `testnet-multisig` | `testnet` | 5535101 | 5535136 | 35 | ~2.9 minutes |
| `whitespace-home-domain` | `public` | 65266813 | 65282680 | 15867 | ~22.0 hours |

## 3. Analysis of Historical Lag in Sponsored Trustlines

The capture in `fixtures/sponsored-trustlines/fixture.toml:10` records ledger 65110665.
Compared to the public root head of 65282680, this represents a delta of 172015 ledgers,
which corresponds to approximately 9.95 days (nearly 10 full days) of Stellar history.

This lag occurred because accounts exhibiting complex sponsored trustline topologies
are infrequent on chain and were identified from earlier ledgers during corpus hunting.
Despite the delta, the specimen remains valid and cryptographically reproducible under
`validate.py:279` because Stellar ledger state at that height is immutable.
