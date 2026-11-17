"""Testovi HTTP dohvata s ponavljanjem (HttpSource), bez mreže."""

import pytest
import requests

from zrakhr.collectors import HttpSource


class Source(HttpSource):
    source = "test"


class FakeResponse:
    """Odgovor s odabranim HTTP statusom."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.content = b"<ok/>"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)  # type: ignore[arg-type]


def test_temporary_errors_are_retried_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mrežna greška se ponavlja, a treći pokušaj uspijeva."""
    calls: list[str] = []

    def flaky_get(url: str, **_: object) -> FakeResponse:
        calls.append(url)
        if len(calls) < 3:
            raise requests.ConnectionError("mreža nije dostupna")
        return FakeResponse(200)

    monkeypatch.setattr(requests, "get", flaky_get)

    result = Source(retries=3, backoff=0)._get("https://example.org", None, lambda r: r.content)

    assert result == b"<ok/>"
    assert len(calls) == 3


def test_client_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 404 se ne popravlja ponavljanjem, pa se greška javlja odmah."""
    calls: list[str] = []

    def missing_get(url: str, **_: object) -> FakeResponse:
        calls.append(url)
        return FakeResponse(404)

    monkeypatch.setattr(requests, "get", missing_get)

    with pytest.raises(requests.HTTPError):
        Source(retries=3, backoff=0)._get("https://example.org", None, lambda r: r.content)
    assert len(calls) == 1
