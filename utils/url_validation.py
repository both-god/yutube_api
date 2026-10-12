"""Reject unsupported target URLs before they reach a yt-dlp subprocess (SSRF guard).

Supports YouTube, Apple Music, Amazon Music, SoundCloud, JioSaavn, and Spotify hosts, as well as bare search queries.
"""
from urllib.parse import urlparse
from fastapi import HTTPException

_ALLOWED_HOSTS = frozenset({
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "music.youtube.com", "youtu.be", "www.youtu.be",
    "music.apple.com",
    "soundcloud.com", "www.soundcloud.com", "m.soundcloud.com",
    "jiosaavn.com", "www.jiosaavn.com", "saavn.com", "www.saavn.com",
    "spotify.com", "open.spotify.com", "www.spotify.com",
})


def is_allowed_target(value: str) -> bool:
    if not value or not value.strip():
        return False
    parsed = urlparse(value.strip())
    if parsed.scheme in ("http", "https"):
        # hostname strips userinfo/port, so "evil.com@youtube.com" -> "evil.com" is blocked
        hostname = (parsed.hostname or "").lower()
        if hostname in _ALLOWED_HOSTS:
            return True
        if hostname.startswith("music.amazon."):
            return True
        return False
    if parsed.scheme:
        return False  # file:, ftp:, etc. — never allowed
    # No scheme: a bare video id or search phrase.
    return True


def validate_target(value: str) -> str:
    """Return value if it's an allowed target URL or search phrase, else raise 400."""
    if not is_allowed_target(value):
        raise HTTPException(status_code=400, detail="Invalid target: only allowed streaming target URLs or search queries permitted")
    return value


validate_youtube_target = validate_target
