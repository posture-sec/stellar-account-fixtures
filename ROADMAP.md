# ROADMAP: Stellar account fixtures

Last updated: 2026-11-02 13:00 UTC

A corpus of public Stellar account reads, their provenance, and the validator that keeps
the provenance honest. Nothing here is a claim about whether an account is well
configured; `SCHEMA.md` section 8 says what the corpus does not do.

## 0. The update rule (mandatory)

Every pull request in this repository updates this file in the same change:

1. Tick, untick or add the task line. A task is done only when it is merged and the
   evidence behind its `Done when` has been read, not asserted.
2. Add a row to the changelog in section 6: UTC date and time read from `date -u` at the
   moment of writing, what changed, which tasks it touches.
3. Regenerate the progress table: `python3 scripts/roadmap_progress.py`. It is derived
   data; a hand-edited row is a row that will be wrong.
4. Update `Last updated` at the top.

CI enforces steps 1 and 3 as the required `roadmap-check / gate` check.

## 1. What "ready" means

Ready means a consumer can pick a fixture by what it contains, verify that the bytes match
the sidecar, and know what is missing. It does not mean complete coverage: 24 shape labels
exist and 16 are captured, so the gap list in `README.md` is part of the product, and an
empty gap list is gate G2.

## 2. Progress

<!-- PROGRESS:START -->
| Phase | Name | Done | Total | Progress |
|---|---|---|---|---|
| 0 | Ground truth | 5 | 6 | 83% |
| 1 | Repository wrapper | 0 | 9 | 0% |
| 2 | Coverage | 0 | 6 | 0% |
| 3 | Consumer contract | 0 | 3 | 0% |
| **All phases** | **Readiness total** | **5** | **24** | **21%** |
| Gates | G1 to G5 | 0 | 5 | 0% |
<!-- PROGRESS:END -->

## 3. Readiness gates

- [ ] **G1** `python3 validate.py` exits 0 on the corpus in a hosted CI run, not only locally.
- [ ] **G2** Every shape label in `SCHEMA.md` 5 is covered by a captured fixture or by a synthetic fixture that says so, and the gap list in `README.md` is empty.
- [ ] **G3** No sidecar key goes unchecked: each key in `SCHEMA.md` 3 has a test that fails when a fixture lies about it.
- [ ] **G4** `main` is protected, both workflows are required checks, and a pull request that drops the roadmap edit is observed failing.
- [ ] **G5** At least one consumer (Gauge or Airlock) uses two or more fixtures in its own test suite and says which ones in that repository.

## 4. Current focus

Phase 0 is nearly closed and Phase 1 has not started on GitHub. The six captures and the
validator exist in the tree; the hosted CI run (1.3), the push refusal that proves the
ruleset (1.2) and the probe pull request that proves the gate (1.4) are the three claims
this repository cannot make from a laptop. Phase 2 is the corpus work that actually adds
value, and 2.2 and 2.4 are blocked on finding accounts with those shapes rather than on
code.

```
python3 validate.py --report
python3 -m unittest test_validate
ruff check . && ruff format --check .
mypy
```

## 5. Phases and tasks

### Phase 0: Ground truth (blocks everything)

