---
name: nyx
description: Build Nyx (Nym) Sappiens proposals — send NYM and claim node rewards.
version: 0.1.0
metadata:
  hermes:
    tags: [nym, nyx, cosmos, wallet, sappiens]
---

# Nyx (Nym) — Sappiens chain skill

Use this skill when the user wants to send NYM on **Nyx** or **claim Nym node operator rewards** through the paired Sappiens Wallet.

Load siblings with `skill_view("sappiens-wallet:nyx")`. Machine config is in `skill.yaml` (chain_id, LCD/RPC, mixnet contract).

## Prerequisites

1. Sappiens Wallet with the builtin Cosmos plugin (includes `chain_id: nyx`).
2. Active pairing: `sappiens_pair` → scan QR → confirm on phone → `wait=true`.
3. Operator / sender address as bech32 `n…`, and if LCD has no pubkey yet, pass `pubkey_hex` (`secp256k1:<33-byte-compressed-hex>` from the wallet Accounts screen).

## Operations

### Send tokens

Tool: `sappiens_send`

```text
from_address: n1…
to_address: n1…
amount: <unym integer string>   # 1 NYM = 1000000 unym
skill: nyx                      # default
```

Optional: `fee_amount`, `gas_limit`, `lcd`, `pubkey_hex`, `summary`. If omitted,
`fee_amount` is computed from Nyx min gas price (0.025 unym/gas) plus headroom for
the chosen `gas_limit`.

Details: `references/send-tokens.md`

### Claim Nym node rewards

Tool: `sappiens_claim_rewards`

Executes CosmWasm `withdraw_operator_reward` on the Nyx mixnet contract
`n17srjznxl9dvzdkpwpw24gg668wc73val88a6m5ajg6ankwvz9wtst0cznr`.

```text
from_address: n1…   # node operator wallet
skill: nyx
```

Details: `references/claim-node-rewards.md`

## Agent workflow

1. `sappiens_status` — confirm paired.
2. `skill_view("sappiens-wallet:nyx")` — refresh chain rules if needed.
3. Call `sappiens_send` or `sappiens_claim_rewards`.
4. Hermes approval gate fires; after approve, the sealed proposal is queued.
5. Tell the user to open Sappiens, review human/technical presentation, Approve + sign.
6. Do **not** claim on-chain success until the person reports the wallet submission result.

## Safety

- Never ask for or accept seed phrases / private keys.
- Never install or remove Sappiens chain plugins.
- `sign_payload` is exact SignDoc bytes; do not invent human copy that contradicts amounts/addresses.
