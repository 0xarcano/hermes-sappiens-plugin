"""Nyx builders + skill loader tests."""

from __future__ import annotations

from unittest.mock import patch

from sappiens_hermes.builders import nyx as nyx_builder
from sappiens_hermes.cosmos.account import CosmosAccountNumbers
from sappiens_hermes.cosmos.protobuf import (
    build_execute_contract_sign_doc,
    build_msgsend_sign_doc,
)
from sappiens_hermes.skill_loader import SkillRegistry, discover_skills


def test_default_fee_amount_meets_nyx_minimum():
    assert int(nyx_builder.default_fee_amount(250_000)) >= 6250
    assert int(nyx_builder.default_fee_amount(400_000)) >= 10_000
    assert nyx_builder.default_fee_amount(250_000) == "6875"
    assert nyx_builder.default_fee_amount(400_000) == "11000"


def test_discover_nyx_skill():
    skills = discover_skills()
    assert any(s.name == "nyx" for s in skills)
    reg = SkillRegistry(skills)
    nyx = reg.get("nyx")
    assert nyx.chain_id == "nyx"
    assert "send_tokens" in nyx.operations
    assert "claim_node_rewards" in nyx.operations
    assert nyx.operations["claim_node_rewards"]["contract"].startswith("n1")


def test_msgsend_sign_doc_contains_type_url_and_chain():
    doc = build_msgsend_sign_doc(
        chain_id="nyx",
        from_addr="n1fromaddressxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        to_addr="n1toaddressyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
        amount="1000",
        denom="unym",
        account_number=1,
        sequence=2,
        gas_limit=200_000,
        fee_amount="500",
        fee_denom="unym",
        compressed_pubkey=None,
    )
    assert b"nyx" in doc
    assert b"/cosmos.bank.v1beta1.MsgSend" in doc
    assert b"unym" in doc


def test_execute_contract_sign_doc_contains_type_url():
    msg = b'{"withdraw_operator_reward":{}}'
    doc = build_execute_contract_sign_doc(
        chain_id="nyx",
        sender="n1fromaddressxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        contract="n17srjznxl9dvzdkpwpw24gg668wc73val88a6m5ajg6ankwvz9wtst0cznr",
        msg_json=msg,
        account_number=1,
        sequence=2,
        gas_limit=400_000,
        fee_amount="5000",
        fee_denom="unym",
    )
    assert b"nyx" in doc
    assert b"/cosmwasm.wasm.v1.MsgExecuteContract" in doc
    assert b"withdraw_operator_reward" in doc


def test_nyx_send_tokens_builder_uses_lcd_mock():
    skill = SkillRegistry().get("nyx")
    account = CosmosAccountNumbers(account_number=7, sequence=3, pubkey_compressed=None)
    with patch(
        "sappiens_hermes.builders.nyx.query_account_numbers", return_value=account
    ):
        presentation = nyx_builder.send_tokens(
            skill,
            {
                "from_address": "n1fromaddressxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "to_address": "n1toaddressyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
                "amount": "1000000",
            },
        )
    assert presentation.technical.chain == "nyx"
    assert presentation.technical.destination.startswith("n1to")
    assert b"/cosmos.bank.v1beta1.MsgSend" in presentation.technical.sign_payload
    assert presentation.technical.payload_fields["account_number"] == "7"
    assert presentation.technical.payload_fields["sequence"] == "3"
    assert int(presentation.technical.payload_fields["fee_amount"]) >= 6250


def test_nyx_claim_builder():
    skill = SkillRegistry().get("nyx")
    account = CosmosAccountNumbers(account_number=1, sequence=0)
    with patch(
        "sappiens_hermes.builders.nyx.query_account_numbers", return_value=account
    ):
        presentation = nyx_builder.claim_node_rewards(
            skill, {"from_address": "n1fromaddressxxxxxxxxxxxxxxxxxxxxxxxxxxx"}
        )
    assert presentation.technical.destination.startswith("n17")
    assert b"/cosmwasm.wasm.v1.MsgExecuteContract" in presentation.technical.sign_payload
    assert int(presentation.technical.payload_fields["fee_amount"]) >= 10_000
    assert "claim" in presentation.human.action.lower() or "reward" in presentation.human.action.lower()
