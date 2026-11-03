# Contributing to the fixtures corpus

This is a corpus with a validator attached, so the bar for a change is the bar for a
fixture: it cannot produce a false pass. Read `SCHEMA.md` before touching a fixture and
`ROADMAP.md` section 0 before opening a pull request.

## Status

Six mainnet captures, `validate.py`, `tools/capture.py` and 95 tests exist and pass in a
local checkout on Python 3.11.16 and 3.12.3, and the same suite is green in this
repository's own CI on a 3.11 runner. `main` refuses a direct push and both checks are
required status checks, so a pull request that skips `ROADMAP.md` fails at the gate rather
than at review. No tag, no release, nothing to install. An OSSF Scorecard run on `main`
published on 2026-11-03 scores the repository 5.2 overall, with Branch-Protection at 4 rather
than erroring; most of the gap is a repository with one maintainer, one contributing company
and nothing to publish, and `ROADMAP.md` 1.9 says which of those numbers mean anything for a
corpus. What is open is in `ROADMAP.md` section 4, and a claim there is backed by a named run or
says that it is not.

## The rules, and what enforces each one

Each rule below is a refusal in the code rather than advice. Break one and something exits
non-zero and says why in one line.

| Rule | Enforced by |
|---|---|
| A fixture is written by `tools/capture.py`, never by hand. | The tool computes `sha256` over the exact bytes it writes, so an edited `account.json` reports `sha256 does not match account.json`, and `unexpected file(s)` and `missing file(s)` refuse a directory with a third file or only one. |
| Only `G...` account ids. | `capture.py` refuses anything that is not `G...` with the message `M... and C... addresses are not captured here`, and refuses a `G`-shaped address whose CRC16-XMODEM checksum does not verify before it makes any request. `validate.py` reports `is not a valid G... strkey` for the same address in a sidecar. |
| No key material, ever. | `capture.py` refuses a body containing a seed-shaped string. `validate.py` runs `seed_findings` over both files of every fixture. The decodable sample in the test suite is built at run time from thirty-two zero bytes, so nothing in this tree is a key. |
| The network is explicit and its passphrase is verified. | `capture.py` reads the endpoint root document and refuses when `network_passphrase` is not the passphrase that network carries. A `G` account id on the wrong network is still a valid id, so nothing else catches it. |
| A redirect is not the source you recorded. | `fetch` uses an opener that refuses a 3xx. `Loopback` in `test_validate.py` proves the refusal, and `corpus/root-<network>.json` holds the root document the passphrase was read from. |
| One request, capped. | `ACCOUNT_CAP` and `ROOT_CAP` bound the two bodies, and a response describing a different account than the one requested is refused rather than renamed. |
| Shape labels are derived, not declared. | `capture.py` labels a capture with `shapes_of()` from `validate.py`, so there is one definition of a label. A sidecar that claims a label the bytes do not support reports `declared shape 'x' is not what account.json shows`, and the missing direction is reported too. |
| A synthetic fixture says so. | `SCHEMA.md` 3: `kind = "synthetic"` may carry none of the five provenance keys and its `scenario` must start with `synthetic:`. `SyntheticFixtures` covers both halves. |
| Standard library only. | D-02 in `ROADMAP.md`. `validate.py` and `tools/capture.py` import nothing outside it. `requirements-dev.txt` is dev tooling, not a runtime dependency. |
| Tests do not touch the network. | The only sockets in the suite are two loopback HTTP servers created inside the test process. `FakeHorizon` patches `capture.fetch` and records every URL it is asked for, so each local refusal asserts that the account was never requested. |
| Never weaken, skip or delete a check to make something pass. | If a test is wrong, fix the test and say why in the pull request. If a check is wrong, the check is the bug and the PR is about the check. |

## Workflow

1. Find the task in `ROADMAP.md`. If it does not exist, add it with the next free ID in its
   phase and say why in the issue.
2. Check its `Deps:` are done. If they are not, stop and report that on the issue.
3. Branch from `main` as `feat/<task-id>-<slug>`. `main` is protected once 1.2 lands; before
   that it is still the rule.
4. Write the failing test first and watch it fail for the right reason.
5. Implement the smallest change that passes.
6. Run the checks below and paste the actual output in the pull request.
7. Update the docs the change touches: `SCHEMA.md` for anything about the format,
   `README.md` for the gap list and the fixture table, this file for a rule.
8. Update `ROADMAP.md` in the same pull request: the task box, a changelog row with the UTC
   time from `date -u` at the moment of writing, then `python3 scripts/roadmap_progress.py`,
   then the `Last updated` line. A task is not done until this file is current.
9. One pull request per task, or per one tightly related group.

## Checks

```bash
python3 validate.py
python3 -m unittest test_validate
ruff check . && ruff format --check .
mypy
scripts/check_roadmap_touched.sh origin/main
python3 scripts/roadmap_progress.py --check ROADMAP.md
```

`ruff` and `mypy` are pinned in `requirements-dev.txt`, the file CI installs from, so a local
run and a hosted run use the same two versions. `mypy` reads its target list from
`pyproject.toml`; three files are type-checked, including the test suite.

## When a shape is missing

`README.md` lists eight labels with no fixture. Close one in this order:

1. Find a real account with that shape. Say which one, on which network, in the issue.
2. Capture it:

   ```bash
   python3 tools/capture.py --network public --account G... \
     --id my-new-shape --scenario "one sentence on why this shape is missing"
   python3 validate.py
   ```

3. Only if the search failed, write a synthetic fixture, and put the reason in `scenario`.
   D-01 is that captured beats synthetic; the schema allows a synthetic fixture so a rare
   shape is not unreachable, and forbids it from claiming a ledger, a URL or a digest.
4. Update the gap list in `README.md`, tick the roadmap task, and record the date and the
   evidence in the changelog row.

Use `--update` to replace a fixture you are intentionally re-capturing. It is the only way a
captured fixture changes after it is on disk, and a re-capture at a later ledger is a new
fact about the same account, so the changelog row has to say which ledger it replaced.

## Issues

One issue per open roadmap task, with the task's `Done when` line as the acceptance criteria.
For a shape the corpus lacks, use the fixture request template; it asks for the account id
and the network, which is the whole difference between a search that ended and a wish.

## Naming and writing

Fixture ids are kebab-case, are part of the contract, and are never reused: a fixture that
leaves the tree takes its id with it (`SCHEMA.md` 7). Shape labels are
`snake_case` tokens from the vocabulary in `SCHEMA.md` 5. Docs, comments and commit messages
use plain language with no em dashes, comments explain why rather than what, and commits
follow Conventional Commits with the subject under 72 characters. This repository describes
what the chain shows; it never calls an account secure or safe.
