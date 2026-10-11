"""Tool JSON schemas for Hermes."""

from __future__ import annotations

SAPPENS_PAIR = {
    "name": "sappiens_pair",
    "description": (
        "Create a Sappiens Wallet registration offer and return the "
        "sappiens://v1/register?offer=… URI for QR scanning. "
        "Set wait=true to poll until the wallet confirms and derive the channel key."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "display_name": {
                "type": "string",
                "description": "Agent display name shown in the wallet (1-64 chars).",
            },
            "wait": {
                "type": "boolean",
                "description": "Poll until the wallet confirms (default false).",
            },
        },
    },
}

SAPPENS_STATUS = {
    "name": "sappiens_status",
    "description": "Show Sappiens pairing status, relay URL, and loaded chain SKILLs.",
    "parameters": {"type": "object", "properties": {}},
}

SAPPENS_SKILLS = {
    "name": "sappiens_skills",
    "description": (
        "List chain SKILLs discovered from skills/*/skill.yaml "
        "(operations, chain_id, LCD/RPC). Load a skill for the agent with "
        "skill_view('sappiens-wallet:<name>')."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Optional skill name for a detailed dump.",
            },
        },
    },
}

SAPPENS_SEND = {
    "name": "sappiens_send",
    "description": (
        "Build a completable Nyx (or skill-selected) MsgSend SignDoc proposal, "
        "seal it, and submit to the Sappiens relay for human review/sign. "
        "Requires an active pairing. Hermes will ask for approval before sending."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "skill": {
                "type": "string",
                "description": "Skill name (default: nyx).",
            },
            "from_address": {
                "type": "string",
                "description": "Sender bech32 (n… for Nyx).",
            },
            "to_address": {
                "type": "string",
                "description": "Destination bech32.",
            },
            "amount": {
                "type": "string",
                "description": "Amount in subunits (unym), integer string.",
            },
            "denom": {"type": "string", "description": "Denom override (default unym)."},
            "pubkey_hex": {
                "type": "string",
                "description": (
                    "Optional 33-byte compressed secp256k1 pubkey hex "
                    "(or secp256k1:<hex>) when LCD has none."
                ),
            },
            "fee_amount": {"type": "string"},
            "gas_limit": {"type": "integer"},
            "lcd": {"type": "string"},
            "summary": {"type": "string"},
        },
        "required": ["from_address", "to_address", "amount"],
    },
}

SAPPENS_CLAIM_REWARDS = {
    "name": "sappiens_claim_rewards",
    "description": (
        "Build a Nyx mixnet withdraw_operator_reward (claim Nym node rewards) "
        "SignDoc proposal, seal it, and submit to the Sappiens relay. "
        "Requires pairing. Hermes will ask for approval before sending."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "skill": {
                "type": "string",
                "description": "Skill name (default: nyx).",
            },
            "from_address": {
                "type": "string",
                "description": "Operator bech32 that owns the node (n…).",
            },
            "pubkey_hex": {"type": "string"},
            "fee_amount": {"type": "string"},
            "gas_limit": {"type": "integer"},
            "lcd": {"type": "string"},
            "contract": {
                "type": "string",
                "description": "Override mixnet contract (defaults from skill).",
            },
            "summary": {"type": "string"},
        },
        "required": ["from_address"],
    },
}

SAPPENS_PROPOSE_RAW = {
    "name": "sappiens_propose_raw",
    "description": (
        "Expert path: submit a caller-built dual presentation with base64url "
        "sign_payload bytes. Prefer sappiens_send / sappiens_claim_rewards."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "human_action": {"type": "string"},
            "human_assets": {"type": "string"},
            "human_amounts": {"type": "string"},
            "human_counterparties": {"type": "string"},
            "human_chain": {"type": "string"},
            "technical_chain": {"type": "string"},
            "destination": {"type": "string"},
            "payload_fields": {
                "type": "object",
                "description": "Map of text keys to text values.",
            },
            "sign_payload_b64": {
                "type": "string",
                "description": "base64url-no-pad SignDoc bytes.",
            },
        },
        "required": [
            "summary",
            "human_action",
            "human_assets",
            "human_amounts",
            "human_counterparties",
            "human_chain",
            "technical_chain",
            "destination",
            "sign_payload_b64",
        ],
    },
}
