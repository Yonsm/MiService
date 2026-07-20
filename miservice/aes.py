"""Builtin AES-128-CBC — pure Python, drop-in fallback for pycryptodome.

Used by miiolocal.py when the `Crypto` package (pycryptodome) is not
installed, same fallback pattern as biohttp.py is for aiohttp.

Usage::

    encrypted = aes_cbc_encrypt(key, iv, data)  # len(data) must be a multiple of 16
    data = aes_cbc_decrypt(key, iv, encrypted)
"""

from typing import List


def _gf_mul(a: int, b: int) -> int:
    """Multiply two bytes in GF(2^8) (AES's finite field)."""
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi:
            a ^= 0x1B
        b >>= 1
    return p


def _build_sbox() -> List[int]:
    inv = [0] * 256
    for a in range(1, 256):
        for b in range(1, 256):
            if _gf_mul(a, b) == 1:
                inv[a] = b
                break
    sbox = [0] * 256
    for i in range(256):
        b = inv[i]
        val = b
        r = b
        for _ in range(4):
            r = ((r << 1) | (r >> 7)) & 0xFF
            val ^= r
        sbox[i] = val ^ 0x63
    return sbox


_SBOX = _build_sbox()
_INV_SBOX = [0] * 256
for _i, _v in enumerate(_SBOX):
    _INV_SBOX[_v] = _i

_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def _key_expansion(key: bytes) -> List[List[int]]:
    """AES-128 key schedule -> 11 round keys, each a flat list of 16 bytes."""
    nk, nr, nb = 4, 10, 4
    w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, nb * (nr + 1)):
        temp = list(w[i - 1])
        if i % nk == 0:
            temp = temp[1:] + temp[:1]
            temp = [_SBOX[b] for b in temp]
            temp[0] ^= _RCON[i // nk - 1]
        w.append([w[i - nk][j] ^ temp[j] for j in range(4)])
    round_keys = []
    for r in range(nr + 1):
        rk = []
        for col in range(4):
            rk.extend(w[4 * r + col])
        round_keys.append(rk)
    return round_keys


def _add_round_key(s: List[int], rk: List[int]) -> List[int]:
    return [s[i] ^ rk[i] for i in range(16)]


def _sub_bytes(s: List[int]) -> List[int]:
    return [_SBOX[b] for b in s]


def _inv_sub_bytes(s: List[int]) -> List[int]:
    return [_INV_SBOX[b] for b in s]


def _shift_rows(s: List[int]) -> List[int]:
    return [s[((c + r) % 4) * 4 + r] for c in range(4) for r in range(4)]


def _inv_shift_rows(s: List[int]) -> List[int]:
    return [s[((c - r) % 4) * 4 + r] for c in range(4) for r in range(4)]


def _mix_columns(s: List[int]) -> List[int]:
    out = [0] * 16
    for c in range(4):
        a0, a1, a2, a3 = s[c * 4:c * 4 + 4]
        out[c * 4 + 0] = _gf_mul(2, a0) ^ _gf_mul(3, a1) ^ a2 ^ a3
        out[c * 4 + 1] = a0 ^ _gf_mul(2, a1) ^ _gf_mul(3, a2) ^ a3
        out[c * 4 + 2] = a0 ^ a1 ^ _gf_mul(2, a2) ^ _gf_mul(3, a3)
        out[c * 4 + 3] = _gf_mul(3, a0) ^ a1 ^ a2 ^ _gf_mul(2, a3)
    return out


def _inv_mix_columns(s: List[int]) -> List[int]:
    out = [0] * 16
    for c in range(4):
        a0, a1, a2, a3 = s[c * 4:c * 4 + 4]
        out[c * 4 + 0] = _gf_mul(14, a0) ^ _gf_mul(11, a1) ^ _gf_mul(13, a2) ^ _gf_mul(9, a3)
        out[c * 4 + 1] = _gf_mul(9, a0) ^ _gf_mul(14, a1) ^ _gf_mul(11, a2) ^ _gf_mul(13, a3)
        out[c * 4 + 2] = _gf_mul(13, a0) ^ _gf_mul(9, a1) ^ _gf_mul(14, a2) ^ _gf_mul(11, a3)
        out[c * 4 + 3] = _gf_mul(11, a0) ^ _gf_mul(13, a1) ^ _gf_mul(9, a2) ^ _gf_mul(14, a3)
    return out


def _encrypt_block(block: bytes, round_keys: List[List[int]]) -> bytes:
    s = _add_round_key(list(block), round_keys[0])
    for rnd in range(1, 10):
        s = _sub_bytes(s)
        s = _shift_rows(s)
        s = _mix_columns(s)
        s = _add_round_key(s, round_keys[rnd])
    s = _sub_bytes(s)
    s = _shift_rows(s)
    s = _add_round_key(s, round_keys[10])
    return bytes(s)


def _decrypt_block(block: bytes, round_keys: List[List[int]]) -> bytes:
    s = _add_round_key(list(block), round_keys[10])
    for rnd in range(9, 0, -1):
        s = _inv_shift_rows(s)
        s = _inv_sub_bytes(s)
        s = _add_round_key(s, round_keys[rnd])
        s = _inv_mix_columns(s)
    s = _inv_shift_rows(s)
    s = _inv_sub_bytes(s)
    s = _add_round_key(s, round_keys[0])
    return bytes(s)


def aes_cbc_encrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    """Encrypt *data* (length must already be a multiple of 16 bytes)."""
    round_keys = _key_expansion(key)
    prev = iv
    out = bytearray()
    for i in range(0, len(data), 16):
        block = bytes(a ^ b for a, b in zip(data[i:i + 16], prev))
        enc = _encrypt_block(block, round_keys)
        out += enc
        prev = enc
    return bytes(out)


def aes_cbc_decrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    round_keys = _key_expansion(key)
    prev = iv
    out = bytearray()
    for i in range(0, len(data), 16):
        block = data[i:i + 16]
        dec = _decrypt_block(block, round_keys)
        out += bytes(a ^ b for a, b in zip(dec, prev))
        prev = block
    return bytes(out)
