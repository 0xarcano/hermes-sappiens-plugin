# Nyx send tokens

## Wire shape

- `chain_id`: `nyx`
- Message: `/cosmos.bank.v1beta1.MsgSend`
- Denom: `unym` (1 NYM = 1_000_000 unym)
- Sign mode: `SIGN_MODE_DIRECT`
- `technical.sign_payload`: protobuf `cosmos.tx.v1beta1.SignDoc`

## Builder steps (plugin)

1. Query LCD `{lcd}/cosmos/auth/v1beta1/accounts/{from}` for `account_number` and `sequence`.
2. Encode MsgSend + AuthInfo (fee in unym) + SignDoc.
3. Fill dual presentation; `technical.destination` = `to_address`.
4. Seal ProposalDocument and `POST /v1/envelopes`.

## Defaults

| Field | Default |
|-------|---------|
| LCD | `https://api.nyx.nodes.guru` |
| RPC (wallet broadcast) | `https://rpc.nyx.nodes.guru` |
| fee_amount | `6875` unym (derived: min 0.025 unym/gas × gas + ~10% headroom) |
| gas_limit | `250000` |

## Tool example

```json
{
  "from_address": "n1…",
  "to_address": "n1…",
  "amount": "1000000",
  "pubkey_hex": "secp256k1:02…"
}
```
