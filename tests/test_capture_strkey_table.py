#!/usr/bin/env python3
"""A mutated G... address is refused by capture.py before any request is made.

capture() checks the account id twice before it touches the network: ACCOUNT_SHAPE refuses
anything that is not `G` plus 55 base32 characters, and is_valid_account_id then decodes the
strkey and refuses a version byte other than 48 or a CRC16-XMODEM that does not verify. The
table below covers the distinct ways an address can be wrong, each built from bytes at run
time with an encoder independent of validate.py (base64.b32encode and binascii.crc_hqx), and
asserts the exact refusal, exit code 2, an untouched root and no network access.
"""

from __future__ import annotations

import base64
import binascii
import io
import socket
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import capture  # noqa: E402

VERSION_ACCOUNT = 6 << 3
PAYLOAD = bytes(range(1, 33))
# A real mainnet account from the shipped corpus, so the table is not only synthetic.
SHIPPED = "GA7DTK7GPOEQGXHI7MLA2OAIEL4365VG6PXUAVREMDVLC4MJIJ62KR75"


def crc(body: bytes) -> int:
    # crc_hqx with an initial value of 0 is CRC16-XMODEM: polynomial 0x1021, no reflection.
    return binascii.crc_hqx(body, 0)


def encode(version: int, payload: bytes, checksum: bytes | None = None) -> str:
    body = bytes([version]) + payload
    tail = crc(body).to_bytes(2, "little") if checksum is None else checksum
    return base64.b32encode(body + tail).decode("ascii")


VALID = encode(VERSION_ACCOUNT, PAYLOAD)
GOOD_CRC = crc(bytes([VERSION_ACCOUNT]) + PAYLOAD)
ZERO_BODY = bytes([VERSION_ACCOUNT]) + bytes(32)


def flip_bit(payload: bytes, index: int, bit: int) -> bytes:
    mutated = bytearray(payload)
    mutated[index] ^= 1 << bit
    return bytes(mutated)


def replace_char(address: str, index: int, char: str) -> str:
    return address[:index] + char + address[index + 1 :]


CHECKSUM = "checksum"
SHAPE = "shape"

# (label, mutated address, which refusal it must hit)
TABLE: list[tuple[str, str, str]] = [
    # Version 49 keeps the leading G (the top five bits of 48 and 49 agree) and carries a
    # correct checksum, so only the version byte comparison can refuse it.
    ("version byte 48 flipped to 49", encode(VERSION_ACCOUNT | 1, PAYLOAD), CHECKSUM),
    ("version byte 48 flipped to 52", encode(VERSION_ACCOUNT | 4, PAYLOAD), CHECKSUM),
    (
        "payload bit flipped, checksum kept",
        encode(VERSION_ACCOUNT, flip_bit(PAYLOAD, 10, 3), GOOD_CRC.to_bytes(2, "little")),
        CHECKSUM,
    ),
    (
        "checksum low nibble changed",
        encode(VERSION_ACCOUNT, PAYLOAD, (GOOD_CRC ^ 0x000F).to_bytes(2, "little")),
        CHECKSUM,
    ),
    (
        "checksum bytes transposed",
        encode(VERSION_ACCOUNT, PAYLOAD, GOOD_CRC.to_bytes(2, "big")),
        CHECKSUM,
    ),
    (
        "all-zero payload with a zero checksum",
        encode(VERSION_ACCOUNT, bytes(32), b"\x00\x00"),
        CHECKSUM,
    ),
    (
        "all-zero payload with the checksum of another payload",
        encode(VERSION_ACCOUNT, bytes(32), GOOD_CRC.to_bytes(2, "little")),
        CHECKSUM,
    ),
    ("last character of the shipped account changed", replace_char(SHIPPED, 55, "4"), CHECKSUM),
    ("truncated to 55 characters", VALID[:55], SHAPE),
    ("extended to 57 characters", VALID + "A", SHAPE),
    ("illegal base32 character 8", replace_char(VALID, 30, "8"), SHAPE),
    ("illegal base32 character 9", replace_char(VALID, 30, "9"), SHAPE),
    ("illegal base32 character 0", replace_char(VALID, 30, "0"), SHAPE),
    ("illegal base32 character 1", replace_char(VALID, 30, "1"), SHAPE),
    ("lowercased", VALID.lower(), SHAPE),
]


