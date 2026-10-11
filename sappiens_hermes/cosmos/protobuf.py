"""Minimal protobuf wire helpers matching sappiens wallet cosmos_tx.dart."""

from __future__ import annotations


def encode_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varint must be non-negative")
    out = bytearray()
    v = value
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def encode_key(field: int, wire: int) -> bytes:
    return encode_varint((field << 3) | wire)


def encode_bytes_field(field: int, data: bytes) -> bytes:
    return encode_key(field, 2) + encode_varint(len(data)) + data


def encode_string_field(field: int, value: str) -> bytes:
    return encode_bytes_field(field, value.encode("utf-8"))


def encode_uint64_field(field: int, value: int) -> bytes:
    return encode_key(field, 0) + encode_varint(value)


def encode_coin(denom: str, amount: str) -> bytes:
    return encode_string_field(1, denom) + encode_string_field(2, amount)


def encode_any(type_url: str, value: bytes) -> bytes:
    return encode_string_field(1, type_url) + encode_bytes_field(2, value)


def encode_msg_send(from_addr: str, to_addr: str, amount: str, denom: str) -> bytes:
    coin = encode_coin(denom, amount)
    return (
        encode_string_field(1, from_addr)
        + encode_string_field(2, to_addr)
        + encode_bytes_field(3, coin)
    )


def encode_msg_execute_contract(
    sender: str,
    contract: str,
    msg_json: bytes,
    funds: list[tuple[str, str]] | None = None,
) -> bytes:
    """cosmwasm.wasm.v1.MsgExecuteContract"""
    out = (
        encode_string_field(1, sender)
        + encode_string_field(2, contract)
        + encode_bytes_field(3, msg_json)
    )
    for denom, amount in funds or []:
        out += encode_bytes_field(5, encode_coin(denom, amount))
    return out


def encode_tx_body(any_messages: list[bytes]) -> bytes:
    out = b""
    for any_msg in any_messages:
        out += encode_bytes_field(1, any_msg)
    return out


def encode_auth_info(
    sequence: int,
    gas_limit: int,
    fee_amount: str,
    fee_denom: str,
    compressed_pubkey: bytes | None = None,
) -> bytes:
    single = encode_uint64_field(1, 1)  # SIGN_MODE_DIRECT
    mode_info = encode_bytes_field(1, single)
    signer_info = b""
    if compressed_pubkey and len(compressed_pubkey) == 33:
        key_msg = encode_bytes_field(1, compressed_pubkey)
        pk_any = encode_any("/cosmos.crypto.secp256k1.PubKey", key_msg)
        signer_info += encode_bytes_field(1, pk_any)
    signer_info += encode_bytes_field(2, mode_info)
    signer_info += encode_uint64_field(3, sequence)

    fee_coin = encode_coin(fee_denom, fee_amount)
    fee = encode_bytes_field(1, fee_coin) + encode_uint64_field(2, gas_limit)
    return encode_bytes_field(1, signer_info) + encode_bytes_field(2, fee)


def encode_sign_doc(
    body_bytes: bytes,
    auth_info_bytes: bytes,
    chain_id: str,
    account_number: int,
) -> bytes:
    return (
        encode_bytes_field(1, body_bytes)
        + encode_bytes_field(2, auth_info_bytes)
        + encode_string_field(3, chain_id)
        + encode_uint64_field(4, account_number)
    )


def build_msgsend_sign_doc(
    *,
    chain_id: str,
    from_addr: str,
    to_addr: str,
    amount: str,
    denom: str,
    account_number: int,
    sequence: int,
    gas_limit: int,
    fee_amount: str,
    fee_denom: str,
    compressed_pubkey: bytes | None = None,
) -> bytes:
    msg = encode_msg_send(from_addr, to_addr, amount, denom)
    any_msg = encode_any("/cosmos.bank.v1beta1.MsgSend", msg)
    body = encode_tx_body([any_msg])
    auth = encode_auth_info(
        sequence, gas_limit, fee_amount, fee_denom, compressed_pubkey
    )
    return encode_sign_doc(body, auth, chain_id, account_number)


def build_execute_contract_sign_doc(
    *,
    chain_id: str,
    sender: str,
    contract: str,
    msg_json: bytes,
    account_number: int,
    sequence: int,
    gas_limit: int,
    fee_amount: str,
    fee_denom: str,
    compressed_pubkey: bytes | None = None,
    funds: list[tuple[str, str]] | None = None,
) -> bytes:
    msg = encode_msg_execute_contract(sender, contract, msg_json, funds)
    any_msg = encode_any("/cosmwasm.wasm.v1.MsgExecuteContract", msg)
    body = encode_tx_body([any_msg])
    auth = encode_auth_info(
        sequence, gas_limit, fee_amount, fee_denom, compressed_pubkey
    )
    return encode_sign_doc(body, auth, chain_id, account_number)