- [x] **0.1** Decide the fixture format and write it down as `SCHEMA.md` version 1: two files per fixture, twelve sidecar keys, `captured` and `synthetic` kinds, and a synthetic fixture forbidden from carrying provenance it cannot have. S. Deps: none. Done when: `SCHEMA.md` exists and `validate.py` refuses every key it does not define. (done 2026-11-02: `SCHEMA.md` 3 is the key table and `load_manifest` reports `unknown key(s) in sidecar: ...`; `SidecarKeysAndTypes` and `CapturedProvenance` name the refusal for each row)
- [x] **0.2** Verify `G...` account ids by checksum, not by shape: 56 base32 characters decoding to a version byte of 48, 32 bytes of key material and a CRC16-XMODEM of the first 33 bytes appended little-endian. M. Deps: none. Done when: a typo in an account id is refused with a message, and a fabricated address cannot enter the corpus. (done 2026-11-02: `strkey_version` and the byte order are both tested; one flipped character returns `None`, and `test_encoder_and_decoder_are_inverses` covers versions 48, 96 and 144. The first version of this function compared the checksum big-endian and marked all six real accounts invalid, which is how the byte order was found)
- [x] **0.3** Refuse seed strings at both ends: `tools/capture.py` will not write a response containing a seed-shaped string, `validate.py` scans both files of every fixture, and the test suite builds its seed-shaped samples from zero bytes at run time. M. Deps: 0.2. Done when: a decodable seed and a seed-shaped fake each produce a distinct problem line. (done 2026-11-02: `SeedRefusal`, four cases; the decodable one says "and its checksum verifies" and the fake one does not)
- [x] **0.4** Capture six mainnet accounts with full provenance. M. Deps: 0.1, 0.2, 0.3. Done when: six directories validate, each sidecar names the URL, UTC capture second, `last_modified_ledger`, Horizon version and the SHA-256 of the bytes beside it. (done 2026-11-02: read from `horizon.stellar.org` on Horizon 30.0.0 at ledgers 65266813 to 65266866, all six pass `validate.py` and `test_the_shipped_corpus_validates`)
- [x] **0.5** The shape vocabulary: labels declared in the sidecar and re-derived from the account bytes, so a label cannot drift from the capture it describes. M. Deps: 0.1. Done when: `--report` prints the derived set for each fixture and a declared label the bytes do not support is a problem. (done 2026-11-02: 24 labels in `SCHEMA.md` 5, `DeclaredShapeVersusBytes` proves both directions, and `tools/capture.py` now labels a new capture from `shapes_of()` rather than by hand)
- [ ] **0.6** `scenario` is free prose and the validator cannot check it. One of the six already drifted: `issuer-auth-required` said "152 sponsorships" where `num_sponsoring` is 150, corrected in the commit that adds this line. Decide whether scenario text loses its numbers or gains a check. S. Deps: 0.5. Done when: either no sidecar `scenario` contains a count, or a test proves the counts in them.

### Phase 1: Repository wrapper

- [ ] **1.1** Create `posture-sec/stellar-account-fixtures` public, with the About description, homepage, topics and the wiki off. Public because the org's plan refuses rulesets and Pages on a private repository, and a corpus nobody can read is not a public good. M. Deps: none. Done when: the repository page shows the description and the topics, and `/wiki` serves no wiki.
- [ ] **1.2** A `protect main` ruleset requiring a pull request and both checks, observed by a direct push being refused against `main` itself. M. Deps: 1.1. Done when: the refusal text is quoted here with its date and `main` has not moved.
- [ ] **1.3** `.github/workflows/ci.yml`: unittest, `ruff check`, `ruff format --check` and `mypy` on Python 3.11, both actions pinned by commit SHA with the tag in the comment. M. Deps: 1.1. Done when: a hosted run is green and its date is recorded here. Until then the local run is a local run.
- [ ] **1.4** `.github/workflows/roadmap-check.yml` plus `scripts/check_roadmap_touched.sh` and `scripts/roadmap_progress.py` as a required check. M. Deps: 1.2, 1.3. Done when: a probe pull request that changes a file and not this document fails, and one that changes both passes, each observed on GitHub rather than inferred.
- [ ] **1.5** `.github/CODEOWNERS` naming the only member of the org across every protected path, with `require_code_owner_review` left off while one maintainer exists. M. Deps: 1.2. Done when: `GET /repos/posture-sec/stellar-account-fixtures/codeowners/errors` returns zero errors. Airlock's file was dead on arrival for a day because a suspended account was still named in it, and nothing in the UI said so.
- [ ] **1.6** `CONTRIBUTING.md`, `SECURITY.md`, `.github/pull_request_template.md` and the two issue templates. M. Deps: none. Done when: merged, and the hard rules in `CONTRIBUTING.md` match the refusals the code actually implements.
- [ ] **1.7** One issue per open task in Phases 0 to 3, no issue for a closed task. S. Deps: 1.1. Done when: the issue list and this file agree.
- [ ] **1.8** `tests/test_roadmap_gate.py`: run both gate scripts as subprocesses over a temporary roadmap and a temporary git repository, including the case where a branch passes the gate it is adding. S. Deps: 1.4. Done when: the suite covers a missing progress block and a phase heading with no tasks as errors rather than tracebacks.
- [ ] **1.9** An OSSF Scorecard run on `main`. S. Deps: 1.2. Done when: Branch Protection returns a score rather than a warning, which is what a ruleset on the default branch buys.

