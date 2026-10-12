"""Tests for multi-platform link resolution, scrapers, and SSRF guards in ytube_api."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from utils.platform_resolvers import (
    EmptyPlaylistError,
    MalformedURLError,
    NetworkTimeoutError,
    PlatformHTTPError,
    ResolverError,
    detect_provider,
    get_audio_stream,
    is_amazon_music,
    is_apple_music,
    is_jiosaavn,
    is_plain_text_query,
    is_soundcloud,
    is_spotify,
    parse_apple_music_html,
    parse_jiosaavn_json,
    parse_odesli_response,
    resolve_amazon_music,
    resolve_apple_music,
    resolve_jiosaavn,
    resolve_soundcloud,
    resolve_spotify,
    resolve_to_playable_stream,
    select_highest_bitrate_url,
    strip_apple_music_branding,
)
from utils.url_validation import is_allowed_target, validate_target


# ── 1. Provider Detection & URL Validation Tests ──────────────────────────────

def test_is_apple_music():
    assert is_apple_music("https://music.apple.com/us/album/blinding-lights/1499378608?i=1499378610")
    assert is_apple_music("https://music.apple.com/us/playlist/todays-hits/pl.f4d106fed2bd41149aa18d3b43d70319")
    assert not is_apple_music("https://spotify.com/track/12345")
    assert not is_apple_music("invalid-url")
    assert not is_apple_music(None)


def test_is_amazon_music():
    assert is_amazon_music("https://music.amazon.com/albums/B083321528")
    assert is_amazon_music("https://music.amazon.in/tracks/B083335XYZ")
    assert not is_amazon_music("https://music.apple.com/us/album/test/123")
    assert not is_amazon_music(None)


def test_is_soundcloud():
    assert is_soundcloud("https://soundcloud.com/artist-name/track-title")
    assert is_soundcloud("https://www.soundcloud.com/artist/sets/my-playlist")
    assert not is_soundcloud("https://soundcloud.com/")
    assert not is_soundcloud(None)


def test_is_jiosaavn():
    assert is_jiosaavn("https://www.jiosaavn.com/song/kesariya/X10ceh5ZAWs")
    assert is_jiosaavn("https://saavn.com/s/song/hindi/kesariya/X10ceh5ZAWs")
    assert not is_jiosaavn("https://youtube.com/watch?v=123")
    assert not is_jiosaavn(None)


def test_is_spotify():
    assert is_spotify("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT")
    assert is_spotify("https://open.spotify.com/album/1DFam4w928374")
    assert not is_spotify("https://amazon.com")
    assert not is_spotify(None)


def test_is_plain_text_query():
    assert is_plain_text_query("Blinding Lights The Weeknd")
    assert is_plain_text_query("Kesariya Arijit Singh 🔥")
    assert not is_plain_text_query("https://music.apple.com/us/album/test/123")
    assert not is_plain_text_query("http://example.com")
    assert not is_plain_text_query(None)


def test_detect_provider():
    assert detect_provider("https://music.apple.com/us/album/test/123") == "apple_music"
    assert detect_provider("https://music.amazon.com/albums/B083321528") == "amazon_music"
    assert detect_provider("https://soundcloud.com/user/track") == "soundcloud"
    assert detect_provider("https://www.jiosaavn.com/song/test/123") == "jiosaavn"
    assert detect_provider("https://open.spotify.com/track/123") == "spotify"
    assert detect_provider("Starboy The Weeknd") == "text_search"
    assert detect_provider("https://example.com/audio.mp3") == "generic_url"

    with pytest.raises(MalformedURLError):
        detect_provider("")

    with pytest.raises(MalformedURLError):
        detect_provider(None)


# ── 2. Apple Music Scraper & Parser Tests ────────────────────────────────────

def test_strip_apple_music_branding():
    assert strip_apple_music_branding("Blinding Lights on Apple Music") == "Blinding Lights"
    assert strip_apple_music_branding("Starboy - Song by The Weeknd on Apple Music") == "Starboy by The Weeknd"
    assert strip_apple_music_branding("After Hours - Album by The Weeknd") == "After Hours by The Weeknd"
    assert strip_apple_music_branding("") == ""


def test_parse_apple_music_html(apple_music_html):
    parsed = parse_apple_music_html(apple_music_html)
    assert parsed["title"] == "Blinding Lights by The Weeknd"
    assert "Listen to Blinding Lights" in parsed["description"]
    assert "Blinding Lights" in parsed["tracks"]
    assert "In Your Eyes" in parsed["tracks"]


def test_parse_apple_music_html_empty():
    with pytest.raises(ResolverError):
        parse_apple_music_html("")


@pytest.mark.asyncio
async def test_resolve_apple_music_success(apple_music_html):
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.text = AsyncMock(return_value=apple_music_html)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    res = await resolve_apple_music("https://music.apple.com/us/album/after-hours/1499378608", session=mock_session)
    assert res["provider"] == "apple_music"
    assert res["title"] == "Blinding Lights by The Weeknd"
    assert "Blinding Lights" in res["tracks"]


@pytest.mark.asyncio
async def test_resolve_apple_music_http_404():
    mock_resp = AsyncMock()
    mock_resp.status = 404

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with pytest.raises(PlatformHTTPError) as exc_info:
        await resolve_apple_music("https://music.apple.com/us/album/not-found/404", session=mock_session)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_apple_music_timeout():
    mock_session = MagicMock()
    mock_session.get.side_effect = asyncio.TimeoutError()

    with pytest.raises(NetworkTimeoutError):
        await resolve_apple_music("https://music.apple.com/us/album/test/123", session=mock_session)


# ── 3. Amazon Music & Spotify Parser Tests ────────────────────────────────────

def test_parse_odesli_response(odesli_json):
    parsed = parse_odesli_response(odesli_json)
    assert parsed["entity_id"] == "AMAZON_SONG::B083335XYZ"
    assert parsed["title"] == "Blinding Lights"
    assert parsed["artist"] == "The Weeknd"
    assert parsed["youtube_url"] == "https://www.youtube.com/watch?q=blinding_lights_yt"
    assert parsed["search_query"] == "Blinding Lights The Weeknd"


def test_parse_odesli_response_missing_youtube():
    data = {
        "entityUniqueId": "AMAZON_SONG::123",
        "entitiesByUniqueId": {
            "AMAZON_SONG::123": {"title": "Song Without YT", "artistName": "Artist"}
        },
        "linksByPlatform": {}
    }
    parsed = parse_odesli_response(data)
    assert parsed["youtube_url"] is None
    assert parsed["search_query"] == "Song Without YT Artist"


@pytest.mark.asyncio
async def test_resolve_amazon_music_success(odesli_json):
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=odesli_json)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    res = await resolve_amazon_music("https://music.amazon.com/albums/B083321528", session=mock_session)
    assert res["provider"] == "amazon_music"
    assert res["title"] == "Blinding Lights"
    assert res["youtube_url"] == "https://www.youtube.com/watch?q=blinding_lights_yt"


@pytest.mark.asyncio
async def test_resolve_spotify_success(odesli_json):
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=odesli_json)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    res = await resolve_spotify("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT", session=mock_session)
    assert res["provider"] == "spotify"
    assert res["title"] == "Blinding Lights"
    assert res["youtube_url"] == "https://www.youtube.com/watch?q=blinding_lights_yt"


# ── 4. JioSaavn Bitrate Selection & Parser Tests ─────────────────────────────

def test_select_highest_bitrate_url():
    # List format
    media_list = [
        {"quality": "12kbps", "link": "https://aac.saavncdn.com/12.mp4"},
        {"quality": "160kbps", "link": "https://aac.saavncdn.com/160.mp4"},
        {"quality": "320kbps", "link": "https://aac.saavncdn.com/320.mp4"},
        {"quality": "96kbps", "link": "https://aac.saavncdn.com/96.mp4"},
    ]
    assert select_highest_bitrate_url(media_list) == "https://aac.saavncdn.com/320.mp4"

    # Dict format
    media_dict = {
        "160kbps": "https://aac.saavncdn.com/160.mp4",
        "320kbps": "https://aac.saavncdn.com/320.mp4",
    }
    assert select_highest_bitrate_url(media_dict) == "https://aac.saavncdn.com/320.mp4"

    # Single string format
    assert select_highest_bitrate_url("https://aac.saavncdn.com/direct.mp4") == "https://aac.saavncdn.com/direct.mp4"
    assert select_highest_bitrate_url(None) is None


def test_parse_jiosaavn_json(jiosaavn_json):
    parsed = parse_jiosaavn_json(jiosaavn_json)
    assert parsed["title"] == "Kesariya"
    assert parsed["artist"] == "Arijit Singh, Pritam"
    assert parsed["duration"] == 268
    assert parsed["stream_url"] == "https://aac.saavncdn.com/kesariya_320kbps.mp4"
    assert parsed["search_query"] == "Kesariya Arijit Singh, Pritam"


@pytest.mark.asyncio
async def test_resolve_jiosaavn_success(jiosaavn_json):
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=jiosaavn_json)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    res = await resolve_jiosaavn("https://www.jiosaavn.com/song/kesariya/X10ceh5ZAWs", session=mock_session)
    assert res["provider"] == "jiosaavn"
    assert res["title"] == "Kesariya"
    assert res["stream_url"] == "https://aac.saavncdn.com/kesariya_320kbps.mp4"


# ── 5. SoundCloud Resolver Tests ─────────────────────────────────────────────

def test_resolve_soundcloud():
    res = resolve_soundcloud("https://soundcloud.com/artist/track-name")
    assert res["provider"] == "soundcloud"
    assert res["stream_url"] == "https://soundcloud.com/artist/track-name"
    assert res["bypass_search"] is True

    with pytest.raises(MalformedURLError):
        resolve_soundcloud("invalid-url")


# ── 6. Master Dispatcher Tests ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resolve_to_playable_stream_plain_text():
    res = await resolve_to_playable_stream("Shape of You Ed Sheeran")
    assert res["provider"] == "text_search"
    assert res["search_query"] == "Shape of You Ed Sheeran"
    assert res["bypass_search"] is False


@pytest.mark.asyncio
async def test_resolve_to_playable_stream_jiosaavn(jiosaavn_json):
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=jiosaavn_json)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    res = await resolve_to_playable_stream("https://www.jiosaavn.com/song/kesariya/X10ceh5ZAWs", session=mock_session)
    assert res["provider"] == "jiosaavn"
    assert res["stream_url"] == "https://aac.saavncdn.com/kesariya_320kbps.mp4"
    assert res["bypass_search"] is True


@pytest.mark.asyncio
async def test_resolve_to_playable_stream_unicode_emojis():
    res = await resolve_to_playable_stream("🔥 🎧 Srivalli - Pushpa 🎵 ✨")
    assert res["provider"] == "text_search"
    assert res["search_query"] == "🔥 🎧 Srivalli - Pushpa 🎵 ✨"


# ── 7. SSRF Guard & Target Validation Tests ──────────────────────────────────

def test_url_validation_ssrf_allowed_hosts():
    assert is_allowed_target("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert is_allowed_target("https://youtu.be/dQw4w9WgXcQ")
    assert is_allowed_target("https://music.apple.com/us/album/test/123")
    assert is_allowed_target("https://music.amazon.com/albums/B083321528")
    assert is_allowed_target("https://music.amazon.in/tracks/B083335XYZ")
    assert is_allowed_target("https://soundcloud.com/artist/track")
    assert is_allowed_target("https://www.jiosaavn.com/song/test/123")
    assert is_allowed_target("https://open.spotify.com/track/12345")
    assert is_allowed_target("Arijit Singh hits")


def test_url_validation_ssrf_blocked_hosts():
    assert not is_allowed_target("https://evil.com/malicious.mp3")
    assert not is_allowed_target("http://169.254.169.254/latest/meta-data/")
    assert not is_allowed_target("ftp://files.example.com/test.mp3")


def test_validate_target_raises():
    assert validate_target("https://music.apple.com/us/album/test/123") == "https://music.apple.com/us/album/test/123"

    with pytest.raises(HTTPException) as exc_info:
        validate_target("https://evil.com/hack")
    assert exc_info.value.status_code == 400


# ── 8. Albums, Playlists & Multi-Track Resolution Examples ───────────────────

@pytest.mark.asyncio
async def test_apple_music_playlist_resolution(apple_music_playlist_html):
    """Test resolution of Apple Music playlist URLs containing multiple tracks."""
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.text = AsyncMock(return_value=apple_music_playlist_html)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    url = "https://music.apple.com/us/playlist/todays-hits/pl.f4d106fed2bd41149aa18d3b43d70319"
    res = await resolve_apple_music(url, session=mock_session)

    assert res["provider"] == "apple_music"
    assert res["title"] == "Today's Hits"
    assert len(res["tracks"]) == 4
    assert res["tracks"] == ["Starboy", "Save Your Tears", "Die For You", "As It Was"]


@pytest.mark.asyncio
async def test_apple_music_album_resolution(apple_music_album_html):
    """Test resolution of Apple Music album URLs containing complete album tracklists."""
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.text = AsyncMock(return_value=apple_music_album_html)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    url = "https://music.apple.com/us/album/after-hours/1499378608"
    res = await resolve_apple_music(url, session=mock_session)

    assert res["provider"] == "apple_music"
    assert res["title"] == "After Hours by The Weeknd"
    assert len(res["tracks"]) == 5
    assert "Blinding Lights" in res["tracks"]
    assert "Hardest To Love" in res["tracks"]


def test_soundcloud_set_playlist_resolution():
    """Test detection and resolution of SoundCloud set / playlist URLs."""
    url = "https://soundcloud.com/artist-name/sets/summer-vibes-2024"
    assert is_soundcloud(url)
    assert detect_provider(url) == "soundcloud"

    res = resolve_soundcloud(url)
    assert res["provider"] == "soundcloud"
    assert res["stream_url"] == url
    assert res["bypass_search"] is True


@pytest.mark.asyncio
async def test_amazon_music_album_resolution(odesli_json):
    """Test resolution of Amazon Music album URLs using Odesli link API."""
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=odesli_json)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    url = "https://music.amazon.com/albums/B083321528"
    assert is_amazon_music(url)
    assert detect_provider(url) == "amazon_music"

    res = await resolve_amazon_music(url, session=mock_session)
    assert res["provider"] == "amazon_music"
    assert res["title"] == "Blinding Lights"
    assert res["youtube_url"] == "https://www.youtube.com/watch?q=blinding_lights_yt"


@pytest.mark.asyncio
async def test_resolve_to_playable_stream_playlist_dispatcher(apple_music_playlist_html):
    """Test master dispatcher routing for playlist link resolution."""
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.text = AsyncMock(return_value=apple_music_playlist_html)

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    url = "https://music.apple.com/us/playlist/todays-hits/pl.f4d106fed2bd41149aa18d3b43d70319"
    res = await resolve_to_playable_stream(url, session=mock_session)

    assert res["provider"] == "apple_music"
    assert len(res["tracks"]) == 4
    assert res["tracks"][0] == "Starboy"
