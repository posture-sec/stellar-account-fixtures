# Network Conformance Audit

This document provides a static compliance audit proving that each captured fixture
in the corpus conforms to its declared Stellar network and matching network root
document, guaranteeing absolute network segregation across the fixture corpus.

## 1. Conformance Contract and Network Segregation

Per `SCHEMA.md:133` (Section 6, Root documents), every network referenced by a
fixture must provide a corresponding `corpus/root-<network>.json` root document.
The network passphrase serves as the cryptographic ground truth for all transaction
signing and network identity. Transactions and account states are bound to a specific
network via the SHA-256 hash of its passphrase:

| Network | Canonical Root Document | Network Passphrase |
|---|---|---|
| `public` | `corpus/root-public.json` | `Public Global Stellar Network ; September 2015` |
| `testnet` | `corpus/root-testnet.json` | `Test SDF Network ; September 2015` |

The passphrases above match the root documents character-for-character, verified at
`corpus/root-public.json:103` and `corpus/root-testnet.json:107`.

## 2. Validator Enforcement Mechanism

Network isolation is enforced programmatically in `validate.py:370` through the
`check_root` function:

1. **Root File Presence**: For every network declared across sidecars, `validate.py`
   confirms the existence of `corpus/root-<network>.json`.
2. **Cryptographic Identity Verification**: `check_root` parses the root document as
   UTF-8 JSON and asserts that the `network_passphrase` top-level field matches the
   expected canonical passphrase from `validate.NETWORKS[network][1]`.
3. **Endpoint and Source Alignment**: In `check_captured` (`validate.py:327`), the
   validator confirms that the fixture `source_url` starts with the exact canonical
   Horizon base URL associated with that network (`https://horizon.stellar.org` for
   `public`, and `https://horizon-testnet.stellar.org` for `testnet`).
4. **Network Consistency**: An account captured from testnet cannot validate if its
   sidecar declares public, because the source URL domain and network passphrase
   would immediately fail validation.

## 3. Fixture Network Conformance Audit Table

The table below audits all captured fixtures in the corpus against their declared
network, Horizon source URL, verified root document, and verified network passphrase.

| Fixture ID | Network | Source URL | Verified Root File | Network Passphrase |
|---|---|---|---|---|
| `asset-heavy-exchange` | `public` | `https://horizon.stellar.org/accounts/GDAYKKYOJ545SUQZ4V26IOHRN6K4VGLAZXK2EOGJCYG4SGRZSA5EOY2S` | `corpus/root-public.json` | `Public Global Stellar Network ; September 2015` |
| `coordinator-data-entry` | `public` | `https://horizon.stellar.org/accounts/GAUA7XL5K54CC2DDGP77FJ2YBHRJLT36CPZDXWPM6MP7MANOGG77PNJU` | `corpus/root-public.json` | `Public Global Stellar Network ; September 2015` |
| `default-plain` | `public` | `https://horizon.stellar.org/accounts/GA7DTK7GPOEQGXHI7MLA2OAIEL4365VG6PXUAVREMDVLC4MJIJ62KR75` | `corpus/root-public.json` | `Public Global Stellar Network ; September 2015` |
| `domain-and-inflation` | `public` | `https://horizon.stellar.org/accounts/GB4UOCL7R5UZQ3C7HM4VNFHB6GGTFDQZ2WEQUTXTDXLXY3UUXKXYV2X6` | `corpus/root-public.json` | `Public Global Stellar Network ; September 2015` |
| `issuer-auth-required` | `public` | `https://horizon.stellar.org/accounts/GD3ZN2T6QQMKLAGKKMWHHY4FITANVJBTREEJERHTWGWF2GSBPOSHGCLU` | `corpus/root-public.json` | `Public Global Stellar Network ; September 2015` |
| `multisig-custody` | `public` | `https://horizon.stellar.org/accounts/GA2TBSAIX6W3C6IND7KC3PIRW6ON5OR7LHMRWD4AJKXEIYMF7B6MAAGR` | `corpus/root-public.json` | `Public Global Stellar Network ; September 2015` |
| `sponsored-trustlines` | `public` | `https://horizon.stellar.org/accounts/GCPEC2WSEJPAFPLPPDPBU3XI6SXHJUZD2KLUA6BBBPO7WES3W5ZKDE54` | `corpus/root-public.json` | `Public Global Stellar Network ; September 2015` |
| `ten-balances-boundary` | `public` | `https://horizon.stellar.org/accounts/GA6H7KUNUTSKIE2RYMGLOOEKJMKIS7UTR2T6LIKSIUMNMJXOKXYGX5SQ` | `corpus/root-public.json` | `Public Global Stellar Network ; September 2015` |
| `testnet-multisig` | `testnet` | `https://horizon-testnet.stellar.org/accounts/GCI76XDVHDGJMZGP5EWQYCZCYIBNBVABLPHWCKEZWJF2K4Z5SD74A4AV` | `corpus/root-testnet.json` | `Test SDF Network ; September 2015` |
| `testnet-sponsored` | `testnet` | `https://horizon-testnet.stellar.org/accounts/GBORJ5OEACW7Z22O46ZFNZRZC5IL36HYV7GF7DHGLJ3BE3MVWYV57YAQ` | `corpus/root-testnet.json` | `Test SDF Network ; September 2015` |
| `whitespace-home-domain` | `public` | `https://horizon.stellar.org/accounts/GBDAZM3LPTHP3IFPDAUQGLSANPW5S5K5WFKBFVHQ3SMT3JDRQICMTSNZ` | `corpus/root-public.json` | `Public Global Stellar Network ; September 2015` |

## 4. Synthetic Fixture Network Isolation

Synthetic fixtures such as `null-home-domain` define `network = "public"` to indicate
the simulated target protocol rules without fetching from a live endpoint. Per
`SCHEMA.md:51`, synthetic sidecars strictly forbid `source_url`, `captured_at`,
`ledger`, `horizon_version`, and `sha256`. Network isolation for synthetic fixtures
is enforced by prohibiting live provenance and requiring the `synthetic:` scenario
prefix in `validate.py:311`.
