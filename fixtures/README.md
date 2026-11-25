# Fixtures index

> A one-page map of the fourteen fixtures (thirteen captures and one synthetic account), so a consumer can choose a fixture without opening twenty-eight files.

Each directory below holds exactly two files: `account.json` (the Horizon response, verbatim) and `fixture.toml` (the sidecar that says where the bytes came from). The layout rules are in [SCHEMA.md](../SCHEMA.md) section 1, and this index is a reading aid, not a second source of truth: when it disagrees with a sidecar, the sidecar and `python3 validate.py --report` are right.

## 1. The fourteen fixtures

| Directory | Network | Ledger | Shape labels | Why it is here |
|---|---|---|---|---|
| [`asset-heavy-exchange`](asset-heavy-exchange/) | public | 65266866 | `has_home_domain`, `many_balances`, `master_is_signer`, `no_data`, `no_inflation`, `not_sponsored`, `single_signer`, `sponsoring`, `thresholds_zero` | 37 balances and a home domain, the shape that makes a response body large |
| [`coordinator-data-entry`](coordinator-data-entry/) | public | 65282653 | `has_data`, `master_is_signer`, `multi_signer`, `no_home_domain`, `no_inflation`, `not_sponsored`, `sponsoring`, `thresholds_nonzero` | one data entry and nine signers, the shape a hosted multisig coordinator leaves on chain |
| [`default-plain`](default-plain/) | public | 65266813 | `master_is_signer`, `no_data`, `no_home_domain`, `no_inflation`, `not_sponsored`, `not_sponsoring`, `single_signer`, `thresholds_zero` | the plain account a rule has to leave alone |
| [`domain-and-inflation`](domain-and-inflation/) | public | 65266813 | `has_home_domain`, `has_inflation`, `master_is_signer`, `no_data`, `not_sponsored`, `single_signer`, `sponsoring`, `thresholds_zero` | a home domain with an inflation destination, a well-formed SEP-1 candidate |
| [`issuer-auth-required`](issuer-auth-required/) | public | 65266862 | `auth_required`, `master_is_signer`, `multi_signer`, `no_data`, `no_home_domain`, `no_inflation`, `not_sponsored`, `sponsoring`, `thresholds_nonzero` | an issuer with `auth_required` set and two signers |
| [`multisig-custody`](multisig-custody/) | public | 65266865 | `has_inflation`, `master_is_signer`, `multi_signer`, `no_data`, `no_home_domain`, `not_sponsored`, `not_sponsoring`, `thresholds_nonzero` | two signers with stepped thresholds, the shape a shared custody account leaves on chain |
| [`null-home-domain`](null-home-domain/) | public | none | `master_is_signer`, `no_data`, `no_home_domain`, `no_inflation`, `not_sponsored`, `not_sponsoring`, `single_signer`, `thresholds_zero` | the one synthetic fixture: a home domain that is an explicit null, for parsers that must not fail on it |
| [`sponsored-trustlines`](sponsored-trustlines/) | public | 65110665 | `has_home_domain`, `many_balances`, `master_is_signer`, `multi_signer`, `no_data`, `no_inflation`, `not_sponsoring`, `sponsored`, `thresholds_nonzero` | an account whose own entries are paid for by someone else |
| [`ten-balances-boundary`](ten-balances-boundary/) | public | 65631935 | `many_balances`, `master_is_signer`, `no_data`, `no_home_domain`, `no_inflation`, `not_sponsored`, `not_sponsoring`, `single_signer`, `thresholds_zero` | exactly ten balances, the smallest array that carries `many_balances` |
| [`unnormalized-home-domain`](unnormalized-home-domain/) | public | 56040206 | `has_home_domain`, `master_is_signer`, `no_data`, `no_inflation`, `not_sponsored`, `not_sponsoring`, `single_signer`, `thresholds_zero` | a `home_domain` that carries uppercase characters (`StellarHQ.io`), for SEP-1 case-folding in consumers |
| [`testnet-multisig`](testnet-multisig/) | testnet | 5535101 | `master_is_signer`, `multi_signer`, `no_data`, `no_home_domain`, `no_inflation`, `not_sponsored`, `not_sponsoring`, `thresholds_nonzero` | six signers with the master at weight 0, the first testnet capture |
| [`testnet-plain`](testnet-plain/) | testnet | 5895891 | `master_is_signer`, `no_data`, `no_home_domain`, `no_inflation`, `not_sponsored`, `not_sponsoring`, `single_signer`, `thresholds_zero` | a plain single-signer testnet baseline, the control next to `testnet-multisig` |
| [`testnet-sponsored`](testnet-sponsored/) | testnet | 5884375 | `master_is_signer`, `no_data`, `no_home_domain`, `no_inflation`, `not_sponsoring`, `single_signer`, `sponsored`, `thresholds_zero` | a testnet account whose entries are paid for by someone else |
| [`whitespace-home-domain`](whitespace-home-domain/) | public | 65266813 | `blank_home_domain`, `has_inflation`, `master_is_signer`, `no_data`, `not_sponsored`, `single_signer`, `sponsoring`, `thresholds_zero` | a home domain that is a single space, which a tool that trims before validating reads as absent |

Eleven fixtures are on the public network (ten captures and the synthetic one) and three are on testnet. Ledger is the sidecar `ledger` value, which `validate.py` requires to be at least the account's `last_modified_ledger`. The synthetic fixture has none, because nothing was read from a ledger. Three captures (`default-plain`, `domain-and-inflation` and `whitespace-home-domain`) record the same ledger, 65266813.

## 2. Reading the shape labels

The labels in the table are the full set each sidecar declares, in the order `python3 validate.py --report` prints them (alphabetical). The vocabulary, and the rule that derives each label from the bytes, is defined once, in [SCHEMA.md](../SCHEMA.md#5-the-shape-vocabulary). This file does not repeat those definitions, so a label added to the schema needs no edit here until a fixture carries it.

Two things to keep in mind when selecting by label:

- A label is present only when the bytes support it. Absence of a label is meaningful: `no_data` means the `data` object is empty, not that the capture failed to look.
- Six labels have no fixture yet. The current list is under "Coverage gaps, stated" in the [top-level README](../README.md#coverage-gaps-stated).

For the same information laid out as a fixture-by-label grid, see [the shape matrix](../corpus/shape-matrix.md).

## 3. Where to go next

| You want | Open |
|---|---|
| Where and when each capture was taken, with its digest | [corpus/provenance.md](../corpus/provenance.md) |
| Signer structure and master key weight | [corpus/signers.md](../corpus/signers.md) |
| Exact threshold triples | [corpus/thresholds.md](../corpus/thresholds.md) |
| The one data entry in the corpus | [corpus/data-entries.md](../corpus/data-entries.md) |
| The file format and the validator rules | [SCHEMA.md](../SCHEMA.md) |
| To add a fixture | [Adding a fixture](../README.md#adding-a-fixture) and [CONTRIBUTING.md](../CONTRIBUTING.md) |

Fixtures are written by `tools/capture.py` and never by hand. This index lives in `fixtures/` but is not a fixture: `validate.py` only reads directories there, so this file is ignored by it.
