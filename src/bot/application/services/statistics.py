from collections import Counter
from datetime import datetime

from bot.domain.entities.statistics import StatsSnapshot
from bot.domain.entities.user import UserEntity
from bot.domain.repositories.statistics import StatisticsRepositoryInterface
from bot.domain.services.statistics import StatisticsServiceInterface
from bot.domain.services.user import UserServiceInterface


class StatisticsService(StatisticsServiceInterface):
    def __init__(
        self,
        user_service: UserServiceInterface,
        repo: StatisticsRepositoryInterface,
    ):
        self.user_service = user_service
        self.repo = repo

    async def build_snapshot(self) -> StatsSnapshot:
        users = await self.user_service.list_all_users()

        snap = StatsSnapshot()
        snap.users_total = len(users)
        snap.users_enabled = sum(1 for u in users if getattr(u, "enable_notifications", False))

        by_course: dict[str, int] = {}
        by_group: dict[str, int] = {}
        excluded_counter: Counter[str] = Counter()

        for u in users:
            course = getattr(u, "user_course", None)
            group = getattr(u, "user_study_group", None)
            if course:
                by_course[str(course)] = by_course.get(str(course), 0) + 1
            if group:
                by_group[str(group)] = by_group.get(str(group), 0) + 1
            for s in (u.excluded_disciplines or set()):
                excluded_counter[s] += 1

        snap.by_course = by_course
        snap.by_group = by_group
        snap.top_excluded = {k: v for k, v in excluded_counter.most_common(10)}

        snap.queue_len = await self.repo.get_queue_len()
        snap.scheduled_total = await self.repo.get_scheduled_total()

        groups, common, computed_at = await self.repo.get_disk_group_counts()
        snap.disk_groups = groups
        snap.disk_common = common
        snap.disk_computed_at = computed_at

        return snap

