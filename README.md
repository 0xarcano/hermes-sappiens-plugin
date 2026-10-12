# hermes-sappiens-plugin

Hermes Agent plugin that pairs with [Sappiens Wallet](https://github.com/0xarcano/sappiens) over the published relay protocol, loads chain **SKILLs** to build completable SignDoc proposals, and ships a first **Nyx (Nym)** skill for:

- sending NYM (`MsgSend`)
- claiming Nym node operator rewards (`withdraw_operator_reward` on the mixnet contract)

Keys never enter Hermes. The wallet holds custody; this plugin only seals ciphertext envelopes.

## Requirements

| Dependency | Purpose |
| --- | --- |
| Hermes Agent | Host (`plugin.yaml` + `register(ctx)`) |
| Sappiens relay | Registration + envelopes (`SAPPIENS_RELAY_URL`) |
| Sappiens Wallet | Scan QR, approve, sign, broadcast |
| Builtin Cosmos plugin in wallet | Provides `chain_id: nyx` |

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# Directory plugin for Hermes:
ln -s "$(pwd)" ~/.hermes/plugins/sappiens-wallet
# hermes plugins enable sappiens-wallet
```

Local check without Hermes CLI:

```bash
./scripts/doctor-local.sh
pytest -q
```

## Secrets / env

| Variable | Required | Meaning |
| --- | --- | --- |
| `SAPPIENS_AGENT_ED25519_SEED` | yes | base64url-no-pad 32-byte Ed25519 seed |
| `SAPPIENS_RELAY_URL` | no | default `http://127.0.0.1:8080` |
| `SAPPIENS_ADVERTISE_RELAY` | no | URL sealed into the QR (wallet-reachable) |
| `SAPPIENS_DISPLAY_NAME` | no | default `Hermes Sappiens Agent` |
| `SAPPIENS_STATE_PATH` | no | override pairing state JSON path |

Relay URLs can also be set in Hermes **Settings → Plugins → sappiens-wallet** (`relay_url`, `advertise_relay`). Plugin settings override the matching env vars.

Generate a seed:

```bash
python -c 'import os; from sappiens_hermes import b64; print(b64.encode(os.urandom(32)))'
```

## Tools

| Tool | Role |
| --- | --- |
| `sappiens_pair` | Mint offer + URI; optional `wait=true` handshake |
| `sappiens_status` | Paired?, relay, skills |
| `sappiens_skills` | List / inspect SKILL metadata from disk |
| `sappiens_send` | Skill-built MsgSend → seal → relay (Hermes approval) |
| `sappiens_claim_rewards` | Skill-built claim → seal → relay (Hermes approval) |
| `sappiens_propose_raw` | Expert raw presentation + SignDoc |

Slash: `/sappiens-pair`, `/sappiens-status`.

Write tools escalate via `pre_tool_call` `{action: approve}`.

## SKILLs

Skills live under `skills/<name>/`:

- `SKILL.md` — agent playbook (`skill_view("sappiens-wallet:nyx")`)
- `skill.yaml` — machine contract (chain_id, LCD/RPC, operations, builder)

First skill: **nyx** (Nyx / Nym). Adding a chain = new skill directory + `sappiens_hermes/builders/<name>.py`.

## Happy path

1. Start Sappiens relay (`deploy/podman` in the wallet repo).
2. Set `SAPPIENS_AGENT_ED25519_SEED` and enable the plugin.
3. In Hermes: “Pair with Sappiens” → show URI as QR → confirm on phone.
4. “Send 1 NYM from n1… to n1…” → approve Hermes prompt → approve in wallet.
5. “Claim my Nym node rewards for n1…” → same dual gates.

## License

MIT
