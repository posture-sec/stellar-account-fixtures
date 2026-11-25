#!/usr/bin/env python3
"""Pin fetch()'s retry schedule: three attempts, 1.5 s, 3.0 s and 4.5 s apart, no retry on 4xx.

Every other capture test replaces fetch wholesale, so the backoff multiplier, the attempt
ceiling and the 4xx short-circuit are otherwise unexercised: a change to any of them passes
the suite. These tests patch OPENER.open with scripted failures and time.sleep with a
recorder, so the schedule is observed exactly and no test waits on a real clock or opens a
socket.
"""

from __future__ import annotations

import email.message
import io
import sys
import tempfile
import time
import unittest
import urllib.error
from collections.abc import Callable
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

import capture  # noqa: E402

URL = "https://horizon.stellar.org/"
ACCOUNT_ID = "GAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWHF"
SCHEDULE = [1.5, 3.0, 4.5]


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(URL, code, f"status {code}", email.message.Message(), None)


class Response:
    """The context manager OPENER.open returns on success."""

    def __init__(self, body: bytes, status: int = 200) -> None:
        self.body = body
        self.status = status

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        return self.body[:size]


def transient_failures() -> list[tuple[str, type[BaseException], Callable[[], BaseException]]]:
    """(label, the type name fetch reports, a factory for one failure) per retried kind."""
    return [
        ("HTTP 500", urllib.error.HTTPError, lambda: http_error(500)),
        ("HTTP 502", urllib.error.HTTPError, lambda: http_error(502)),
        ("HTTP 503", urllib.error.HTTPError, lambda: http_error(503)),
        ("URLError", urllib.error.URLError, lambda: urllib.error.URLError("no route")),
        ("TimeoutError", TimeoutError, lambda: TimeoutError("timed out")),
        ("OSError", OSError, lambda: OSError("network is down")),
        ("ConnectionResetError", ConnectionResetError, lambda: ConnectionResetError()),
    ]


class PatchedNetwork(unittest.TestCase):
    """OPENER.open answers from a script and time.sleep only records its argument."""

    def setUp(self) -> None:
        sleep = mock.patch.object(capture.time, "sleep")
        self.sleep = sleep.start()
        self.addCleanup(sleep.stop)
        opener = mock.patch.object(capture.OPENER, "open")
        self.open = opener.start()
        self.addCleanup(opener.stop)

    def slept(self) -> list[float]:
        return [call.args[0] for call in self.sleep.call_args_list]


