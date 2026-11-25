# Home Domain Values

> Raw `home_domain` values in all nine captured account resources, including the whitespace-only case.

## 1. Context

Stellar's [SEP-1 discovery process](https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0001.md)
uses an account's home domain to locate its `stellar.toml` file at
`https://<home_domain>/.well-known/stellar.toml`. A home domain is a discovery
starting point, not proof that a document exists there.

The table records the `home_domain` member exactly as encoded in each
`account.json`. Quoted values are JSON strings. `omitted` means the JSON object
has no `home_domain` member; it does not mean the member is `null`. None of these
nine captures has an explicit `null` value.

## 2. Values across the corpus

| Fixture | Raw JSON value or key state | Derived shape |
|---|---|---|
| `asset-heavy-exchange` | `"stellarterm.com"` | `has_home_domain` |
| `coordinator-data-entry` | omitted | `no_home_domain` |
| `default-plain` | omitted | `no_home_domain` |
| `domain-and-inflation` | `"lobstr.co"` | `has_home_domain` |
| `issuer-auth-required` | omitted | `no_home_domain` |
| `multisig-custody` | omitted | `no_home_domain` |
| `sponsored-trustlines` | `"sl8.online"` | `has_home_domain` |
| `testnet-multisig` | omitted | `no_home_domain` |
| `whitespace-home-domain` | `" "` | `blank_home_domain` |

The final row is a JSON string containing exactly one ASCII space (U+0020).
The quotes make the value visible in Markdown and distinguish it from an empty
string (`""`) and from an omitted member.

## 3. Shape derivation

[`SCHEMA.md` section 5, lines 154-156](../SCHEMA.md#5-the-shape-vocabulary)
defines `no_home_domain` for an absent or null value, `blank_home_domain` for
a whitespace-only string, and `has_home_domain` for a non-blank string. In
[`validate.py:194-199`](../validate.py#L194), `shapes_of` first classifies
`None` as `no_home_domain`, then checks `home_domain.strip() == ""` for
`blank_home_domain`, and otherwise derives `has_home_domain`. Consequently, an
absent member and an explicit JSON `null` both become `None` through
`account.get("home_domain")`, while the single-space string remains present and
is classified as blank.

See the [shape label matrix](shape-matrix.md) for all shape labels across the
nine captures, and the [schema](../SCHEMA.md) for their contract.
