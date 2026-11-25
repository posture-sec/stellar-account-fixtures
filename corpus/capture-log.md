# Chronological Capture Log

This log orders the nine captured fixtures by the UTC `captured_at` value in each
`fixture.toml`. Timestamps are listed as recorded, and fixture ID is the tie-breaker
if two captures share a second. The Horizon build version is the exact version string
from each sidecar.

| Fixture ID | Network | Captured at (UTC) | Capture ledger | Horizon build version |
|---|---|---|---:|---|
| `default-plain` | `public` | `2026-11-02T11:48:46Z` | 65266813 | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` |
| `multisig-custody` | `public` | `2026-11-02T11:48:49Z` | 65266865 | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` |
| `issuer-auth-required` | `public` | `2026-11-02T11:48:52Z` | 65266862 | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` |
| `asset-heavy-exchange` | `public` | `2026-11-02T11:48:55Z` | 65266866 | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` |
| `whitespace-home-domain` | `public` | `2026-11-02T11:48:58Z` | 65266813 | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` |
| `domain-and-inflation` | `public` | `2026-11-02T11:49:02Z` | 65266813 | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` |
| `coordinator-data-entry` | `public` | `2026-11-03T09:48:29Z` | 65282653 | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` |
| `testnet-multisig` | `testnet` | `2026-11-03T09:48:40Z` | 5535101 | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` |
| `sponsored-trustlines` | `public` | `2026-11-03T09:50:41Z` | 65110665 | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` |

## Ledger lag

The `sponsored-trustlines` capture is a pronounced public-network ledger outlier.
Its ledger, 65110665, is 156148 ledgers below the earliest ledger among the other
public captures, 65266813, despite its later capture timestamp. Testnet ledger
heights are on a separate network and are not compared with public-network heights.

The `captured_at` and `horizon_version` fields are required provenance fields. The
schema lists `horizon_version` at `SCHEMA.md:61`; the task's validator reference is
`validate.py:279`. In this checkout, the captured timestamp check is at
`validate.py:342` and the non-empty Horizon version check is at `validate.py:363`.
