# Stellar account fixtures

Public Stellar account reads, captured from Horizon and kept honest by a validator.

Gauge audits the configuration of a real Stellar account. Airlock scans Stellar
repositories. Both need account-shaped JSON that is not invented: a rule written against
a hand-typed fixture passes until the first real account disagrees with the invention.
This corpus is the alternative. Six mainnet accounts, stored verbatim, each with the
provenance that lets you check the claim.

```
fixtures/
  asset-heavy-exchange/    account.json  fixture.toml
  default-plain/           account.json  fixture.toml
  domain-and-inflation/    account.json  fixture.toml
  issuer-auth-required/    account.json  fixture.toml
  multisig-custody/        account.json  fixture.toml
  whitespace-home-domain/  account.json  fixture.toml
corpus/
  root-public.json
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
fixtures/default-plain: master_is_signer, no_data, no_home_domain, no_inflation, not_sponsored, not_sponsoring, single_signer, thresholds_zero
fixtures/domain-and-inflation: has_home_domain, has_inflation, master_is_signer, no_data, not_sponsored, single_signer, sponsoring, thresholds_zero
fixtures/issuer-auth-required: auth_required, master_is_signer, multi_signer, no_data, no_home_domain, no_inflation, not_sponsored, sponsoring, thresholds_nonzero
fixtures/multisig-custody: has_inflation, master_is_signer, multi_signer, no_data, no_home_domain, no_inflation, not_sponsored, not_sponsoring, thresholds_nonzero
fixtures/whitespace-home-domain: blank_home_domain, has_inflation, master_is_signer, no_data, not_sponsored, single_signer, sponsoring, thresholds_zero
validate: corpus agrees with itself
```

That block is the output of the command above, run in this checkout on 2026-11-02. If a
fixture changes, the block is stale and the command is not: regenerate rather than trust it.

This corpus says nothing about whether an account is well configured. No expectations, no
severities, no rule ids: that is Gauge's job. Nothing here holds a secret key, and a
seed-shaped string (`S...`) is refused by both the capture tool and the validator.

## The six accounts

| Fixture | Why it is here |
|---|---|
| `default-plain` | One signer, which is the master key at weight 1; all thresholds zero and no optional field set. The account a rule has to leave alone. |
| `multisig-custody` | Two signers, master weight 2, thresholds 2/3/4. The shape a shared custody account leaves on chain. |
| `issuer-auth-required` | An issuer with `auth_required` set, two signers at weight 1, thresholds 1/1/1, 150 sponsored entries. |
| `asset-heavy-exchange` | 37 trustlines and a home domain. The account shape that makes a naive response body large. |
| `whitespace-home-domain` | `home_domain` is a single space, which a tool that trims before validating reads as absent. |
| `domain-and-inflation` | `lobstr.co` plus an inflation destination: a well-formed SEP-1 candidate to check the positive path against. |

Account ids are in each sidecar. All six are mainnet (`network = "public"`).

## Using it from another project

There is no package to install. Point a test at a directory, or vendor one:

```python
import json
from pathlib import Path

fixture = Path("stellar-account-fixtures/fixtures/multisig-custody/account.json")
account = json.loads(fixture.read_text())
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

24 shape labels exist in `SCHEMA.md` section 5. These 8 have no fixture:

- `has_data`, `sponsored`, `no_balances`, `master_absent`, `no_signers`
- `auth_revocable`, `auth_immutable`, `auth_clawback_enabled`

`master_absent` and `no_signers` need an account whose master key was revoked, which is
rare and must not be manufactured; `has_data` and `sponsored` are ordinary and are
roadmap 2.1. The three remaining auth flags need issuer accounts. No testnet fixture
exists yet, so the `testnet` branch of the validator is covered by tests only, not by a
capture. None of these are quietly worked around with synthetic data: a synthetic fixture
is allowed by the schema and none is shipped, so every number in this section describes a
real read.

## Checks

```
python3 validate.py                 # corpus against its own sidecars
python3 -m unittest test_validate    # 95 tests, no network except two loopback checks
ruff check . && ruff format --check .
mypy
python3 scripts/roadmap_progress.py --check ROADMAP.md   # the table is derived, not typed
```

`.github/workflows/ci.yml` runs those on Python 3.11 for every pull request and every push
to `main`; `.github/workflows/roadmap-check.yml` is the roadmap gate. The run that proves
they passed on GitHub is recorded with its date in `ROADMAP.md`, not here.

## Status and licence

Pre-release. No tag, no version to depend on, and the corpus is small enough that the
shape set will grow rather than stay fixed. Apache License 2.0; see `LICENSE`. The account
data itself is public ledger state, so what is licensed here is the compilation, the
sidecars and the tooling.

Sibling projects: [Gauge](https://github.com/posture-sec/guage), which reads one of these
accounts and evaluates rules against it, and
[Airlock](https://github.com/posture-sec/airlock), which scans Stellar repositories.
