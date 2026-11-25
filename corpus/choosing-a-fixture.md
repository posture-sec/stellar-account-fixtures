# Choosing a Fixture

Use this question-driven index to find an existing account specimen for a consumer
test. Shape labels are copied from each fixture's `fixture.toml`; their definitions
are in [SCHEMA.md, section 5](../SCHEMA.md#5-the-shape-vocabulary). This guide selects
specimens only. It does not recommend audit rules or policy.

## Which fixture has whitespace in its home domain?

Use [`whitespace-home-domain`](../fixtures/whitespace-home-domain/fixture.toml) to test
handling of a `home_domain` containing one space. Its declared shape labels are
`blank_home_domain`, `has_inflation`, `master_is_signer`, `no_data`, `not_sponsored`,
`single_signer`, `sponsoring`, and `thresholds_zero`.

## Which fixture represents a revoked master key?

No current fixture has the `master_absent` shape. A future specimen for this scenario
should have `master_absent`; it should also have `no_signers` only if its signers list
is empty. The schema notes that omission of the master key from `signers` is what a
revoked master key looks like in an account resource.

A zero-weight master key is a different specimen, not a revoked-key example:
[`coordinator-data-entry`](../fixtures/coordinator-data-entry/fixture.toml) declares
`has_data`, `master_is_signer`, `multi_signer`, `no_home_domain`, `no_inflation`,
`not_sponsored`, `sponsoring`, and `thresholds_nonzero`.

## Which fixture has a high balance count?

Use [`asset-heavy-exchange`](../fixtures/asset-heavy-exchange/fixture.toml) for an
account with 37 trustlines and the `many_balances` shape. Its other declared labels are
`has_home_domain`, `master_is_signer`, `no_data`, `no_inflation`, `not_sponsored`,
`single_signer`, `sponsoring`, and `thresholds_zero`.

## Which fixture has an account data entry?

Use [`coordinator-data-entry`](../fixtures/coordinator-data-entry/fixture.toml) for an
account with a non-empty `data` object. Its declared labels are `has_data`,
`master_is_signer`, `multi_signer`, `no_home_domain`, `no_inflation`, `not_sponsored`,
`sponsoring`, and `thresholds_nonzero`.

## Which fixture should I use for multi-signature thresholds?

- For nine signers with thresholds `2/2/2`, use
  [`coordinator-data-entry`](../fixtures/coordinator-data-entry/fixture.toml). Its
  declared labels are `has_data`, `master_is_signer`, `multi_signer`, `no_home_domain`,
  `no_inflation`, `not_sponsored`, `sponsoring`, and `thresholds_nonzero`.
- For two signers with distinct thresholds `2/3/4`, use
  [`multisig-custody`](../fixtures/multisig-custody/fixture.toml). Its declared labels are
  `has_inflation`, `master_is_signer`, `multi_signer`, `no_data`, `no_home_domain`,
  `not_sponsored`, `not_sponsoring`, and `thresholds_nonzero`.
- For six signers with thresholds `3/3/3` on testnet, use
  [`testnet-multisig`](../fixtures/testnet-multisig/fixture.toml). Its declared labels
  are `master_is_signer`, `multi_signer`, `no_data`, `no_home_domain`, `no_inflation`,
  `not_sponsored`, `not_sponsoring`, and `thresholds_nonzero`.

For all fixture threshold triples, see the
[Threshold Combinations Matrix](thresholds.md).
