# Drips Wave submission packet: stellar-account-fixtures

Last checked: 2026-11-09T14:48Z. Prepared for Stellar Wave 11 (opening 2026-11-18T14:00:35Z, closing 2026-11-25T14:00:55Z, $75,000 USD budget).

This packet prepares `posture-sec/stellar-account-fixtures` for application into the Drips Wave program alongside its sibling security tooling repositories (`posture-sec/airlock`, `posture-sec/guage`, and `posture-sec/stellar-posture-watch`).

## 1. Project description (plain English)

`stellar-account-fixtures` is an open-source corpus of real Stellar account configurations captured live from Horizon (mainnet and testnet), re-serialized deterministically, and cryptographically pinned with individual SHA-256 sidecars. Account security tools (like Gauge and Airlock) audit account permissions, thresholds, signers, and flags; testing detection logic against synthetic or hand-typed mocks frequently misses edge cases that real chain history produces. This corpus provides 9 captured real-world account structures (covering multi-sig treasuries, sponsors, data entries, and multi-signer tiers), verified by a deterministic `validate.py` harness and captured via a safe `tools/capture.py` CLI that enforces address checksums, Horizon network passphrases, and payload integrity.

## 2. Current repository status

| Surface | State | Evidence |
|---|---|---|
| Captures | 9 accounts | 8 mainnet captures, 1 testnet capture (`testnet-multisig`); all 9 sidecars recording Horizon `30.0.0-b3ff4119` |
| Tests | 115 passing | 97 test cases in `test_validate.py`, 18 subprocess gate cases in `tests/test_roadmap_gate.py` |
| Verification | Clean | `validate.py` exits 0 (all SHA-256 checksums match and shape declarations pass) |
| Documentation | Live site | `https://posture-sec.github.io/stellar-account-fixtures/` deployed via GitHub Pages |
| Security & Badges | Scorecard 5.2 | OpenSSF Scorecard workflow active on `main`; dynamic Shields.io endpoints live at `site/data/` |
| Protection | Enforced | Ruleset 26367047 enforcing strict checks (`ci / python`, `roadmap-check / gate`), direct push refused |

## 3. Supporting links

- Repository: `https://github.com/posture-sec/stellar-account-fixtures`
- Documentation site: `https://posture-sec.github.io/stellar-account-fixtures/`
- Schema and verification contract: [`SCHEMA.md`](https://github.com/posture-sec/stellar-account-fixtures/blob/main/SCHEMA.md)
- Validator implementation: [`validate.py`](https://github.com/posture-sec/stellar-account-fixtures/blob/main/validate.py)
- Roadmap and progress: [`ROADMAP.md`](https://github.com/posture-sec/stellar-account-fixtures/blob/main/ROADMAP.md)

## 4. Planned issues for Wave 11

The open backlog contains 11 issues, including 4 scoped tasks tagged with `Stellar Wave` that invite contributors to expand corpus coverage or tooling:

1. **Issue #13 (`feat(fixtures): capture an auth_revocable account`)**
   - *Tier:* Medium (150 pts).
   - *Work:* Identify a real mainnet or testnet account with `auth_revocable = true` (and optional `auth_required`), capture it using `tools/capture.py`, verify sidecar checksum, and register the shape in `SCHEMA.md`.
2. **Issue #14 (`feat(fixtures): capture an account with sponsor entries`)**
   - *Tier:* Medium (150 pts).
   - *Work:* Capture an account demonstrating `num_sponsored` or `num_sponsoring` > 0 from live Horizon, verifying the sponsorship mechanics against `validate.py`.
3. **Issue #15 (`feat(fixtures): capture the zero-balance account shape`)**
   - *Tier:* Trivial (100 pts).
   - *Work:* Capture a live account holding exactly 0 XLM or minimal reserve with no additional asset trustlines.
4. **Issue #17 (`feat(tools): print a machine-readable fixture manifest`)**
   - *Tier:* Trivial (100 pts).
   - *Work:* Add a `--manifest` JSON output flag to `validate.py` or `tools/capture.py` that summarizes all registered captures, their ledger heights, and SHA-256 digests.
5. **Issue #7 (`fix(schema): decide whether home_domain without SEP-1 is a valid shape`)**
   - *Tier:* Trivial (100 pts).
   - *Work:* Resolve schema declaration for domain accounts that do not host a readable `stellar.toml`.
6. **Issue #18 (`feat(consumers): point Gauge's rule tests at this corpus`)**
   - *Tier:* Medium (150 pts).
   - *Work:* Update Gauge integration test suite to read account states directly from this submodule or repository.
7. **Issue #19 (`feat(consumers): use one captured fixture in Airlock's SEP test`)**
   - *Tier:* Trivial (100 pts).
   - *Work:* Import one captured test fixture into Airlock's SEP-1 parser verification suite.

## 5. Maintainer runbook

1. Sign into **[Drips Maintainer Dashboard](https://www.drips.network/maintainers)** with GitHub organization permissions.
2. Select `posture-sec/stellar-account-fixtures` and apply to the Stellar Wave program with the text from Section 1.
3. Confirm repository application approval on the dashboard before the active wave begins.
4. On the Issues dashboard, assign appropriate tiers (Trivial, Medium, High) to the designated Wave issues.
5. Review contributor pull requests, verify `validate.py` passes, and mark issues resolved before the wave closes on 2026-11-25.