class FetchRetrySchedule(PatchedNetwork):
    def test_exhaustion_sleeps_on_the_schedule_then_raises(self) -> None:
        for label, kind, make in transient_failures():
            with self.subTest(failure=label):
                self.sleep.reset_mock()
                self.open.reset_mock()
                self.open.side_effect = [make(), make(), make()]
                with self.assertRaises(RuntimeError) as raised:
                    capture.fetch(URL, capture.ROOT_CAP)
                self.assertEqual(self.slept(), SCHEDULE)
                self.assertEqual(self.open.call_count, 3)
                self.assertEqual(
                    str(raised.exception), f"{URL} unreachable after 3 attempts: {kind.__name__}"
                )

    def test_schedule_is_one_and_a_half_seconds_times_the_attempt(self) -> None:
        self.open.side_effect = [http_error(500)] * 3
        with self.assertRaises(RuntimeError):
            capture.fetch(URL, capture.ROOT_CAP)
        self.assertEqual(self.slept(), [1.5 * (attempt + 1) for attempt in range(3)])

    def test_a_fourth_attempt_is_never_made(self) -> None:
        # A fourth scripted answer would succeed; reaching it would mean a raised ceiling.
        self.open.side_effect = [http_error(500)] * 3 + [Response(b"{}")]
        with self.assertRaises(RuntimeError):
            capture.fetch(URL, capture.ROOT_CAP)
        self.assertEqual(self.open.call_count, 3)
        self.assertEqual(len(self.sleep.call_args_list), 3)

    def test_a_client_error_is_refused_at_once(self) -> None:
        for code in (400, 401, 403, 404, 410, 429, 499):
            with self.subTest(code=code):
                self.sleep.reset_mock()
                self.open.reset_mock()
                self.open.side_effect = [http_error(code), Response(b"{}")]
                with self.assertRaises(capture.Refused) as raised:
                    capture.fetch(URL, capture.ROOT_CAP)
                self.assertEqual(str(raised.exception), f"{URL} returned HTTP {code}")
                self.assertEqual(self.open.call_count, 1)
                self.sleep.assert_not_called()

    def test_a_client_error_after_a_retry_stops_the_loop(self) -> None:
        self.open.side_effect = [http_error(503), http_error(404), Response(b"{}")]
        with self.assertRaises(capture.Refused):
            capture.fetch(URL, capture.ROOT_CAP)
        self.assertEqual(self.open.call_count, 2)
        self.assertEqual(self.slept(), [1.5])

    def test_recovery_returns_the_body_after_the_sleeps_it_needed(self) -> None:
        self.open.side_effect = [
            http_error(500),
            urllib.error.URLError("no route"),
            Response(b'{"ok": true}'),
        ]
        self.assertEqual(capture.fetch(URL, capture.ROOT_CAP), b'{"ok": true}')
        self.assertEqual(self.slept(), [1.5, 3.0])

    def test_a_first_success_does_not_sleep(self) -> None:
        self.open.side_effect = [Response(b"{}")]
        self.assertEqual(capture.fetch(URL, capture.ROOT_CAP), b"{}")
        self.sleep.assert_not_called()

    def test_each_attempt_uses_the_same_request_and_timeout(self) -> None:
        self.open.side_effect = [http_error(500)] * 3
        with self.assertRaises(RuntimeError):
            capture.fetch(URL, capture.ROOT_CAP)
        requests = [call.args[0] for call in self.open.call_args_list]
        self.assertEqual({r.full_url for r in requests}, {URL})
        self.assertEqual({r.get_header("User-agent") for r in requests}, {capture.USER_AGENT})
        self.assertEqual([call.kwargs["timeout"] for call in self.open.call_args_list], [15] * 3)

    def test_no_real_time_passes(self) -> None:
        self.open.side_effect = [OSError("down")] * 3
        started = time.monotonic()
        with self.assertRaises(RuntimeError):
            capture.fetch(URL, capture.ROOT_CAP)
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual(sum(self.slept()), 9.0)


class CaptureExitCodesOnFetchFailure(PatchedNetwork):
    """The same two outcomes seen through main(): exhaustion exits 1, a 4xx exits 2."""

    def run_main(self) -> tuple[int, str, Path]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = capture.main(
                [
                    "--network",
                    "public",
                    "--account",
                    ACCOUNT_ID,
                    "--id",
                    "retry-schedule",
                    "--scenario",
                    "retry test",
                    "--root",
                    tmp.name,
                ]
            )
        return code, stderr.getvalue(), Path(tmp.name)

    def test_exhausted_retries_exit_one_and_write_nothing(self) -> None:
        self.open.side_effect = [urllib.error.URLError("no route")] * 3
        code, stderr, root = self.run_main()
        self.assertEqual(code, 1)
        self.assertEqual(
            stderr.strip(), f"capture failed: {URL} unreachable after 3 attempts: URLError"
        )
        self.assertEqual(self.slept(), SCHEDULE)
        self.assertEqual(list(root.iterdir()), [])

    def test_a_client_error_exits_two_without_sleeping(self) -> None:
        self.open.side_effect = [http_error(429)]
        code, stderr, root = self.run_main()
        self.assertEqual(code, 2)
        self.assertEqual(stderr.strip(), f"capture refused: {URL} returned HTTP 429")
        self.sleep.assert_not_called()
        self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
