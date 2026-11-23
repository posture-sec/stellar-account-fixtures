<p align="center">
  <a href="https://github.com/posture-sec/stellar-account-fixtures/actions/workflows/ci.yml"><img src="https://github.com/posture-sec/stellar-account-fixtures/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/posture-sec/stellar-account-fixtures/actions/workflows/roadmap-check.yml"><img src="https://github.com/posture-sec/stellar-account-fixtures/actions/workflows/roadmap-check.yml/badge.svg" alt="Roadmap check" /></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/posture-sec/stellar-account-fixtures"><img src="https://api.scorecard.dev/projects/github.com/posture-sec/stellar-account-fixtures/badge" alt="OpenSSF Scorecard" /></a>
  <a href="https://github.com/posture-sec/stellar-account-fixtures/actions"><img src="https://img.shields.io/endpoint?url=https://posture-sec.github.io/stellar-account-fixtures/data/badge-tests.json" alt="Tests" /></a>
  <a href="#the-nine-accounts"><img src="https://img.shields.io/endpoint?url=https://posture-sec.github.io/stellar-account-fixtures/data/badge-fixtures.json" alt="Fixtures" /></a>
  <a href="https://posture-sec.github.io/stellar-account-fixtures/"><img src="https://img.shields.io/badge/docs-live-06b6d4" alt="Documentation Site" /></a>
  <a href="https://github.com/posture-sec/stellar-account-fixtures/actions/workflows/posture-watch.yml"><img src="https://github.com/posture-sec/stellar-account-fixtures/actions/workflows/posture-watch.yml/badge.svg" alt="Posture Watch" /></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache-2.0" />
  <a href="ROADMAP.md"><img src="https://img.shields.io/badge/status-active%20corpus-emerald" alt="Active Corpus" /></a>
</p>

# Stellar account fixtures

Public Stellar account reads, captured from Horizon and kept honest by a validator.

