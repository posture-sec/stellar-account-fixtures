# Optional Account Key Coverage Matrix

Stellar Horizon account resources contain optional fields that appear only under specific account states. This matrix maps the coverage of optional account fields across all fixtures in the corpus to identify parser coverage and schema gaps.

For field handling specifications and derivation rules, see [SCHEMA.md:27](../SCHEMA.md#2-accountjson) and [validate.py:171](../validate.py#L171).

## Horizon Optional Key Matrix

Values below have been verified directly against `account.json` files on disk. In accordance with Stellar Horizon API conventions, omitted keys are not returned with null literals; rather, the key is absent from the JSON payload. Where a field is present, the observed value or structural type is recorded.

| Fixture ID | `sponsor` | `num_sponsored` | `num_sponsoring` | `home_domain` | `inflation_destination` | `data` |
|---|---|---|---|---|---|---|
| `asset-heavy-exchange` | absent | present (0) | present (127) | present (`stellarterm.com`) | absent | present (`{}`) |
| `coordinator-data-entry` | absent | present (0) | present (4135797) | absent | absent | present (`config.multisig.coordinator`) |
| `default-plain` | absent | present (0) | present (0) | absent | absent | present (`{}`) |
| `domain-and-inflation` | absent | present (0) | present (2) | present (`lobstr.co`) | present (`GDCH...4VW`) | present (`{}`) |
| `issuer-auth-required` | absent | present (0) | present (150) | absent | absent | present (`{}`) |
| `liquidity-pool-share` | absent | present (0) | present (0) | present (`lu.meme`) | absent | present (`{}`) |
| `multisig-custody` | absent | present (0) | present (0) | absent | present (`GA6W...ID3`) | present (`{}`) |
| `sponsored-trustlines` | present (`GDB3...6CU`) | present (17) | present (0) | present (`sl8.online`) | absent | present (`{}`) |
| `testnet-multisig` | absent | present (0) | present (0) | absent | absent | present (`{}`) |
| `whitespace-home-domain` | absent | present (0) | present (12) | present (` `) | present (`GCLG...BEW`) | present (`{}`) |

## Field Analysis and Parser Implications

### 1. `sponsor`
- **Presence**: Present in exactly 1 capture (`fixtures/sponsored-trustlines/account.json:6`). Absent in all other 9 captures.
- **Nullness**: Never explicitly serialized as `null` by Horizon; when an account has no sponsor, the key is omitted entirely.
- **Handling**: Parsers must treat `sponsor` as an optional string. Accessing `account["sponsor"]` without `.get()` or an existence check will raise `KeyError`.

### 2. `num_sponsored` and `num_sponsoring`
- **Presence**: Present across all 10 captures as integers.
- **Values**: `num_sponsored` is 0 on 9 captures and 17 on `sponsored-trustlines`. `num_sponsoring` ranges from 0 up to 4,135,797 (`coordinator-data-entry`).
- **Handling**: These fields represent active sponsorship counts introduced in Protocol 14. They are standard integer counters on all modern Horizon responses.

### 3. `home_domain`
- **Presence**: Present in 5 captures (`asset-heavy-exchange`, `domain-and-inflation`, `liquidity-pool-share`, `sponsored-trustlines`, `whitespace-home-domain`). Absent in the other 5 captures.
- **Edge cases**: `whitespace-home-domain` contains a single space string (`" "`), exercising parsers that fail to distinguish empty strings or whitespace from absent domains.
- **Derivation**: `validate.py:171` derives `no_home_domain` when the key is absent or null, `blank_home_domain` when whitespace-only, and `has_home_domain` when populated with non-blank characters.

### 4. `inflation_destination`
- **Presence**: Present in 3 captures (`domain-and-inflation`, `multisig-custody`, `whitespace-home-domain`). Absent in the other 7 captures.
- **Protocol note**: Inflation was disabled in Stellar Protocol 12, but accounts with pre-existing destinations continue to return the field in Horizon payloads.
- **Handling**: Parsers must treat `inflation_destination` as optional.

### 5. `data`
- **Presence**: Present as an object across all 10 captures.
- **Entries**: Populated with key-value entries in `coordinator-data-entry` (`config.multisig.coordinator`), and present as an empty object (`{}`) on the remaining 9 captures.
- **Derivation**: `validate.py:171` derives `has_data` when `data` contains entries, and `no_data` when empty or absent.
