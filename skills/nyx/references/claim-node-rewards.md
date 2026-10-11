# Claim Nym node operator rewards

## Contract

- Mixnet contract: `n17srjznxl9dvzdkpwpw24gg668wc73val88a6m5ajg6ankwvz9wtst0cznr`
- Message type: `/cosmwasm.wasm.v1.MsgExecuteContract`
- Execute JSON: `{"withdraw_operator_reward":{}}`

This zeroes accrued operator rewards and transfers them to the operator address (Nym mixnet v2 `WithdrawOperatorReward`).

## Builder steps (plugin)

1. LCD account query for the operator `from_address`.
2. Encode MsgExecuteContract with empty funds.
3. Dual presentation: human action describes claiming node rewards; `technical.destination` = mixnet contract.
4. Seal and submit envelope.

## Defaults

| Field | Default |
|-------|---------|
| fee_amount | `5000` unym |
| gas_limit | `400000` |

## Out of scope (this skill version)

- `withdraw_delegator_reward` (needs `mix_id`)
- Bonding / unbonding / family invites
- Vesting-contract proxy claims