[Documentation site & Specimen Vault](https://posture-sec.github.io/stellar-account-fixtures/) · [Schema Specification](SCHEMA.md) · [The Nine Accounts](#the-nine-accounts) · [Shape Matrix](corpus/shape-matrix.md) · [Provenance](corpus/provenance.md) · [Signers](corpus/signers.md) · [Thresholds](corpus/thresholds.md) · [Data Entries](corpus/data-entries.md) · [Root Diff](corpus/root-diff.md) · [Adding a Fixture](#adding-a-fixture) · [Contributing](CONTRIBUTING.md)

Gauge audits the configuration of a real Stellar account. Airlock scans Stellar
repositories. Both need account-shaped JSON that is not invented: a rule written against
a hand-typed fixture passes until the first real account disagrees with the invention.
This corpus is the alternative. Nine accounts, eight on mainnet and one on testnet, stored
verbatim, each with the provenance that lets you check the claim.

```
fixtures/
  asset-heavy-exchange/    account.json  fixture.toml
  coordinator-data-entry/  account.json  fixture.toml
  default-plain/           account.json  fixture.toml
  domain-and-inflation/    account.json  fixture.toml
  issuer-auth-required/    account.json  fixture.toml
  multisig-custody/        account.json  fixture.toml
  sponsored-trustlines/    account.json  fixture.toml
  testnet-multisig/        account.json  fixture.toml
  whitespace-home-domain/  account.json  fixture.toml
corpus/
  data-entries.md
  provenance.md
  root-diff.md
  root-public.json
  root-testnet.json
  shape-matrix.md
  signers.md
  thresholds.md
```

## What is here, and what it is not

Every fixture is a `GET /accounts/<id>` response from the network named in its sidecar,
re-serialised with sorted keys and nothing else changed. The sidecar records the URL, the
UTC capture time, `last_modified_ledger`, the Horizon version that served it, and the
SHA-256 of the bytes next to it. `validate.py` recomputes all of that and fails if a
sidecar no longer describes its capture, or if a `shape` label is not visible in the
bytes.

```
$ python3 validate.py --report
fixtures/asset-heavy-exchange: has_home_domain, many_balances, master_is_signer, no_data, no_inflation, not_sponsored, single_signer, sponsoring, thresholds_zero
fixtures/coordinator-data-entry: has_data, master_is_signer, multi_signer, no_home_domain, no_inflation, not_sponsored, sponsoring, thresholds_nonzero
fixtures/default-plain: master_is_signer, no_data, no_home_domain, no_inflation, not_sponsored, not_sponsoring, single_signer, thresholds_zero
fixtures/domain-and-inflation: has_home_domain, has_inflation, master_is_signer, no_data, not_sponsored, single_signer, sponsoring, thresholds_zero
fixtures/issuer-auth-required: auth_required, master_is_signer, multi_signer, no_data, no_home_domain, no_inflation, not_sponsored, sponsoring, thresholds_nonzero
fixtures/multisig-custody: has_inflation, master_is_signer, multi_signer, no_data, no_home_domain, not_sponsored, not_sponsoring, thresholds_nonzero
fixtures/sponsored-trustlines: has_home_domain, many_balances, master_is_signer, multi_signer, no_data, no_inflation, not_sponsoring, sponsored, thresholds_nonzero
fixtures/testnet-multisig: master_is_signer, multi_signer, no_data, no_home_domain, no_inflation, not_sponsored, not_sponsoring, thresholds_nonzero
fixtures/whitespace-home-domain: blank_home_domain, has_inflation, master_is_signer, no_data, not_sponsored, single_signer, sponsoring, thresholds_zero
validate: corpus agrees with itself
```

That block is the output of the command above, run in this checkout on 2026-11-03. If a
fixture changes, the block is stale and the command is not: regenerate rather than trust it.
A static cross-reference matrix across all nine fixtures and all 24 labels is documented in
[Shape Label Matrix](corpus/shape-matrix.md). Consolidated account digests, ledger heights, and
Horizon versions are tabulated in [Corpus Provenance](corpus/provenance.md). Specific multi-signature
threshold triples (low, medium, high) are detailed in [Threshold Combinations Matrix](corpus/thresholds.md).

This corpus says nothing about whether an account is well configured. No expectations, no
severities, no rule ids: that is Gauge's job. Nothing here holds a secret key, and a
seed-shaped string (`S...`) is refused by both the capture tool and the validator.

## Status

<!-- METRICS:START -->
| Indicator | Value | Source |
|---|---|---|
| Verified Captures | **9 accounts** (8 Mainnet, 1 Test) | `fixtures/` |
| Test Suite | **246 passing** | `python -m unittest` |
| Integrity Assurance | **SHA-256 sidecars verified** | `validate.py` |
| Safety Invariant | **Zero secret keys (`S...`)** | Validator enforced |
<!-- METRICS:END -->

## Documentation site & Specimen Vault

A cryptographic specimen vault and ledger matrix is published at **[https://posture-sec.github.io/stellar-account-fixtures/](https://posture-sec.github.io/stellar-account-fixtures/)**. It provides interactive search, network filtering (Public vs Testnet), instant SHA-256 fingerprint copying, and visual specimen cards for each fixture in the corpus.

## The nine accounts

<!-- ACCOUNTS:START -->
| Fixture | Why it is here |
|---|---|
| `asset-heavy-exchange` | 37 trustlines and a home domain, the account shape that makes a naive response body large |
| `coordinator-data-entry` | one data entry named config.multisig.coordinator, nine signers with the master key at weight 0 and all three thresholds at 2, the shape a hosted multisig coordinator leaves on chain |
| `default-plain` | one signer which is the master key at weight 1, all thresholds zero and no optional fields, the account a rule has to leave alone |
| `domain-and-inflation` | home_domain lobstr.co with an inflation destination and two sponsorships, a well-formed SEP-1 candidate |
| `issuer-auth-required` | an issuer account with auth_required set, two signers at weight 1 and 150 sponsored entries |
| `multisig-custody` | two signers, master weight 2 and nonzero thresholds, the shape a shared custody account leaves on chain |
| `sponsored-trustlines` | num_sponsored 17 against num_sponsoring 0: seventeen balances and two signers, the account whose own entries are paid for by someone else, which no earlier capture showed |
| `testnet-multisig` | six signers on testnet, master weight 0 and all three thresholds at 3, the first capture that runs the testnet branch of the validator |
| `whitespace-home-domain` | home_domain is a single space, which a tool that trims before validating reads as absent |
<!-- ACCOUNTS:END -->

Account ids are in each sidecar. Eight are mainnet (`network = "public"`) and one is testnet
(`network = "testnet"`), and the root document for each network is the one the capture tool
fetched while writing it; see [Root Diff Analysis](corpus/root-diff.md). For signer structure
comparisons, master key presence, and authority analysis across all nine accounts, see
[Signer Structures](corpus/signers.md); for numerical threshold breakdowns, see
[Threshold Combinations Matrix](corpus/thresholds.md).

## Using it from another project

There is no package to install. Point a test at a directory, or vendor one:

```python
import json
from pathlib import Path

fixture = Path("stellar-account-fixtures/fixtures/multisig-custody/account.json")
account = json.loads(fixture.read_text())
```

Consumers can pin fixtures by content instead of repository commit using `tools/manifest.py`.
The tool prints one JSON line per fixture with its `id`, `account_id`, `network`, `ledger`, and `sha256`:

```bash
python3 tools/manifest.py
```

`shape` in the sidecar is the label set to select by. The ids are part of the contract and
do not get renamed; if a fixture has to be replaced, `SCHEMA.md` section 7 applies.

## Adding a fixture

Only `G...` account ids, only through the tool, and never by hand:

```
python3 tools/capture.py --network public --account G... \
  --id my-new-shape --scenario "one sentence on why this shape is missing"
python3 validate.py
```

The tool refuses a `G`-shaped address whose checksum does not verify, refuses an endpoint
whose `network_passphrase` is not the one that network should have, refuses a response
that describes a different account, and refuses to write anything containing a
seed-shaped string. Existing fixtures are not overwritten without `--update`.
`CONTRIBUTING.md` has the rules for a pull request.

## Coverage gaps, stated

24 shape labels exist in `SCHEMA.md` section 5; see [Shape Label Matrix](corpus/shape-matrix.md)
for the complete 9x24 cross-reference grid. Eighteen have a fixture. These 6 do not:

- `master_absent`, `no_signers`
- `auth_revocable`, `auth_immutable`, `auth_clawback_enabled`
- `no_balances`

`master_absent` and `no_signers` need an account whose master key was revoked, which is rare
and must not be manufactured (see [Signer Structures](corpus/signers.md) for how `master_is_signer`
checks key presence rather than signing authority). The three remaining auth flags need issuer accounts, and
roadmap 2.5 asks for one flag per account rather than one issuer carrying all three;
`auth_required` has had a fixture since 2026-11-02. `no_balances` has not appeared in any
read taken for this corpus: every account fetched while hunting these shapes, on both
networks, carries at least its native balance, so 2.3 may end in a decision that the label
stays uncovered rather than in a capture. `has_data`, `sponsored` and the first testnet
capture arrived on 2026-11-03 as roadmap 2.1, 2.2 and 2.6. None of the remaining six is
quietly worked around with synthetic data: a synthetic fixture is allowed by the schema and
none is shipped, so every number in this section describes a real read.

## Checks

```
python3 validate.py                 # corpus against its own sidecars
python3 -m unittest test_validate    # 95 tests, no network except two loopback checks
python3 -m unittest discover -s tests -t tests   # 18 cases that run the two roadmap gate scripts
ruff check . && ruff format --check .
mypy
python3 scripts/roadmap_progress.py --check ROADMAP.md   # the table is derived, not typed
```

`.github/workflows/ci.yml` runs those on Python 3.11 for every pull request and every push
to `main`; `.github/workflows/roadmap-check.yml` is the roadmap gate. The run that proves
they passed on GitHub is recorded with its date in `ROADMAP.md`, not here.

One workflow here reads the chain rather than the tree.
`.github/workflows/posture-watch.yml` runs the sibling action
[stellar-posture-watch](https://github.com/posture-sec/stellar-posture-watch) on Wednesday
06:41 UTC against `.posture/gauge.toml`, which declares the account behind
`fixtures/testnet-multisig` as this corpus captured it. A finding on the issue it maintains
means the capture no longer describes the live account, which is a thing to re-capture or to
explain rather than a number to average out. Its first three runs, on 2026-11-05, were a dry
run, the run that opened issue #29 with no findings at ledger 5568533, and a run that found
that issue by its state marker and left it alone. It triggers on `schedule` and
`workflow_dispatch` only, never on a pull request, and its token can write issues in this
repository and nothing else. The Gauge commit that action builds has no signer or threshold
rule yet, so what that read can report today is a flag appearing, a home domain appearing, or
the account ceasing to exist.

## Status and licence

Pre-release. No tag, no version to depend on, and the corpus is small enough that the
shape set will grow rather than stay fixed. Apache License 2.0; see `LICENSE`. The account
data itself is public ledger state, so what is licensed here is the compilation, the
sidecars and the tooling.

Sibling projects: [Gauge](https://github.com/posture-sec/guage), which reads a real Stellar account
and evaluates rules against it, and
[Airlock](https://github.com/posture-sec/airlock), which scans Stellar repositories. Both were the
reason this corpus exists, and neither has been pointed at these fixtures yet: that is gate G5, and
until a consumer names the two or more files it reads in its own test suite the sentence above
describes intent rather than a run.

The third sibling is the one this corpus points at rather than the other way round:
[stellar-posture-watch](https://github.com/posture-sec/stellar-posture-watch) is a scheduled
audit that keeps one tracking issue current, and the Checks section above describes this
repository using it. That is not G5 either. A watch reads a live account off Horizon and
compares it to a declared expectation; it consumes none of the files here, while G5 asks for a
test suite that names them.
