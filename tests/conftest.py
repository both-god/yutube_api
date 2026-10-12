import os
import sys
import pytest

# Ensure root workspace directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Must be set before `main` is imported: it gates the cookie/logging bootstrap in the
# lifespan, which shells out to yt-dlp and would make tests slow and network-dependent.
os.environ.setdefault("TESTING", "1")


@pytest.fixture
def apple_music_html():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:title" content="Blinding Lights - Song by The Weeknd on Apple Music" />
        <meta property="og:description" content="Listen to Blinding Lights by The Weeknd on Apple Music." />
    </head>
    <body>
        <div class="songs-list-row__song-name">Blinding Lights</div>
        <div class="songs-list-row__song-name">In Your Eyes</div>
    </body>
    </html>
    """


@pytest.fixture
def odesli_json():
    return {
        "entityUniqueId": "AMAZON_SONG::B083335XYZ",
        "userCountry": "US",
        "pageUrl": "https://song.link/i/1499378610",
        "entitiesByUniqueId": {
            "AMAZON_SONG::B083335XYZ": {
                "id": "B083335XYZ",
                "type": "song",
                "title": "Blinding Lights",
                "artistName": "The Weeknd",
                "thumbnailUrl": "https://m.media-amazon.com/images/I/71.jpg",
            }
        },
        "linksByPlatform": {
            "amazonMusic": {
                "url": "https://music.amazon.com/albums/B083321528?trackAsin=B083335XYZ"
            },
            "youtube": {
                "url": "https://www.youtube.com/watch?q=blinding_lights_yt"
            }
        }
    }


@pytest.fixture
def apple_music_playlist_html():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:title" content="Today's Hits on Apple Music" />
        <meta property="og:description" content="The biggest songs in pop, hip-hop, R&B, and dance." />
    </head>
    <body>
        <div class="songs-list-row__song-name">Starboy</div>
        <div class="songs-list-row__song-name">Save Your Tears</div>
        <div class="songs-list-row__song-name">Die For You</div>
        <div class="songs-list-row__song-name">As It Was</div>
    </body>
    </html>
    """


@pytest.fixture
def apple_music_album_html():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta property="og:title" content="After Hours - Album by The Weeknd on Apple Music" />
        <meta property="og:description" content="Listen to After Hours by The Weeknd on Apple Music." />
    </head>
    <body>
        <div class="songs-list-row__song-name">Alone Again</div>
        <div class="songs-list-row__song-name">Too Late</div>
        <div class="songs-list-row__song-name">Hardest To Love</div>
        <div class="songs-list-row__song-name">Scared To Live</div>
        <div class="songs-list-row__song-name">Blinding Lights</div>
    </body>
    </html>
    """


@pytest.fixture
def jiosaavn_json():
    return {
        "id": "X10ceh5ZAWs",
        "song": "Kesariya",
        "singers": "Arijit Singh, Pritam",
        "duration": "268",
        "download_url": [
            {"quality": "12kbps", "link": "https://aac.saavncdn.com/kesariya_12kbps.mp4"},
            {"quality": "160kbps", "link": "https://aac.saavncdn.com/kesariya_160kbps.mp4"},
            {"quality": "320kbps", "link": "https://aac.saavncdn.com/kesariya_320kbps.mp4"}
        ]
    }


@pytest.fixture
def jiosaavn_album_json():
    return {
        "title": "Top Hindi Hits",
        "songs": [
            {
                "id": "song1",
                "song": "Kesariya",
                "singers": "Arijit Singh, Pritam",
                "duration": "268",
                "media_url": "https://aac.saavncdn.com/kesariya_320kbps.mp4"
            },
            {
                "id": "song2",
                "song": "Chaleya",
                "singers": "Arijit Singh, Anirudh",
                "duration": "200",
                "media_url": "https://aac.saavncdn.com/chaleya_320kbps.mp4"
            }
        ]
    }
