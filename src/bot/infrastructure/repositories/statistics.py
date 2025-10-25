import json
from datetime import datetime
from hashlib import sha256
from typing import Optional

from bot.domain.repositories.statistics import StatisticsRepositoryInterface


class RedisStatisticsRepository(StatisticsRepositoryInterface):
    def _key(self, base: str) -> str:
        return f"{self.key_prefix}:{base}" if self.key_prefix else base

    def _queue_key(self) -> str:
        return self._key("notifications:queue")

    def _users_pattern(self) -> str:
        return self._key("notifications:user:*")

    def _group_counts_cache_key(self) -> str:
        url_hash = sha256(self.public_root_url.encode()).hexdigest()[:12]
        return self._key(f"stats:group_counts:{url_hash}")

    async def get_queue_len(self) -> int:
        try:
            return int(await self.redis.llen(self._queue_key()))
        except Exception:
            return 0

    async def get_scheduled_total(self) -> int:
        total = 0
        try:
            async for key in self.redis.scan_iter(match=self._users_pattern()):
                total += int(await self.redis.zcard(key))
        except Exception:
            pass
        return total

    async def get_disk_group_counts(self) -> tuple[dict[str, int], int, Optional[datetime]]:
        try:
            raw = await self.redis.get(self._group_counts_cache_key())
            if not raw:
                return {}, 0, None
            data = json.loads(raw if isinstance(raw, str) else raw.decode())
            groups = {str(k): int(v) for k, v in (data.get("groups") or {}).items()}
            common = int(data.get("common") or 0)
            computed_at_raw = data.get("computed_at")
            computed_at = None
            if computed_at_raw:
                try:
                    computed_at = datetime.fromisoformat(str(computed_at_raw).replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    computed_at = None
            return groups, common, computed_at
        except Exception:
            return {}, 0, None
