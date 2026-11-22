# Worked Re-capture and Replacement Workflow

This document illustrates the re-capture and replacement workflow defined in `SCHEMA.md` Section 7, using `fixtures/sponsored-trustlines` as a specimen example.

> Note: This document provides a worked illustrative workflow. The shipped files under `fixtures/sponsored-trustlines/` remain at their captured ledger to maintain reproducibility for downstream test suites.

## 1. Decision Criteria: Re-capture vs New Fixture

Before refreshing any fixture bytes using `tools/capture.py --update`, maintainers must evaluate the following decision criteria:

| Scenario | Permissible Action | Rationale |
|---|---|---|
| Account state changed, but derived shape labels and scenario are unchanged | **Re-capture permitted** (`--update`) | Updates byte freshness without breaking consumer expectations |
| Account gained or lost signers, thresholds, flags, or trustline states that alter derived shape labels | **New fixture required** | Consumers pin fixtures for specific shape testing; mutating shapes breaks tests |
| Account was merged or closed on chain | **Retain existing capture** | Historical specimen provenance remains valid for that ledger |

If any derived shape label emitted by `validate.py shapes_of` would change, the maintainer must not overwrite the existing fixture. Instead, create a new fixture directory with a new descriptive ID (e.g., `fixtures/sponsored-multisig/`).

## 2. Worked Specimen Workflow: `fixtures/sponsored-trustlines`

### Step 1: Inspect Current Fixture State

Check the current sidecar metadata in `fixtures/sponsored-trustlines/fixture.toml`:

```toml
id = "sponsored-trustlines"
kind = "captured"
account_id = "GCPEC2WSEJPAFPLPPDPBU3XI6SXHJUZD2KLUA6BBBPO7WES3W5ZKDE54"
network = "public"
captured_at = "2026-11-03T09:50:41Z"
ledger = 65110665
sha256 = "66f488f28df4192b0051e8a011feee2e0c1f513511eb0041dc84b901509eb34a"
shape = [
  "has_home_domain",
  "many_balances",
  "master_is_signer",
  "multi_signer",
  "no_data",
  "no_inflation",
  "not_sponsoring",
  "sponsored",
  "thresholds_nonzero",
]
```

### Step 2: Fetch Live State and Verify Shape Parity

Query Horizon to verify that the live account still produces the exact same shape set:

```bash
python3 -c '
import json, urllib.request, validate
url = "https://horizon.stellar.org/accounts/GCPEC2WSEJPAFPLPPDPBU3XI6SXHJUZD2KLUA6BBBPO7WES3W5ZKDE54"
req = urllib.request.Request(url, headers={"User-Agent": "recapture-check"})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
live_shapes = sorted(validate.shapes_of(data))
print("Live shapes:", live_shapes)
'
```

If `live_shapes` equals the existing `shape` list in `fixture.toml`, re-capture is permissible.

### Step 3: Execute Re-capture with `--update`

Execute `tools/capture.py` with `--update`:

```bash
python3 tools/capture.py \
  --network public \
  --account GCPEC2WSEJPAFPLPPDPBU3XI6SXHJUZD2KLUA6BBBPO7WES3W5ZKDE54 \
  --id sponsored-trustlines \
  --scenario "num_sponsored 17 against num_sponsoring 0: seventeen balances and two signers, the account whose own entries are paid for by someone else, which no earlier capture showed" \
  --update
```

The tool refreshes `account.json` verbatim, recomputes the SHA-256 digest, updates `ledger`, `captured_at`, and `horizon_version`, and confirms that the derived shape set matches the sidecar.

### Step 4: Validate the Whole Corpus

Verify that the updated fixture and entire corpus pass validation:

```bash
python3 validate.py
python3 -m unittest discover -s tests -t tests
```

### Step 5: Document in `ROADMAP.md` Changelog

Every re-capture must be recorded in `ROADMAP.md` Section 7 (Changelog):

```markdown
| YYYY-MM-DD HH:MM | Re-capture fixtures/sponsored-trustlines at ledger <new_ledger> (was 65110665), SHA-256 <new_sha256>. Shape labels verified invariant across re-capture. | none ticked |
```

Update `Last updated` in `ROADMAP.md` and run `python3 scripts/roadmap_progress.py` to regenerate the progress table.
