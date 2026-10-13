"""Nyx (Nym) SignDoc builders: bank send + withdraw_operator_reward."""

from __future__ import annotations

import json
from typing import Any

from sappiens_hermes.cosmos.account import parse_pubkey_hex, query_account_numbers
from sappiens_hermes.cosmos.protobuf import (
    build_execute_contract_sign_doc,
    build_msgsend_sign_doc,
)
from sappiens_hermes.errors import BuilderError
from sappiens_hermes.presentation import (
    HumanReadableView,
    ProposalPresentation,
    TechnicalView,
)

DEFAULT_GAS_LIMIT = 250_000
CLAIM_GAS_LIMIT = 400_000

# Nyx enforces min gas price 0.025 unym (e.g. 6250 unym for 250k gas).
_NYX_MIN_GAS_PRICE_NUM = 25
_NYX_MIN_GAS_PRICE_DEN = 1000
_FEE_HEADROOM_NUM = 11
_FEE_HEADROOM_DEN = 10


def default_fee_amount(gas_limit: int) -> str:
    """Minimum fee for [gas_limit] on Nyx, with ~10% headroom above chain minimum."""
    if gas_limit <= 0:
        raise BuilderError("gas_limit must be positive")
    minimum = (
        gas_limit * _NYX_MIN_GAS_PRICE_NUM + _NYX_MIN_GAS_PRICE_DEN - 1
    ) // _NYX_MIN_GAS_PRICE_DEN
    with_headroom = (
        minimum * _FEE_HEADROOM_NUM + _FEE_HEADROOM_DEN - 1
    ) // _FEE_HEADROOM_DEN
    return str(with_headroom)


def _resolve_pubkey(account_pubkey: bytes | None, pubkey_hex: str | None) -> bytes | None:
    if account_pubkey:
        return account_pubkey
    return parse_pubkey_hex(pubkey_hex)


def _format_unym(amount: str, denom: str) -> str:
    if denom == "unym":
        try:
            n = int(amount)
            whole, frac = divmod(n, 1_000_000)
            if frac == 0:
                return f"{whole} NYM"
            return f"{whole}.{frac:06d} NYM"
        except ValueError:
            pass
    return f"{amount} {denom}"


def send_tokens(skill: Any, params: dict[str, Any]) -> ProposalPresentation:
    from_addr = str(params.get("from_address") or "").strip()
    to_addr = str(params.get("to_address") or "").strip()
    amount = str(params.get("amount") or "").strip()
    if not from_addr or not to_addr or not amount:
        raise BuilderError("from_address, to_address, and amount are required")
    if not amount.isdigit() or int(amount) <= 0:
        raise BuilderError("amount must be a positive integer string in subunits")

    denom = str(params.get("denom") or skill.denom)
    gas_limit = int(params.get("gas_limit") or DEFAULT_GAS_LIMIT)
    fee_amount = str(params.get("fee_amount") or default_fee_amount(gas_limit))
    fee_denom = str(params.get("fee_denom") or denom)
    lcd = str(params.get("lcd") or skill.lcd)
    chain_id = skill.chain_id
    pubkey_hex = params.get("pubkey_hex")

    account = query_account_numbers(lcd, from_addr)
    pubkey = _resolve_pubkey(account.pubkey_compressed, pubkey_hex)
    sign_payload = build_msgsend_sign_doc(
        chain_id=chain_id,
        from_addr=from_addr,
        to_addr=to_addr,
        amount=amount,
        denom=denom,
        account_number=account.account_number,
        sequence=account.sequence,
        gas_limit=gas_limit,
        fee_amount=fee_amount,
        fee_denom=fee_denom,
        compressed_pubkey=pubkey,
    )
    human_amount = _format_unym(amount, denom)
    summary = str(params.get("summary") or "").strip()
    action = summary or f"Send {human_amount} on Nyx (Nym)"

    return ProposalPresentation(
        human=HumanReadableView(
            action=action,
            assets="NYM" if denom == "unym" else denom,
            amounts=human_amount,
            counterparties=to_addr,
            chain=skill.display_name,
        ),
        technical=TechnicalView(
            chain=chain_id,
            destination=to_addr,
            payload_fields={
                "chain_id": chain_id,
                "to": to_addr,
                "amount": amount,
                "denom": denom,
                "account_number": str(account.account_number),
                "sequence": str(account.sequence),
                "gas_limit": str(gas_limit),
                "fee_amount": fee_amount,
                "fee_denom": fee_denom,
                "sign_mode": "SIGN_MODE_DIRECT",
                "operation": "send_tokens",
            },
            sign_payload=sign_payload,
        ),
    )


def claim_node_rewards(skill: Any, params: dict[str, Any]) -> ProposalPresentation:
    from_addr = str(params.get("from_address") or "").strip()
    if not from_addr:
        raise BuilderError("from_address is required")

    op = skill.operations.get("claim_node_rewards") or {}
    contract = str(params.get("contract") or op.get("contract") or "").strip()
    if not contract:
        raise BuilderError("mixnet contract address missing from skill")
    msg_obj = op.get("msg") or {"withdraw_operator_reward": {}}
    msg_json = json.dumps(msg_obj, separators=(",", ":"), sort_keys=True).encode("utf-8")

    denom = str(params.get("denom") or skill.denom)
    gas_limit = int(params.get("gas_limit") or CLAIM_GAS_LIMIT)
    fee_amount = str(params.get("fee_amount") or default_fee_amount(gas_limit))
    fee_denom = str(params.get("fee_denom") or denom)
    lcd = str(params.get("lcd") or skill.lcd)
    chain_id = skill.chain_id
    pubkey_hex = params.get("pubkey_hex")

    account = query_account_numbers(lcd, from_addr)
    pubkey = _resolve_pubkey(account.pubkey_compressed, pubkey_hex)
    sign_payload = build_execute_contract_sign_doc(
        chain_id=chain_id,
        sender=from_addr,
        contract=contract,
        msg_json=msg_json,
        account_number=account.account_number,
        sequence=account.sequence,
        gas_limit=gas_limit,
        fee_amount=fee_amount,
        fee_denom=fee_denom,
        compressed_pubkey=pubkey,
    )
    summary = str(params.get("summary") or "").strip()
    action = summary or "Claim pending Nym node operator rewards on Nyx"

    return ProposalPresentation(
        human=HumanReadableView(
            action=action,
            assets="NYM operator rewards",
            amounts="pending (on-chain after approve)",
            counterparties=from_addr,
            chain=skill.display_name,
        ),
        technical=TechnicalView(
            chain=chain_id,
            destination=contract,
            payload_fields={
                "chain_id": chain_id,
                "contract": contract,
                "execute_msg": json.dumps(msg_obj, separators=(",", ":")),
                "sender": from_addr,
                "account_number": str(account.account_number),
                "sequence": str(account.sequence),
                "gas_limit": str(gas_limit),
                "fee_amount": fee_amount,
                "fee_denom": fee_denom,
                "sign_mode": "SIGN_MODE_DIRECT",
                "operation": "claim_node_rewards",
            },
            sign_payload=sign_payload,
        ),
    )