def refusal(address: str, kind: str) -> str:
    if kind == CHECKSUM:
        return (
            f"account {address!r} is G-shaped but its checksum does not verify; "
            "a typo is refused here rather than 404ing at Horizon"
        )
    return (
        f"account {address!r} is not a G... ed25519 account id; "
        "M... and C... addresses are not captured here"
    )


class NoNetwork(unittest.TestCase):
    """Every way out of the process is a mock that records being called."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.guards: dict[str, mock.MagicMock] = {}
        for target, name in (
            (capture, "fetch"),
            (capture.OPENER, "open"),
            (socket.socket, "connect"),
            (socket, "create_connection"),
            (socket, "getaddrinfo"),
        ):
            patcher = mock.patch.object(target, name, side_effect=AssertionError(name))
            self.guards[name] = patcher.start()
            self.addCleanup(patcher.stop)

    def assert_no_network(self) -> None:
        for guard in self.guards.values():
            guard.assert_not_called()

    def run_main(self, address: str) -> tuple[int, str]:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = capture.main(
                [
                    "--network",
                    "public",
                    "--account",
                    address,
                    "--id",
                    "strkey-table",
                    "--scenario",
                    "strkey table",
                    "--root",
                    str(self.root),
                ]
            )
        return code, stderr.getvalue()


class MutatedAddressTable(NoNetwork):
    def test_the_table_is_wide_enough(self) -> None:
        self.assertGreaterEqual(len(TABLE), 8)
        self.assertEqual(len({label for label, _, _ in TABLE}), len(TABLE))
        self.assertEqual(len({address for _, address, _ in TABLE}), len(TABLE))

    def test_the_unmutated_addresses_are_valid(self) -> None:
        for address in (VALID, SHIPPED):
            self.assertEqual(len(address), 56)
            self.assertTrue(capture.ACCOUNT_SHAPE.match(address), address)
            self.assertTrue(capture.is_valid_account_id(address), address)

    def test_each_row_reaches_the_check_it_names(self) -> None:
        """A checksum row must pass the shape check, or it is testing the wrong refusal."""
        self.assertNotEqual(GOOD_CRC & 0xFF, GOOD_CRC >> 8, "transposition would be a no-op")
        self.assertNotEqual(crc(ZERO_BODY), 0)
        self.assertNotEqual(crc(ZERO_BODY), GOOD_CRC)
        for label, address, kind in TABLE:
            with self.subTest(case=label):
                shaped = bool(capture.ACCOUNT_SHAPE.match(address))
                self.assertEqual(shaped, kind == CHECKSUM, address)

    def test_capture_raises_refused_before_any_request(self) -> None:
        for label, address, kind in TABLE:
            with self.subTest(case=label):
                with self.assertRaises(capture.Refused) as raised:
                    capture.capture(
                        "strkey-table", address, "strkey table", "public", self.root, False
                    )
                self.assertEqual(str(raised.exception), refusal(address, kind))
                self.assert_no_network()
                self.assertEqual(list(self.root.iterdir()), [])

    def test_main_exits_two_with_the_refusal(self) -> None:
        for label, address, kind in TABLE:
            with self.subTest(case=label):
                code, stderr = self.run_main(address)
                self.assertEqual(code, 2)
                self.assertEqual(stderr.strip(), f"capture refused: {refusal(address, kind)}")
                self.assert_no_network()
                self.assertEqual(list(self.root.iterdir()), [])


class ValidAddressReachesTheNetwork(NoNetwork):
    """The control: the same path with the unmutated address gets as far as fetch()."""

    def test_valid_address_is_not_refused_by_the_strkey_check(self) -> None:
        self.guards["fetch"].side_effect = RuntimeError("network reached")
        code, stderr = self.run_main(VALID)
        self.assertEqual(code, 1)
        self.assertEqual(stderr.strip(), "capture failed: network reached")
        self.guards["fetch"].assert_called_once_with(
            "https://horizon.stellar.org/", capture.ROOT_CAP
        )


if __name__ == "__main__":
    unittest.main()
