from datetime import datetime

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import LinkPreviewOptions, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dishka import FromDishka
from dishka.integrations.aiogram import inject
from redis.asyncio import Redis

from bot.application.services.long_poll import YandexDiskPollingService
from bot.application.services.scheduler import NotificationScheduler
from bot.domain.services.user import UserServiceInterface
from bot.domain.entities.mappings import UserType
from bot.domain.entities.user import CreateUserEntity
from bot.domain.services.statistics import StatisticsServiceInterface

router = Router(name="stats")

# Размер страницы для пагинации списков
STATS_PAGE_SIZE = 10


def _parse_dt_raw(value: str | bytes | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (bytes, bytearray)):
        value = value.decode()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _fmt_secs(v: float | int | str) -> str:
    try:
        num = float(v)
        if abs(num - int(num)) < 1e-9:
            return f"{int(num)} с"
        return f"{num:.1f} с"
    except Exception:
        return str(v)


def _fmt_int(n: int) -> str:
    try:
        return f"{int(n):,}".replace(",", " ")
    except Exception:
        return str(n)


def _human_ago(dt: datetime | None) -> str:
    if not dt:
        return "—"
    now = datetime.now()
    delta = now - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return f"{secs} сек назад"
    mins = secs // 60
    if mins < 60:
        return f"{mins} мин назад"
    hours = mins // 60
    if hours < 24:
        return f"{hours} ч назад"
    days = hours // 24
    return f"{days} дн назад"


def _is_admin(u) -> bool:
    return getattr(u, "user_type", None) in (UserType.ADMIN, UserType.SUPERUSER)


def _summary_text(snap) -> str:
    lines: list[str] = []
    lines.append("📊 <b>Статистика пользователей</b>")
    lines.append(f"• Всего: <b>{_fmt_int(snap.users_total)}</b>")
    lines.append(f"• Уведомления включены: <b>{_fmt_int(snap.users_enabled)}</b>")

    if snap.by_course:
        parts = ", ".join(f"{k}: {_fmt_int(v)}" for k, v in sorted(snap.by_course.items()))
        lines.append(f"• По курсам: {parts}")
    if snap.by_group:
        parts = ", ".join(f"{k}: {_fmt_int(v)}" for k, v in sorted(snap.by_group.items()))
        lines.append(f"• По группам: {parts}")

    lines.append("")
    lines.append("🧩 <b>Уведомления</b>")
    lines.append(f"• В очереди задач: <b>{_fmt_int(snap.queue_len)}</b>")
    lines.append(f"• Запланировано к отправке: <b>{_fmt_int(snap.scheduled_total)}</b>")

    lines.append("")
    lines.append("📁 <b>Файлы на диске</b>")
    if getattr(snap, "disk_computed_at", None) is None:
        lines.append("• Обновляется… (подождите до 5 минут)")
    else:
        if getattr(snap, "disk_groups", None):
            parts = ", ".join(f"{k}: {_fmt_int(v)}" for k, v in sorted(snap.disk_groups.items()))
            lines.append(f"• По группам: {parts}")
        lines.append(f"• Общие (без группы): <b>{_fmt_int(getattr(snap, 'disk_common', 0))}</b>")
        lines.append(
            f"• Обновлено: {snap.disk_computed_at.strftime('%d.%m.%Y %H:%M:%S')} ({_human_ago(snap.disk_computed_at)})"
        )

    lines.append("")
    lines.append("🚫 <b>Топ отключённых дисциплин</b>")
    if getattr(snap, "top_excluded", None):
        top_disabled = ", ".join(f"{k}×{v}" for k, v in snap.top_excluded.items())
    else:
        top_disabled = "—"
    lines.append(top_disabled)

    return "\n".join(lines)


def _build_stats_menu_kb() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📚 По курсам", callback_data="stats:courses:page:0"),
        InlineKeyboardButton(text="👥 По группам", callback_data="stats:groups:page:0"),
    )
    kb.row(InlineKeyboardButton(text="🚫 Отключённые", callback_data="stats:disabled"))
    kb.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="stats:refresh"))
    kb.adjust(2)
    return kb.as_markup()


def _build_kv_list_kb(*, items: list[tuple[str, int]], page: int, back_cb: str, page_cb_prefix: str) -> types.InlineKeyboardMarkup:
    page_size = STATS_PAGE_SIZE
    start = page * page_size
    end = start + page_size
    page_items = items[start:end]

    kb = InlineKeyboardBuilder()

    # По 2 в ряд для читаемости
    row: list[InlineKeyboardButton] = []
    for key, val in page_items:
        text = f"{key}: {_fmt_int(val)}"
        row.append(InlineKeyboardButton(text=text, callback_data="stats:nop"))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)

    # Навигация
    has_prev = page > 0
    has_next = end < len(items)
    nav: list[InlineKeyboardButton] = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"{page_cb_prefix}:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"{page_cb_prefix}:{page + 1}"))
    if nav:
        kb.row(*nav)

    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb))
    return kb.as_markup()


@router.message(Command("stats"))
@inject
async def cmd_stats(
    message: types.Message,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(message.from_user))
    if not _is_admin(caller):
        await message.answer("🚫 Доступно только администраторам")
        return

    snap = await stats_service.build_snapshot()
    await message.answer(
        _summary_text(snap),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
        reply_markup=_build_stats_menu_kb(),
    )


