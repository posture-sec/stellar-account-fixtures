# Corpus directory guide

> How the two network root documents work, and what to do if a capture ever needs a third network.

The `corpus/` directory holds documents about the fixtures rather than fixtures themselves. Two of its files are data and are checked by the validator: `root-public.json` and `root-testnet.json`. Everything else here is reference prose.

## 1. What a root document is

A root document is the JSON that a Horizon server returns for `GET /` on its base URL. It names the server build, the ledger range it holds, and, most importantly for this corpus, the `network_passphrase` it serves. A fixture's `network` field says which network a capture came from, and the root document is the on-disk evidence that the server which answered used the passphrase that network is supposed to have.

That matters because a `G...` account id is valid on every Stellar network. Nothing in the id says which network it was read from, so without the root document a fixture could quietly be from somewhere else. The rule is in [SCHEMA.md](../SCHEMA.md) section 6.

## 2. The two root files

| Network | Root file | Horizon base URL | `network_passphrase` | Passphrase line |
|---|---|---|---|---|
| `public` | [`root-public.json`](root-public.json) | `https://horizon.stellar.org` | `Public Global Stellar Network ; September 2015` | line 103 |
| `testnet` | [`root-testnet.json`](root-testnet.json) | `https://horizon-testnet.stellar.org` | `Test SDF Network ; September 2015` | line 107 |

Both files are written by `tools/capture.py` in the same run that writes a fixture, serialised with sorted keys, indent 2 and a trailing newline. Do not reformat or hand-edit them. The files also record volatile fields such as the latest ledger at the time of the read, so they are a snapshot, not a live view of the network. For a field-by-field comparison of the two, see [root-diff.md](root-diff.md).

## 3. How the validator uses them

Every network that any fixture declares must have a root file named `root-<network>.json` in this directory, and its `network_passphrase` must equal the passphrase the validator holds for that network.

- The expected passphrases live in the `NETWORKS` mapping in `validate.py` (line 49), next to the base URL used to check each sidecar's `source_url`.
- `check_root` in `validate.py` (line 444, called from `validate()`) enforces the rule for each network in use. It reports four conditions: the file is missing, the file is not JSON, the JSON is not an object, and the passphrase does not match.
- Only networks that a fixture references are checked. A root file for an unused network would be ignored, which is why a third root file must arrive in the same change as the first fixture that needs it.

Line numbers in this file are as of the commit that added it. The names `NETWORKS` and `check_root` are the stable references; use them if the numbers have moved.

## 4. Adding a third network

Only do this when a real capture needs it. The corpus describes what the chain shows, so a network with no capture has no root file.

1. Confirm the Horizon endpoint and the network's official passphrase from the network operator's documentation. If the operator does not publish a passphrase, stop and ask on the issue before going further.
2. Add the network to both tables that hold it: `NETWORKS` in `validate.py` (base URL and passphrase) and `ENDPOINTS` plus `PASSPHRASES` in `tools/capture.py`. They are separate constants today, so a network added to one and not the other is refused by one tool and accepted by the other.
3. Capture a fixture with `python3 tools/capture.py --network <name> --account G... --id <fixture-id> --scenario "..."`. The tool fetches the root document, refuses the capture if the passphrase does not match, and writes `corpus/root-<name>.json` for you.
4. Run `python3 validate.py` and the test suites listed in [CONTRIBUTING.md](../CONTRIBUTING.md). Add tests for the new network in the same pull request.
5. Add a row for the network to the table in [SCHEMA.md](../SCHEMA.md) section 6, add it to the table in section 2 of this file, and update the roadmap as `CONTRIBUTING.md` requires.

Do not copy a root document from another network and edit the passphrase, and do not write a root file by hand. A root file whose bytes did not come from the endpoint it names defeats the purpose of having one.

## 5. Other documents in this directory

| File | What it covers |
|---|---|
| [`provenance.md`](provenance.md) | Account id, network, ledger, capture time, Horizon version and digest for each fixture |
| [`shape-matrix.md`](shape-matrix.md) | Which fixture carries which shape label |
| [`signers.md`](signers.md) | Signer counts and master key weights |
| [`thresholds.md`](thresholds.md) | The exact low, medium and high threshold triples |
| [`data-entries.md`](data-entries.md) | The coordinator data entry, decoded |
| [`root-diff.md`](root-diff.md) | The two root documents, compared field by field |
