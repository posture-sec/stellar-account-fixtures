# Corpus Provenance and Integrity Directory

> Consolidated provenance records across all nine fixtures, detailing network origin, ledger height, capture timestamps, and SHA-256 integrity digests.

## 1. Purpose of Aggregate Provenance

Each captured fixture in this corpus records local provenance metadata in its `fixture.toml` sidecar. This document aggregates all provenance records into a single consolidated reference table, enabling consumer developers and security auditors to verify ledger chronology, Horizon software versions, and cryptographic integrity across the entire corpus without parsing individual subdirectories.

Per `SCHEMA.md:62`, every captured fixture requires exact provenance metadata. Synthetic fixtures (if introduced) are strictly prohibited from carrying provenance keys because they are not captured from a live network.

## 2. Consolidated Provenance Table

| Fixture ID | Account ID | Network | Ledger Height | Capture Timestamp | Horizon Version | SHA-256 Digest |
|---|---|---|---|---|---|---|
| `asset-heavy-exchange` | `GDAYKKYOJ545SUQZ4V26IOHRN6K4VGLAZXK2EOGJCYG4SGRZSA5EOY2S` | `public` | 65266866 | `2026-11-02T11:48:55Z` | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` | `dc7ccffebd29f079e61482a764013a418fc496e150c6129ec10d82d11fa3f9bc` |
| `coordinator-data-entry` | `GAUA7XL5K54CC2DDGP77FJ2YBHRJLT36CPZDXWPM6MP7MANOGG77PNJU` | `public` | 65282653 | `2026-11-03T09:48:29Z` | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` | `6c794f8716fb0754605344923e37d6ef417fbb680db274f7e27ba0a12a917659` |
| `default-plain` | `GA7DTK7GPOEQGXHI7MLA2OAIEL4365VG6PXUAVREMDVLC4MJIJ62KR75` | `public` | 65266813 | `2026-11-02T11:48:46Z` | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` | `d14f1f7bbcf10f9e1d7e162b59db1481ecd1ea542a7f21766a53fafdebdb4cdb` |
| `domain-and-inflation` | `GB4UOCL7R5UZQ3C7HM4VNFHB6GGTFDQZ2WEQUTXTDXLXY3UUXKXYV2X6` | `public` | 65266813 | `2026-11-02T11:49:02Z` | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` | `b33a885e520b9cfcd5cc515a3b678e5413d7880b7185cbcdcbe8de863757de76` |
| `issuer-auth-required` | `GD3ZN2T6QQMKLAGKKMWHHY4FITANVJBTREEJERHTWGWF2GSBPOSHGCLU` | `public` | 65266862 | `2026-11-02T11:48:52Z` | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` | `701981c0c40d4d6a109274df6a6bb735f876b2c7204ffa86eb79071a2654f7de` |
| `multisig-custody` | `GA2TBSAIX6W3C6IND7KC3PIRW6ON5OR7LHMRWD4AJKXEIYMF7B6MAAGR` | `public` | 65266865 | `2026-11-02T11:48:49Z` | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` | `c960f2f7f2b9573493d0f4a78bcc02fe11e0c5c829b7dea3b30938b196470711` |
| `sponsored-trustlines` | `GCPEC2WSEJPAFPLPPDPBU3XI6SXHJUZD2KLUA6BBBPO7WES3W5ZKDE54` | `public` | 65110665 | `2026-11-03T09:50:41Z` | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` | `20ebd6c8e9552a7cfeae0d348d859c76996f3cf798ca39c0c2b8e0a8151bc97a` |
| `testnet-multisig` | `GCI76XDVHDGJMZGP5EWQYCZCYIBNBVABLPHWCKEZWJF2K4Z5SD74A4AV` | `testnet` | 5535101 | `2026-11-03T09:48:40Z` | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` | `547fe3f3d484fdec1d6ecc699605597ba7b43e49613648c0b1bca6f2dac6776d` |
| `whitespace-home-domain` | `GBDAZM3LPTHP3IFPDAUQGLSANPW5S5K5WFKBFVHQ3SMT3JDRQICMTSNZ` | `public` | 65266813 | `2026-11-02T11:48:58Z` | `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666` | `768c86e8393955ec943eb951e4ec25bf9cba83a3c8bb8a5b25ca04fca2093b0e` |

## 3. SHA-256 Computation and Verification Contract

In accordance with `SCHEMA.md:62` and `validate.py:317` (formerly referenced in `validate.py:273`), the `sha256` value is computed directly over the exact raw bytes of `account.json` as it resides on disk:

```python
digest = hashlib.sha256(body.read_bytes()).hexdigest()
if data["sha256"] != digest:
    corpus.error(where, f"sha256 does not match account.json (bytes say {digest[:12]}...)")
```

The SHA-256 digest is an immutable content-hash covering the full JSON payload, including character encoding, key ordering, and whitespace. Because `tools/capture.py` formats JSON with sorted keys and standard separators, the digest guarantees bit-for-bit reproducibility.

### Independent Verification

Consumers can verify all fixture digests independently without Python tooling using standard shell utilities:

```bash
sha256sum fixtures/*/account.json
```

Each resulting digest matches the `sha256` field in the corresponding `fixture.toml` sidecar exactly.

## 4. Horizon Version and Ledger Chronology

All nine captures were collected from official Stellar Horizon endpoints running `30.0.0-b3ff4119cc99ebcc8048334f5ec64e78c16d1666`:
- Mainnet captures span ledgers 65110665 through 65282653, captured between 2026-11-02 and 2026-11-03.
- The Testnet capture (`testnet-multisig`) was recorded at ledger 5535101 on 2026-11-03.