@router.callback_query(F.data == "stats:refresh")
@inject
async def cb_stats_refresh(
    callback: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    await callback.answer()
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(callback.from_user))
    if not _is_admin(caller):
        return
    snap = await stats_service.build_snapshot()
    await callback.message.edit_text(
        _summary_text(snap),
        parse_mode="HTML",
        reply_markup=_build_stats_menu_kb(),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.callback_query(F.data == "stats:disabled")
@inject
async def cb_stats_disabled(
    callback: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    await callback.answer()
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(callback.from_user))
    if not _is_admin(caller):
        return
    snap = await stats_service.build_snapshot()
    items = list(snap.top_excluded.items()) if getattr(snap, "top_excluded", None) else []
    kb = _build_kv_list_kb(items=items, page=0, back_cb="stats:refresh", page_cb_prefix="stats:disabled:page")
    await callback.message.edit_text("🚫 Отключённые дисциплины (топ)", reply_markup=kb)


@router.callback_query(F.data.startswith("stats:disabled:page:"))
@inject
async def cb_stats_disabled_page(
    callback: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    await callback.answer()
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(callback.from_user))
    if not _is_admin(caller):
        return
    try:
        page = int(callback.data.rsplit(":", 1)[1])
    except Exception:
        page = 0
    snap = await stats_service.build_snapshot()
    items = list(snap.top_excluded.items()) if getattr(snap, "top_excluded", None) else []
    kb = _build_kv_list_kb(items=items, page=page, back_cb="stats:refresh", page_cb_prefix="stats:disabled:page")
    await callback.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(F.data.startswith("stats:courses:page:"))
@inject
async def cb_stats_courses(
    callback: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    await callback.answer()
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(callback.from_user))
    if not _is_admin(caller):
        return
    try:
        page = int(callback.data.rsplit(":", 1)[1])
    except Exception:
        page = 0
    snap = await stats_service.build_snapshot()
    items = sorted(list(snap.by_course.items()), key=lambda kv: (-(kv[1]), kv[0]))
    kb = _build_kv_list_kb(items=items, page=page, back_cb="stats:refresh", page_cb_prefix="stats:courses:page")
    await callback.message.edit_text("📚 Пользователи по курсам", reply_markup=kb)


@router.callback_query(F.data.startswith("stats:groups:page:"))
@inject
async def cb_stats_groups(
    callback: types.CallbackQuery,
    user_service: FromDishka[UserServiceInterface],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    await callback.answer()
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(callback.from_user))
    if not _is_admin(caller):
        return
    try:
        page = int(callback.data.rsplit(":", 1)[1])
    except Exception:
        page = 0
    snap = await stats_service.build_snapshot()
    items = sorted(list(snap.by_group.items()), key=lambda kv: (-(kv[1]), kv[0]))
    kb = _build_kv_list_kb(items=items, page=page, back_cb="stats:refresh", page_cb_prefix="stats:groups:page")
    await callback.message.edit_text("👥 Пользователи по группам", reply_markup=kb)


@router.callback_query(F.data == "stats:nop")
async def cb_stats_nop(callback: types.CallbackQuery):
    await callback.answer()


@router.message(Command("status"))
@inject
async def cmd_status(
    message: types.Message,
    user_service: FromDishka[UserServiceInterface],
    redis: FromDishka[Redis],
    polling: FromDishka[YandexDiskPollingService],
    scheduler: FromDishka[NotificationScheduler],
    stats_service: FromDishka[StatisticsServiceInterface],
):
    caller = await user_service.get_or_create(CreateUserEntity.from_aiogram(message.from_user))
    if not _is_admin(caller):
        await message.answer("🚫 Доступно только администраторам")
        return

    # Чекпоинт long-poll
    try:
        checkpoint_raw = await redis.get(polling._get_checkpoint_key())  # noqa: SLF001
        checkpoint_dt = _parse_dt_raw(checkpoint_raw)
        checkpoint = checkpoint_dt.strftime("%d.%m.%Y %H:%M:%S") if checkpoint_dt else "—"
        checkpoint_ago = _human_ago(checkpoint_dt)
    except Exception:
        checkpoint = "—"
        checkpoint_ago = "—"

    # Общая информация по long-poll
    poll_url = getattr(polling, "public_root_url", "—")
    poll_interval = _fmt_secs(getattr(polling, "poll_interval", "—"))
    http_timeout = _fmt_secs(getattr(polling, "http_timeout", "—"))
    poll_running = getattr(polling, "_running", False)

    # Планировщик
    sched_interval = _fmt_secs(getattr(scheduler, "check_interval", "—"))
    sched_running = getattr(scheduler, "_running", False)

    # Очереди/план через сервис статистики
    snap = await stats_service.build_snapshot()
    queue_len = snap.queue_len
    scheduled_total = snap.scheduled_total

    lines: list[str] = []
    lines.append("ℹ️ <b>Статус сервиса</b>")

    # Long-poll
    lines.append("🛰️ <b>Long‑poll</b>")
    if poll_url and poll_url != "—":
        lines.append(f"  • URL: <a href=\"{poll_url}\">{poll_url}</a>")
    else:
        lines.append(f"  • URL: {poll_url}")
    lines.append(f"  • Интервал опроса: {poll_interval}")
    lines.append(f"  • HTTP таймаут: {http_timeout}")
    lines.append(f"  • Состояние: {'<b>работает</b>' if poll_running else '<b>остановлен</b>'}")
    lines.append(f"  • Последняя проверка: {checkpoint} ({checkpoint_ago})")

    # Scheduler
    lines.append("⏰ <b>Планировщик уведомлений</b>")
    lines.append(f"  • Период проверки: {sched_interval}")
    lines.append(f"  • Состояние: {'<b>работает</b>' if sched_running else '<b>остановлен</b>'}")

    # Queues
    lines.append("🗃️ <b>Очереди</b>")
    lines.append(f"  • Входящих задач: <b>{_fmt_int(queue_len)}</b>")
    lines.append(f"  • Запланировано к отправке: <b>{_fmt_int(scheduled_total)}</b>")

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
