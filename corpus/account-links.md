# What account `_links` does and does not prove

> The `_links` object in every `account.json` is navigation that Horizon wrote into the response. It records no provenance, and a consumer should not use it to decide where a fixture came from.

## 1. What `_links` is

Every `account.json` begins with a `_links` object. It is the hypermedia block Horizon adds to an account resource: for each related resource it gives a URL, so a client can move from the account to its transactions, operations, offers and so on without building URLs itself.

All thirteen captures carry the same eight relations. The fourteenth fixture, `null-home-domain`, is synthetic: it has no `source_url`, and its `account.json` has no `_links` at all, so nothing in this document applies to it.

| Relation | `href` pattern (after the base URL) | Templated |
|---|---|---|
| `self` | `/accounts/<account-id>` | no |
| `data` | `/accounts/<account-id>/data/{key}` | yes |
| `effects` | `/accounts/<account-id>/effects{?cursor,limit,order}` | yes |
| `offers` | `/accounts/<account-id>/offers{?cursor,limit,order}` | yes |
| `operations` | `/accounts/<account-id>/operations{?cursor,limit,order}` | yes |
| `payments` | `/accounts/<account-id>/payments{?cursor,limit,order}` | yes |
| `trades` | `/accounts/<account-id>/trades{?cursor,limit,order}` | yes |
| `transactions` | `/accounts/<account-id>/transactions{?cursor,limit,order}` | yes |

A templated `href` is a URI template, not a URL: `{key}` and `{?cursor,limit,order}` have to be expanded by the client before the link can be requested.

With the host and the account id replaced by placeholders, the `_links` of all thirteen captured files are identical. The only things that differ between fixtures are the Horizon host and the account id that Horizon filled in. Every `href` in a fixture also begins with the same host as that fixture's `source_url`.

## 2. What it does not prove

`_links` is text that the Horizon server chose to write. It is part of the bytes the capture tool stored, so it is covered by the `sha256` in the sidecar, but covering a field with a digest only shows that the file has not changed since the sidecar was written. It does not show that the field is true.

Specifically, `_links`:

- does not identify the network. A testnet server writes testnet URLs and a mainnet server writes mainnet URLs, but any server, proxy or private deployment can write any host into this block, and a hand-edited file could say anything.
- does not say when the read happened or at which ledger.
- is not checked by the validator. As of the commit that added this document, neither `validate.py` nor `tools/capture.py` reads `_links`, so a fixture whose links contradicted its sidecar would still validate.
- cannot be trusted as a redirect target. Following a link from a fixture requests whatever host the file names, and this corpus does not fetch them.

The account id inside the links is a copy of the same `id` the file carries elsewhere, so it adds no independent evidence either.

## 3. What the provenance record actually is

The facts about where a fixture came from live in the sidecar `fixture.toml` and in the root document, not in `_links`. See [SCHEMA.md](../SCHEMA.md) section 2 for how `account.json` is stored and section 3 for the sidecar keys.

| Evidence | Where it lives | What it tells you | What it cannot tell you |
|---|---|---|---|
| `source_url` | sidecar | the exact URL the tool requested; `validate.py` requires it to equal the network's Horizon base URL plus `/accounts/<account_id>` | that the server told the truth |
| `network` and the root document | sidecar and `corpus/root-<network>.json` | which network was asked for, and that the server answering reported that network's passphrase when the capture ran | anything about later ledgers |
| `captured_at`, `ledger`, `horizon_version` | sidecar | when, at which ledger, and by which server build | that the clock or the server was correct |
| `sha256` | sidecar | that `account.json` is the file the tool wrote | that the file came from Horizon in the first place |
| `_links` | `account.json` | which URLs Horizon suggested for related resources | none of the above |

None of these is a signature. Horizon responses are not signed, so this corpus records claims with the evidence that supports each one, and it never says an account is safe or secure. What the tool does enforce is that a capture refuses a redirect, refuses an endpoint whose passphrase is wrong, and refuses a response that describes a different account than the one requested. Those refusals are what make `source_url` and the root document worth reading. `_links` adds nothing to them.

## 4. Public and testnet side by side

The `self` link of two captures, set against the `source_url` in each sidecar:

| | `default-plain` (public) | `testnet-multisig` (testnet) |
|---|---|---|
| `network` in sidecar | `public` | `testnet` |
| `source_url` in sidecar | `https://horizon.stellar.org/accounts/GA7DTK7GPOEQGXHI7MLA2OAIEL4365VG6PXUAVREMDVLC4MJIJ62KR75` | `https://horizon-testnet.stellar.org/accounts/GCI76XDVHDGJMZGP5EWQYCZCYIBNBVABLPHWCKEZWJF2K4Z5SD74A4AV` (`fixture.toml` line 8) |
| `_links.self.href` in `account.json` | the same URL | the same URL |
| `_links.transactions.href` | `https://horizon.stellar.org/accounts/GA7D.../transactions{?cursor,limit,order}` | `https://horizon-testnet.stellar.org/accounts/GCI7.../transactions{?cursor,limit,order}` |

The relations are identical and only the host differs, which is exactly why `_links` cannot tell a consumer more than the sidecar already does. In the testnet capture the sidecar line is the evidence. The matching link in `account.json` is a copy of it that Horizon happened to include.

The two root documents show the contrast one level up. Their `_links` also differ only by host, but there the field that carries the weight is `network_passphrase`, which is checked (see [README.md](README.md) in this directory and [root-diff.md](root-diff.md)).

## 5. Guidance for consumers

- Select and verify fixtures with the sidecar: `network`, `source_url`, `ledger` and `sha256`, and `python3 tools/manifest.py` to pin by content.
- Treat `_links` as decoration. Do not branch on its host, do not follow its URLs from a test, and do not use it to infer which network a file came from.
- If a parser needs to compare two account resources from different networks, ignore `_links` or compare it after replacing the host and id.
- If a tool needs custom handling of `_links` (for example expanding templates), keep that code in the consumer. This corpus stores the bytes and does not interpret them.

Existing `account.json` files are never edited to clean up or adjust their links. A fixture whose bytes were changed no longer matches its `sha256`.
