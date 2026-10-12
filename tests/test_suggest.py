import pytest
from unittest.mock import AsyncMock, patch
from utils.formatters import process_video
from utils.search_service import fetch_suggestions, fetch_results, MEMORY_CACHE


@pytest.mark.asyncio
async def test_process_video_includes_video_id_and_time():
    item = {
        "id": {"videoId": "test_id_123"},
        "snippet": {
            "title": "Artist Name - Cool Song",
            "channelTitle": "Cool Channel",
            "thumbnails": {"high": {"url": "https://img.youtube.com/vi/test_id_123/hqdefault.jpg"}}
        }
    }
    details = {
        "contentDetails": {"duration": "PT3M45S"},
        "statistics": {"viewCount": "1500000"}
    }
    res = process_video(item, details)
    assert res is not None
    assert res["video_id"] == "test_id_123"
    assert res["title"] == "Artist Name - Cool Song"
    assert res["time"] == "3:45"
    assert res["duration"] == "3:45"
    assert res["channel_name"] == "Cool Channel"


@pytest.mark.asyncio
async def test_fetch_suggestions_structure():
    mock_html = """
    <html>
    <script>
    var ytInitialData = {
        "contents": {
            "twoColumnSearchResultsRenderer": {
                "primaryContents": {
                    "sectionListRenderer": {
                        "contents": [
                            {
                                "itemSectionRenderer": {
                                    "contents": [
                                        {
                                            "videoRenderer": {
                                                "videoId": "vid_1",
                                                "title": {"runs": [{"text": "Song 1"}]},
                                                "lengthText": {"simpleText": "3:30"},
                                                "ownerText": {"runs": [{"text": "Channel 1"}]},
                                                "viewCountText": {"simpleText": "1,000 views"}
                                            }
                                        },
                                        {
                                            "videoRenderer": {
                                                "videoId": "vid_2",
                                                "title": {"runs": [{"text": "Song 2"}]},
                                                "lengthText": {"simpleText": "4:15"},
                                                "ownerText": {"runs": [{"text": "Channel 2"}]},
                                                "viewCountText": {"simpleText": "2,000 views"}
                                            }
                                        },
                                        {
                                            "videoRenderer": {
                                                "videoId": "vid_3",
                                                "title": {"runs": [{"text": "Song 3"}]},
                                                "lengthText": {"simpleText": "2:50"},
                                                "ownerText": {"runs": [{"text": "Channel 3"}]},
                                                "viewCountText": {"simpleText": "3,000 views"}
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            }
        }
    };
    </script>
    </html>
    """

    class MockResponse:
        text = mock_html

    with patch("utils.search_service._client.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = MockResponse()
        MEMORY_CACHE.clear()

        data = await fetch_suggestions("test query", limit=2)
        assert "results" in data
        assert "suggested" in data
        assert len(data["results"]) == 2
        assert len(data["suggested"]) > 0

        first = data["results"][0]
        assert first["title"] == "Song 1"
        assert first["video_id"] == "vid_1"
        assert first["time"] == "3:30"
        assert first["duration"] == "3:30"
