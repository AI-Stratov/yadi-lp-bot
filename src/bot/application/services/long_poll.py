import asyncio
from datetime import datetime
from hashlib import sha256
from typing import Any, Optional
import json

import aiohttp
from bot.common.logs import logger
from bot.domain.entities.notification import NotificationTask
from bot.domain.services.long_poll import LongPollServiceInterface
from bot.domain.entities.mappings import StudyGroups, TOPICS


class YandexDiskPollingService(LongPollServiceInterface):
    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="yadisk_poll")
        logger.info("✅ Опрос Яндекс.Диска запущен")

    async def stop(self):
        self._running = False
        if hasattr(self, "_task"):
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Опрос Яндекс.Диска остановлен")

    async def _poll_loop(self):
        """Основной цикл опроса."""
        while self._running:
            try:
                new_files = await self._check_for_new_files()
                if new_files:
                    logger.info(f"📨 Найдено новых файлов: {new_files}")
            except Exception as e:
                logger.exception(f"Ошибка опроса: {e}")

            await asyncio.sleep(self.poll_interval)

    async def _check_for_new_files(self) -> int:
        """Проверяет диск и добавляет новые файлы в очередь."""
        # Читаем чекпоинт - время последней проверки
        checkpoint_key = self._get_checkpoint_key()
        last_check = await self.redis.get(checkpoint_key)
        last_check_dt = self._parse_datetime(last_check)

        # Запоминаем время начала текущего обхода (без timezone)
        current_check_dt = datetime.now()

        if last_check_dt:
            logger.info(f"🕒 Последняя проверка: {last_check_dt.isoformat()}")
        else:
            logger.info(f"🆕 Первый запуск, чекпоинта нет")

        # Собираем новые файлы и параллельно считаем статистику по группам
        new_tasks = []
        group_counts: dict[str, int] = {}
        common_count = 0

        async for file_dict in self._fetch_all_files():
            file_modified = self._parse_datetime(file_dict.get("modified"))

            # Подсчёт для статистики
            path = file_dict.get("path", "")
            g = self._extract_group_from_path(path)
            if g:
                name = g.value
                group_counts[name] = group_counts.get(name, 0) + 1
            else:
                common_count += 1

            # Пропускаем старые файлы (модифицированные до последней проверки)
            if last_check_dt and file_modified and file_modified <= last_check_dt:
                continue

            # Создаём задачу на уведомление
            task = self._create_notification_task(file_dict)
            new_tasks.append(task)

        # Сохраняем задачи в очередь и обновляем чекпоинт
        if new_tasks:
            await self.notification_service.enqueue_many(new_tasks)
            # Сохраняем время начала обхода как новый чекпоинт
            await self.redis.set(checkpoint_key, current_check_dt.isoformat())
            logger.info(f"✅ Чекпоинт обновлен: {current_check_dt.isoformat()}")
        elif last_check_dt:
            # Даже если файлов нет, обновляем чекпоинт
            await self.redis.set(checkpoint_key, current_check_dt.isoformat())
            logger.debug(f"⏭️ Новых файлов нет, чекпоинт обновлен")

        # Обновляем кэш статистики по группам (5 минут)
        try:
            await self._save_group_counts_cache(group_counts, common_count, ttl=300)
        except Exception as e:
            logger.debug(f"Не удалось обновить кэш статистики групп: {e}")

        return len(new_tasks)

    async def _fetch_all_files(self):
        """Получает все файлы с диска (обходит директории рекурсивно)."""
        # Используем стек для обхода в ширину
        dirs_to_scan = [""]  # Начинаем с корня

        while dirs_to_scan:
            current_path = dirs_to_scan.pop(0)

            # Запрашиваем содержимое директории
            items = await self._fetch_directory(current_path)

            for item in items:
                if item.get("type") == "file":
                    yield item
                elif item.get("type") == "dir":
                    # Добавляем поддиректорию в очередь на обход
                    dirs_to_scan.append(item.get("path"))

    async def _fetch_directory(self, path: str) -> list[dict]:
        """Запрашивает содержимое одной директории (с пагинацией)."""
        all_items = []
        offset = 0
        limit = 200

        while True:
            params = {
                "public_key": self.public_root_url,
                "limit": limit,
                "offset": offset,
            }
            if path:
                params["path"] = path

            try:
                timeout = aiohttp.ClientTimeout(total=self.http_timeout)
                url = "https://cloud-api.yandex.net/v1/disk/public/resources"

                async with self.http.get(url, params=params, timeout=timeout) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    items = data.get("_embedded", {}).get("items", [])

                    if not items:
                        break

                    all_items.extend(items)

                    # Если получили меньше чем limit, значит это последняя страница
                    if len(items) < limit:
                        break

                    offset += limit
                    await asyncio.sleep(0.1)  # Небольшая пауза между запросами

            except Exception as e:
                logger.error(f"Ошибка запроса к Яндекс.Диску (path={path}): {e}")
                break

        return all_items

    def _create_notification_task(self, file_dict: dict) -> NotificationTask:
        """Создаёт задачу на уведомление из данных файла."""
        path = file_dict.get("path", "")
        file_name = file_dict.get("name", "")
        subject_code = self._extract_subject_from_path(path)
        study_group = self._extract_group_from_path(path)
        group_raw = self._extract_group_raw_from_path(path)
        topic = self._extract_topic_from_path(path)

        # Формируем прямую ссылку на просмотр файла на Яндекс.Диске
        public_url = self._build_public_file_url(path)

        # Парсим метаданные из названия файла
        teacher = self._extract_teacher_from_filename(file_name)
        lesson_date = self._extract_date_from_filename(file_name) or self._parse_datetime(file_dict.get("modified"))

        return NotificationTask(
            subject_code=subject_code,
            subject_title=None,
            topic=topic,
            study_group=study_group,
            group_raw=group_raw,
            teacher=teacher,
            lesson_date=lesson_date,
            file_name=file_name,
            file_path=path,
            public_url=public_url,
            download_url=file_dict.get("file"),  # Временная ссылка для скачивания
            md5=file_dict.get("md5"),
            resource_id=file_dict.get("resource_id"),
            modified_iso=file_dict.get("modified"),
        )

    def _build_public_file_url(self, file_path: str) -> str:
        """Формирует прямую ссылку на файл на Яндекс.Диске"""
        import urllib.parse

        # Убираем ведущий слэш
        clean_path = file_path.lstrip("/")

        # Разделяем базовую ссылку и параметры
        base_url = self.public_root_url.split('?')[0].rstrip('/')

        # Формируем полный путь для параметра path
        encoded_path = urllib.parse.quote(clean_path, safe="/")

        # Возвращаем ссылку с параметром path
        return f"{base_url}/{encoded_path}"

    def _extract_subject_from_path(self, path: str) -> Optional[str]:
        """Извлекает код предмета из пути (ищет в сегментах пути)."""
        try:
            from bot.domain.entities.mappings import SUBJECTS

            # Разбиваем путь на сегменты и ищем известный предмет
            segments = [s for s in path.replace("\\", "/").split("/") if s]
            for segment in reversed(segments):
                if segment in SUBJECTS:
                    return segment
        except Exception:
            pass

        return None

    def _extract_topic_from_path(self, path: str) -> Optional[str]:
        """Извлекает тему занятия (Лекция/Семинар) из сегментов пути."""
        try:
            segments = [s.strip() for s in path.replace("\\", "/").split("/") if s]
            for segment in segments:
                if segment in TOPICS:
                    return segment
        except Exception:
            pass
        return None

    def _extract_group_from_path(self, path: str) -> Optional[StudyGroups]:
        """Извлекает код учебной группы из пути, если присутствует соответствующая папка.
        Например: '/1 курс/МА/БКНАД252/...' -> StudyGroups.BKNAD252
        Лекции общие для курса обычно без папки группы: '/1 курс/ЛА/Лекция/...'
        """
        try:
            segments = [s for s in path.replace("\\", "/").split("/") if s]
            values = set(g.value for g in StudyGroups)
            for segment in segments:
                if segment in values:
                    # Вернём enum по значению
                    return StudyGroups(segment)
        except Exception:
            pass
        return None

    def _extract_group_raw_from_path(self, path: str) -> Optional[str]:
        """Находит в пути сегмент, похожий на код группы (даже если неизвестен enum).
        Паттерн: ^БКНАД\d{3}$
        """
        import re

        segments = [s for s in path.replace("\\", "/").split("/") if s]
        pattern = re.compile(r"^БКНАД\d{3}$", re.IGNORECASE)
        for segment in segments:
            if pattern.match(segment):
                return segment
        return None

    def _extract_teacher_from_filename(self, filename: str) -> Optional[str]:
        """Извлекает имя преподавателя из названия файла.
        Формат: 'Фамилия И.О. 2025-10-15T08-08-19Z.mp4'
        """
        import re

        # Паттерн: Фамилия И.О. (кириллица + точки)
        # Примеры: "Лобода А.А.", "Медведь Н.Ю.", "Овчинников С.А."
        pattern = r'^([А-ЯЁа-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.)'
        match = re.match(pattern, filename)

        if match:
            return match.group(1).strip()

        return None

    def _extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Извлекает дату занятия из названия файла.
        Формат: '2025-10-15T08-08-19Z' или '2025-10-15'
        """
        import re

        # Паттерн: ISO-подобная дата в названии
        # Формат: YYYY-MM-DDTHH-MM-SSZ или YYYY-MM-DD
        pattern = r'(\d{4})-(\d{2})-(\d{2})(?:T(\d{2})-(\d{2})-(\d{2})Z?)?'
        match = re.search(pattern, filename)

        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            hour = int(match.group(4)) if match.group(4) else 0
            minute = int(match.group(5)) if match.group(5) else 0
            second = int(match.group(6)) if match.group(6) else 0

            try:
                return datetime(year, month, day, hour, minute, second)
            except ValueError:
                pass

        return None

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Парсит datetime из строки или bytes (без timezone)."""
        if not value:
            return None

        if isinstance(value, (bytes, bytearray)):
            value = value.decode()

        try:
            # Убираем timezone из ISO формата
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            # Возвращаем naive datetime (без timezone)
            return dt.replace(tzinfo=None)
        except Exception:
            return None

    def _get_checkpoint_key(self) -> str:
        """Генерирует ключ Redis для хранения чекпоинта."""
        url_hash = sha256(self.public_root_url.encode()).hexdigest()[:12]
        base = f"checkpoint:{url_hash}"
        return f"{self.key_prefix}:{base}" if getattr(self, 'key_prefix', None) else base

    def _group_counts_cache_key(self) -> str:
        url_hash = sha256(self.public_root_url.encode()).hexdigest()[:12]
        base = f"stats:group_counts:{url_hash}"
        return f"{self.key_prefix}:{base}" if getattr(self, 'key_prefix', None) else base

    async def _save_group_counts_cache(self, groups: dict[str, int], common: int, ttl: int = 300) -> None:
        payload = {
            "groups": groups,
            "common": common,
            "computed_at": datetime.now().isoformat(),
        }
        await self.redis.set(self._group_counts_cache_key(), json.dumps(payload), ex=ttl)