### Phase 2: Coverage

- [ ] **2.1** A fixture with `has_data`: an account carrying data entries. M. Deps: 0.4. Done when: it validates and `README.md`'s gap list loses that label.
- [ ] **2.2** A fixture with `sponsored` (`num_sponsored` above 0). Horizon has no index for "sponsored by anyone", so this needs a source for such an account, and if none is found the shape becomes a synthetic fixture with the reason recorded. M. Deps: 0.4. Done when: captured, or synthetic and labelled `synthetic:` with the reason in `scenario`.
- [ ] **2.3** A fixture with `no_balances`: an account that has never held a trustline. M. Deps: 0.4. Done when: it validates.
- [ ] **2.4** `master_absent` and `no_signers`: accounts whose master key was revoked, which is what Horizon omits it from `signers` for. These are rare and one of them is an unrecoverable account, so neither may be invented. M. Deps: 0.4. Done when: captured, or a written decision that the shape stays uncovered and why.
- [ ] **2.5** `auth_revocable`, `auth_immutable` and `auth_clawback_enabled`: three issuer accounts, one flag set each, not one issuer with all three. M. Deps: 0.4. Done when: all three labels appear in the report.
- [ ] **2.6** The first `testnet` capture, which also exercises `corpus/root-testnet.json`. Today the testnet branch of the validator is covered by tests and by nothing else. S. Deps: 0.4. Done when: a testnet fixture validates against the testnet passphrase.

### Phase 3: Consumer contract

- [ ] **3.1** `tools/manifest.py`: print one JSON line per fixture with id, account id, network, ledger and `sha256`, so a consumer can pin the corpus by content instead of by commit. M. Deps: 0.4. Done when: its output is reproducible from a clean checkout and a test asserts the line count equals the fixture count.
- [ ] **3.2** Gauge's rule tests read fixtures from here rather than carrying their own copies, which needs D-03 decided first. M. Deps: 3.1, D-03. Done when: a Gauge test names the fixture id it used.
- [ ] **3.3** Airlock's Stellar-side detectors use at least one fixture from here. S. Deps: 3.1. Done when: G5 is ticked with the two repository names.

## 6. Decision log

| ID | Decision | Status | Notes |
|---|---|---|---|
| D-01 | Captured beats synthetic. A shape is fabricated only after the search for a real account failed, and the sidecar has to say `synthetic` and start its `scenario` with `synthetic:`. | Accepted | The schema still allows synthetic fixtures because `master_absent` may be genuinely hard to find; what is not allowed is a synthetic fixture pretending to be a capture. |
| D-02 | Standard library only. `validate.py` and `tools/capture.py` import nothing outside it, and there is no package to install. | Accepted | Python 3.11 or newer for `tomllib`. A dependency would have to earn its place against a corpus that is read by tests in another language too. |
| D-03 | How a consumer takes the corpus: vendored copy, git submodule, or a download pinned by `tools/manifest.py`. | Open | Decides 3.2. Submodules break a contributor who has never used one, vendoring duplicates the bytes, and the download needs somewhere to host them; the org's plan refuses Pages on a private repository. |
| D-04 | No version tags until a consumer pins one. | Accepted | Mirrors Gauge's D-12. A tag on a six-fixture corpus invites the reading that the shape set is stable, and it is not. |
| D-05 | One account resource per fixture. No transactions, offers, effects or operations in version 1. | Accepted | `SCHEMA.md` section 2 defines what a fixture is; a second resource type is a schema discussion, not a new directory. |

