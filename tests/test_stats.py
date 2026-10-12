import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from plugins.admin import _build_stats, bot_stats


@pytest.mark.asyncio
async def test_build_stats_returns_single_string():
    mock_client = AsyncMock()
    mock_user = MagicMock()
    mock_user.first_name = "Admin"
    mock_user.last_name = "User"
    mock_client.get_users.return_value = mock_user

    with patch("plugins.admin.scan_keys", return_value=["user_token:12345"]), \
         patch("plugins.admin.redis_client") as mock_redis, \
         patch("plugins.admin.is_admin", return_value=True):
        
        mock_redis.get.return_value = "5"
        mock_redis.info.return_value = {
            "used_memory_human": "10M",
            "used_memory_peak_human": "15M",
            "uptime_in_seconds": 3600,
            "connected_clients": 2,
            "instantaneous_ops_per_sec": 10,
            "total_commands_processed": 500,
            "keyspace_hits": 100,
            "keyspace_misses": 10,
        }

        result = await _build_stats(mock_client)
        assert isinstance(result, str)
        assert "<h1>Bot Statistics Dashboard</h1>" in result
        assert "<h2>User Metrics</h2>" in result
        assert "<h2>Request Analytics</h2>" in result
        assert "<h2>Top 10 Users Today</h2>" in result
        assert "<h2>Redis Infrastructure</h2>" in result
        assert "<h2>Failure Analytics</h2>" in result


@pytest.mark.asyncio
async def test_bot_stats_sends_only_one_response_to_admin():
    mock_client = AsyncMock()
    mock_client.rnd_id.return_value = 12345
    mock_message = MagicMock()
    mock_message.chat.id = 999
    mock_message.from_user.id = 12345

    with patch("plugins.admin.is_admin", return_value=True), \
         patch("plugins.admin._build_stats", new_callable=AsyncMock) as mock_build:
        
        mock_build.return_value = "<h1>Dashboard Content</h1>"

        await bot_stats(mock_client, mock_message)

        # Ensure send_rich_message was called exactly ONCE (not twice)
        assert mock_client.send_rich_message.call_count == 1
        call_args = mock_client.send_rich_message.call_args
        assert call_args.kwargs["chat_id"] == 999
        assert call_args.kwargs["rich_message"].html == "<h1>Dashboard Content</h1>"
        assert call_args.kwargs["reply_markup"] is not None
