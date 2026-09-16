import pytest

from app.channel.resolver import ChannelHandleResolver, normalize_handle


def test_normalize_handle_accepts_handle_and_url() -> None:
    assert normalize_handle("@Reelios") == "@Reelios"
    assert normalize_handle("https://www.youtube.com/@Reelios/") == "@Reelios"
    assert normalize_handle("youtube.com/@Reelios") == "@Reelios"


def test_resolver_parses_channel_id_from_html() -> None:
    html = '<link rel="canonical" href="https://www.youtube.com/@Reelios"><meta itemprop="channelId" content="UC123">'
    resolver = ChannelHandleResolver(fetch_html=lambda _: html)
    identity = resolver.resolve("@Reelios")
    assert identity.channel_id == "UC123"
    assert identity.channel_handle == "@Reelios"


def test_invalid_handle_is_rejected() -> None:
    with pytest.raises(ValueError):
        normalize_handle("not a valid handle")
