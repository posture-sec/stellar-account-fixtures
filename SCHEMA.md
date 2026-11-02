# Fixture schema, version 1

This document is the contract. `validate.py` enforces most of it, `tools/capture.py`
writes all of the captured fixtures, and anything a consumer of this corpus relies on
should be described here or it is not part of the corpus.

## 1. Layout

```
fixtures/<fixture-id>/
  account.json      the account resource, verbatim from Horizon
  fixture.toml      the sidecar: what this is, where it came from, what shape it has
corpus/
  root-<network>.json  the Horizon root document captured alongside the fixture
tools/
  capture.py        writes a new captured fixture and its root document
validate.py         checks the whole tree against this schema
test_validate.py    the tests for both
```

A fixture id is kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`) and equals its directory name.
A fixture directory contains exactly `account.json` and `fixture.toml`; a third file is
a validator problem, because the schema does not know what to do with it.

## 2. account.json

The bytes are what Horizon returned for `GET /accounts/<account-id>`, re-serialised with
`json.dumps(payload, indent=2, sort_keys=True)` plus a trailing newline. Nothing is
stripped and nothing is added: an account resource is public ledger state, and a fixture
that has been edited is a fixture whose provenance claim is a lie. LF line endings only.

Consequences worth stating plainly:

- Field names and shapes follow Horizon, so they can change when Horizon changes. A
  `--update` re-capture is how a fixture is refreshed; the ledger number in the sidecar
  is what tells you how old the bytes are.
- The capture is a point-in-time read. An account that was multisig at ledger 65266865
  can be single-signer tomorrow. Do not treat `last_modified_ledger` as decorative.
- `data` is present in some captures and empty in others. Empty means the account has no
  data entries, not that the field was dropped.

## 3. fixture.toml

Flat TOML, one section, no tables. Unknown keys are a validator problem: a key the
schema does not define is a key no consumer will read.

| Key | Captured | Synthetic | Meaning |
|---|---|---|---|
| `schema_version` | required | required | Integer. This corpus is `1`; see section 7. |
| `id` | required | required | Kebab-case, equal to the directory name. |
| `kind` | required | required | `captured` or `synthetic`. |
| `scenario` | required | required | One sentence on what the shape is for, in plain words. |
| `account_id` | required | required | `G...` ed25519 account id, checksum included. |
| `network` | required | required | `public` or `testnet`. |
| `shape` | required | required | Sorted list of the labels in section 5. |
| `source_url` | required | forbidden | The exact URL that was read. |
| `captured_at` | required | forbidden | `YYYY-MM-DDTHH:MM:SSZ`, UTC, not in the future. |
| `ledger` | required | forbidden | `last_modified_ledger` of the resource, positive. |
| `horizon_version` | required | forbidden | Version string from the endpoint that served it. |
| `sha256` | required | forbidden | SHA-256 of `account.json` as it sits on disk. |

`synthetic` exists for shapes that cannot be captured, and the split is strict: a
synthetic fixture may not carry provenance keys, because it was never read from
anywhere, and its `scenario` must start with `synthetic:`. A synthetic fixture's
`account_id` still has to be a valid `G...` strkey, so a consumer's tests can treat both
kinds the same way.

## 4. What `account_id` has to satisfy

Only `G...` (ed25519 public key, version byte 48). `M...`, `C...`, `T...` and `X...` are
not account resources and are refused by `tools/capture.py` before it makes a request.
The CRC16-XMODEM checksum over the first 33 bytes must verify, which is what stops a
typo or an invented address from entering the corpus: `validate.py` recomputes it.

Seed strings (`S...`) are refused at three points: the capture tool will not write a
response containing a seed-shaped string, the validator scans both files of every fixture
for one, and the test suite builds its seed-shaped samples from zero bytes at run time so
a real key cannot appear in this repository by accident.

## 5. The shape vocabulary

`shape` is a declared list of labels, and `validate.py` re-derives the same labels from
`account.json`. A label the bytes do not support is a problem. This is the only field in
the sidecar that is checked against content rather than form, and it exists so that a
consumer can pick fixtures by what they contain without re-implementing Horizon parsing.

| Label | Derived when |
|---|---|
| `no_signers` | `signers` is empty or absent |
| `single_signer` | exactly one signer |
| `multi_signer` | two or more signers |
| `master_is_signer` | a signer key equals `account_id` |
| `master_absent` | no signer key equals `account_id` |
| `thresholds_zero` | all three thresholds are 0 |
| `thresholds_nonzero` | any threshold is nonzero |
| `auth_required` | `flags.auth_required` is true |
| `auth_revocable` | `flags.auth_revocable` is true |
| `auth_immutable` | `flags.auth_immutable` is true |
| `auth_clawback_enabled` | `flags.auth_clawback_enabled` is true |
| `no_home_domain` | `home_domain` is absent or null |
| `blank_home_domain` | `home_domain` is a string that trims to empty |
| `has_home_domain` | `home_domain` is a non-blank string |
| `has_inflation` | `inflation_destination` is set |
| `no_inflation` | `inflation_destination` is absent or null |
| `has_data` | the `data` object is non-empty |
| `no_data` | the `data` object is empty or absent |
| `sponsored` | `num_sponsored` is greater than 0 |
| `not_sponsored` | `num_sponsored` is 0 |
| `sponsoring` | `num_sponsoring` is greater than 0 |
| `not_sponsoring` | `num_sponsoring` is 0 |
| `no_balances` | `balances` is an empty list |
| `many_balances` | `balances` has 10 or more entries |

Two reading notes:

- **`master_absent` means Horizon omitted the master key from `signers`, which is what a
  revoked master key looks like on the account resource.** The ledger does not carry a
  `master_key_revoked` boolean. A consumer that needs the difference between "revoked" and
  "never set" cannot get it from this corpus, and `sha256`-verified bytes are the only
  evidence either way.
- A derived field that is not an integer (a string, a bool, a list where a dict belongs)
  reads as absent or zero rather than raising. Types the schema does not police are a
  validator concern, not a crash.

`scenario` is prose and is not checked beyond the `synthetic:` prefix. Keep the numbers in
it out of the way: it describes why a fixture exists, and `shape` is the machine-readable
part.

## 6. Root documents

Every network used by any fixture must have `corpus/root-<network>.json`, and its
`network_passphrase` must be the one that network is supposed to have:

| Network | Passphrase |
|---|---|
| `public` | `Public Global Stellar Network ; September 2015` |
| `testnet` | `Test SDF Network ; September 2015` |

The root document is why a fixture cannot quietly be from somewhere else. `mainnet` and
`public` are the same network with different names in different tools; this corpus says
`public` because that is what Horizon and the passphrase both say.

## 7. Versioning

`schema_version` is 1. A key is added by adding it here, making `validate.py` accept it,
and shipping fixtures that use it. A key is renamed, a shape label changes meaning, or
`account.json` stops being verbatim bytes: that is version 2, and the validator has to
read both for a release cycle so consumers are not broken mid-flight. Nothing is a version
2 candidate today.

## 8. What this schema does not do

It does not say whether an account is well configured. It holds no expectations, no
severities, no rule ids and no policy: those belong to Gauge, which reads a real account
and evaluates rules, and to Airlock, which reads repositories. A fixture here is an input,
and the only claim it makes is that these bytes came from that URL on that date at that
ledger, or that a human wrote them and said so.
