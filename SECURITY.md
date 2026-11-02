# Security policy

## Reporting a vulnerability

Report it privately through
[a security advisory](https://github.com/posture-sec/stellar-account-fixtures/security/advisories/new).
Do not open a public issue for it. This is a one-maintainer project, so expect an
acknowledgement within seven days.

Include the command you ran, the exit code, the fixture directory or the file that shows the
problem, and the output of `python3 validate.py --report`. Account ids are public ledger
state, so leave them in. **Never paste a secret seed (`S...`) into a report or an issue.** If
a seed did reach a file in this tree, treat the key as compromised, move it, then report.

## What is in scope

A vulnerability here is anything that lets a false statement about provenance, or unwanted
key material, into a corpus that other projects' tests read:

- A fixture whose bytes do not match what its sidecar claims: a digest that verifies over
  edited content, a `source_url` that never served those bytes, a `captured_at` or `ledger`
  that does not describe the capture, or a redirect whose 3xx target was written under the
  name of the original URL.
- A secret seed or any other private key material that `tools/capture.py` writes, or that
  `validate.py` accepts.
- `validate.py` exiting 0 on a tree it should refuse. Examples that matter: a `shape` label
  the account bytes do not support, an unknown sidecar key accepted silently, two fixtures
  with the same account id, a fixture directory with a third file in it.
- `tools/capture.py` writing outside `fixtures/<id>/`, or reading a URL other than the two it
  documents. The fixture id is checked against an anchored kebab-case pattern for this
  reason.
- A capture against a network whose `network_passphrase` does not match the network named in
  the sidecar, or a root document that was never verified before the account read.
- A workflow step that can be edited by the pull request it is supposed to check, or an
  action that is not pinned by commit SHA.

## What is out of scope

- The configuration of any account in this corpus. These are real mainnet accounts and the
  point of publishing them is that the chain already does. A report that `issuer-auth-required`
  has a bad threshold is not a vulnerability here; it is a finding for Gauge.
- A missing shape. The eight uncovered labels are listed in `README.md` and are roadmap
  tasks, not a defect.
- The public data itself. Horizon responses are ledger state, so there is nothing to redact
  and no privacy claim to make against a fixture.
- Vulnerabilities in Horizon, Stellar Core, the SDKs or the public endpoints.
- Anything reproduced only in a fork or an untagged commit, unless it also reproduces on
  `main`.

## Known limits, stated plainly

**Unaudited.** No third party has reviewed this code.

**The validator is only as strict as its tests.** Eight defects were found while writing
`test_validate.py` and fixed there, including one where `urllib` followed a redirect and would
have written bytes served from somewhere else under the URL the sidecar records. A ninth may be
waiting; the suite is 95 cases, not a proof.

**No hosted run yet.** The checks that matter today (`validate.py`, the test suite, `ruff`,
`mypy`) have been run on a laptop on Python 3.11.16 and 3.12.3. Phase 1 tasks 1.2 and 1.3
cover branch protection and the hosted CI run, and until they are ticked nothing here should
be read as "CI is guarding this". See `ROADMAP.md` section 4.

**`scenario` is unchecked prose.** It is free text, and one of the six already drifted from
the bytes it described. Task 0.6 is open on that. A sidecar can therefore be accurate about
every field the validator checks and still describe the account badly in one sentence.

**Provenance is a claim about a moment.** A fixture records the account as Horizon served it
at one ledger. The account may have changed since, and nothing here detects that; a consumer
comparing a live read to a fixture is comparing two different times.

## What this corpus cannot tell you

It records what the chain showed. It does not rate an account, does not say a configuration
is good or bad, and does not claim any account here is secure or well run. Five of the six
are ordinary mainnet accounts chosen for their shape, not for their owner's decisions.