## 7. Changelog

| When | What | Tasks |
|---|---|---|
| 2026-11-02 12:42 | Six mainnet accounts, `validate.py`, `tools/capture.py` and `test_validate.py` land in the first commit on `main`, captured from `horizon.stellar.org` on Horizon 30.0.0 at ledgers 65266813 to 65266866 and written as sorted-key JSON with one sidecar each. `validate.py` checks every sidecar against the bytes beside it and against the shape vocabulary. Eight defects were found by writing the tests and fixed in the same work, all of them in the code rather than in a fixture: `REQUIRED` demanded the five provenance keys from a `synthetic` fixture that `check_common` forbids them, so no synthetic fixture could ever validate; `load_manifest` read the sidecar with `read_text`, whose universal newlines turned CRLF into LF before the CRLF check could see it, so that check was dead code; `check_root` indexed `NETWORKS[network]` with an unvalidated key, so a sidecar naming a made-up network plus a file of that name raised instead of reporting; `shapes_of` did unguarded arithmetic and iteration over body fields, so a threshold written as a string crashed the validator rather than failing it; `tools/capture.py` accepted a `G`-shaped address whose CRC16 does not verify, so a typo cost a Horizon round trip instead of a refusal; its local refusals ran after the request rather than before it; the root document was parsed with no guard, so an HTML error page raised instead of refusing; and `urllib` follows a 3xx by default, which is the one that matters most here, because a redirect would have written bytes served from somewhere else under the URL the sidecar records as its source and the passphrase check on the root document would never have seen it. `fetch` now uses an opener that refuses a redirect, and the loopback suite covers that and the size cap. `issuer-auth-required`'s scenario said 152 sponsorships where the bytes say `num_sponsoring` is 150; corrected, and that drift is why 0.6 is open. `SCHEMA.md` is version 1, `README.md` states the eight uncovered labels rather than implying coverage, and its report block is the command's output with a staleness note rather than a hand-written list. Not verified: any GitHub state at all, since this document was written before the repository existed. Verified locally: `validate.py` exits 0, 95 tests pass on Python 3.12.3 and again on 3.11.16, `ruff check` and `ruff format --check` are clean, `mypy` is clean on three files, and the `shape` line `capture.py` now generates is byte-identical to the six already on disk. | 0.1 to 0.5, 0.6 left open |
| 2026-11-02 13:00 | The repository wrapper arrives as a pull request: this file, `CONTRIBUTING.md` with a rule table that names the refusal behind every rule, `SECURITY.md` with the scope written around provenance rather than around the accounts, `.github/CODEOWNERS`, the pull request template, two issue forms, `ci.yml` and `roadmap-check.yml` with both actions pinned by commit SHA, `requirements-dev.txt` pinning ruff 0.17.3 and mypy 2.4.0 so CI installs what the laptop ran, and `scripts/roadmap_progress.py` adapted from the Airlock script of the same name so the two repositories count tasks the same way. Its readiness row reads "All phases" because this roadmap has four phases and no backlog phase. `scripts/check_roadmap_touched.sh` also stops printing git's `fatal:` line when the base has no `ROADMAP.md`, which is the state of the first pull request in a repository; the comparison it feeds is unchanged and still empty there. No hosted evidence is claimed in this row: 1.1 to 1.4 and 1.7 stay open until the repository, the ruleset, a green run and the probe exist on GitHub, 1.5 stays open until `GET /repos/.../codeowners/errors` returns zero errors, and 1.6 stays open until this change is merged. | 1.3, 1.4, 1.5, 1.6, 1.7 left open |
