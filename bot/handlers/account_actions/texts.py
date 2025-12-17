from __future__ import annotations

import dataclasses
import logging
import random
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING, Final

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import delete, select

from bot.db.models import (
    AccountTexts,
    ClarifyingText,
    ClosingText,
    FollowUpText,
    GreetingAnytime,
    GreetingDay,
    GreetingEvening,
    GreetingMorning,
    GreetingNight,
    LeadInText,
)
from bot.keyboards.factories import AccountTextFactory, BackFactory, CancelFactory
from bot.keyboards.inline import (
    ik_account_texts_category_actions,
    ik_account_texts_menu,
    ik_action_with_account,
    ik_cancel_action,
    ik_connect_account,
)
from bot.states import AccountState, AccountTextsState

from .common import account_back_to, account_from_state, alert_notifier

router = Router()
logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class TextFieldConfig:
    label: str
    model: type


TEXT_FIELDS: Final[dict[str, TextFieldConfig]] = {
    "greetings_morning": TextFieldConfig(
        label="Приветствия утром",
        model=GreetingMorning,
    ),
    "greetings_day": TextFieldConfig(
        label="Приветствия днем",
        model=GreetingDay,
    ),
    "greetings_evening": TextFieldConfig(
        label="Приветствия вечером",
        model=GreetingEvening,
    ),
    "greetings_night": TextFieldConfig(
        label="Приветствия ночью",
        model=GreetingNight,
    ),
    "greetings_anytime": TextFieldConfig(
        label="Приветствия в любое время",
        model=GreetingAnytime,
    ),
    "clarifying_texts": TextFieldConfig(
        label="Уточняющие",
        model=ClarifyingText,
    ),
    "follow_up_texts": TextFieldConfig(
        label="Развивающие диалог",
        model=FollowUpText,
    ),
    "lead_in_texts": TextFieldConfig(
        label="Вводные",
        model=LeadInText,
    ),
    "closing_texts": TextFieldConfig(
        label="Закрывающие",
        model=ClosingText,
    ),
}

DEFAULT_TEXTS: Final[dict[str, list[str]]] = {
    "greetings_morning": [
        "доброе утро",
        "утро доброе",
    ],
    "greetings_day": [
        "добрый день",
        "доброго дня",
    ],
    "greetings_evening": [
        "добрый вечер",
        "рада знакомству, добрый вечер",
    ],
    "greetings_night": [
        "доброй ночи",
    ],
    "greetings_anytime": [
        "здравствуйте",
        "приветствую",
        "доброго времени суток",
    ],
    "clarifying_texts": [
        "предложение по кешбэку на {item} ещё актуально?",
        "кешбэк на {item} сейчас действует?",
        "по {item} кешбэк ещё предлагается?",
        "работает ли кешбэк за {item}?",
        "на {item} кешбэк всё ещё в силе?",
        "я ещё могу рассчитывать на кешбэк за {item}?",
        "расскажите, действует ли кешбэк на {item} сейчас?",
        "я присматривалась к {item}, кешбэк доступен?",
        "получится ли оформить кешбэк за {item} сегодня?",
        "интересуюсь {item} кешбэк сохраняется?",
        "я хотела уточнить, кешбэк на {item} ещё работает?",
        "кешбэк на {item} активен или уже закрыли?",
        "успеваю ли я на кешбэк по {item}?",
        "могу ли я оформить кешбэк на {item} прямо сейчас?",
        "уточните, пожалуйста, по {item} кешбэк в силе?",
    ],
    "follow_up_texts": [
        "если да, расскажите, пожалуйста, условия",
        "готова оформить сегодня, если всё ещё в силе",
        "если предложение актуально, напишите детали",
        "готова обсудить условия кешбэка",
        "буду благодарна за короткий ответ",
        "буду рада, если подскажете детали",
        "готова сразу оформить, если условия подходят",
        "мне важно понять условия, расскажите, пожалуйста",
        "если всё ок, сразу сделаю заказ",
        "расскажите коротко, как активировать кешбэк",
        "буду признательна за быстрый ответ",
        "напишите коротко, как активировать кешбэк",
        "если всё актуально, готова оформить сразу",
    ],
    "lead_in_texts": [
        "",
        "подскажите, ",
        "можно уточнить, ",
        "интересует, ",
        "скажите, пожалуйста, ",
        "а скажите, ",
        "хочу уточнить, ",
        "интересно узнать, ",
    ],
    "closing_texts": [
        "",
        "спасибо!",
        "заранее спасибо",
        "жду ваш ответ",
        "буду признательна",
        "буду рада ответу",
    ],
}

TEXTS_FLOW_HINT: Final[str] = (
    "Схема:\n"
    "1) Приветствие\n"
    "2) Вводные + Уточняющие ({item})\n"
    "3) Развивающие диалог\n"
    "4) Закрывающие\n\n"
    "Примечание: приветствие и развивающая часть могут быть отдельными "
    "сообщениями, закрывающие - опционально."
)

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.db.models import UserDB


async def _load_texts(session: AsyncSession, account_id: int) -> AccountTexts | None:
    return await session.scalar(
        select(AccountTexts).where(AccountTexts.account_id == account_id)
    )


async def _ensure_texts(
    session: AsyncSession, account_id: int
) -> tuple[AccountTexts, bool]:
    texts = await _load_texts(session, account_id)
    if texts:
        return texts, False
    texts = AccountTexts(account_id=account_id)
    session.add(texts)
    await session.flush()
    allow_empty_fields = {"lead_in_texts", "closing_texts"}
    default_items = []
    for field, values in DEFAULT_TEXTS.items():
        cfg = TEXT_FIELDS.get(field)
        if not cfg:
            continue
        for value in values:
            text = value.strip()
            if text or field in allow_empty_fields:
                default_items.append(cfg.model(account_texts_id=texts.id, text=text))
    if default_items:
        session.add_all(default_items)
    return texts, True


async def _load_text_models(session: AsyncSession, texts_id: int, model: type) -> list:
    return (
        await session.scalars(
            select(model).where(model.account_texts_id == texts_id).order_by(model.id)
        )
    ).all()


def _format_text_items(items: list[str]) -> str:
    if not items:
        return "Пока пусто."
    rows = [f"{index}. {text}" for index, text in enumerate(items, start=1)]
    text = "\n".join(rows)
    if len(text) > 3500:
        text = text[:3497] + "..."
    return text


def _texts_menu_text(prefix: str | None = None) -> str:
    base = f"Выберите блок текстов.\n\n{TEXTS_FLOW_HINT}"
    if not prefix:
        return base
    return f"{prefix}\n\n{base}"


async def _category_items_text(
    session: AsyncSession,
    texts: AccountTexts | None,
    model: type,
) -> str:
    if not texts:
        return _format_text_items([])
    items = await _load_text_models(session, texts.id, model)
    return _format_text_items([item.text for item in items])


async def _category_actions_text(
    session: AsyncSession, texts: AccountTexts | None, field: str
) -> str:
    cfg = TEXT_FIELDS[field]
    items_text = await _category_items_text(session, texts, cfg.model)
    return f"{cfg.label}\n\nТекущие тексты:\n{items_text}\n\nВыберите действие."


def _parse_indices(raw: str, *, max_index: int) -> list[int]:
    if not raw:
        return []
    tokens = raw.replace(",", " ").split()
    indices: set[int] = set()
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_raw, end_raw = token.split("-", 1)
            if not (start_raw.isdigit() and end_raw.isdigit()):
                continue
            start = int(start_raw)
            end = int(end_raw)
            if start > end:
                start, end = end, start
            for idx in range(start, end + 1):
                if 1 <= idx <= max_index:
                    indices.add(idx)
            continue
        if token.isdigit():
            idx = int(token)
            if 1 <= idx <= max_index:
                indices.add(idx)
    return sorted(indices)


async def _load_text_items(
    session: AsyncSession,
    texts_id: int,
    model: type,
    *,
    keep_empty: bool = False,
) -> list[str]:
    items = (
        await session.scalars(
            select(model.text)
            .where(model.account_texts_id == texts_id)
            .order_by(model.id)
        )
    ).all()
    cleaned = []
    for item in items:
        text = (item or "").strip()
        if text:
            cleaned.append(text)
        elif keep_empty:
            cleaned.append("")
    return cleaned


@router.callback_query(AccountState.actions, F.data == "edit_account_texts")
async def edit_account_texts(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    _, created = await _ensure_texts(session, account.id)
    if created:
        await session.commit()
    await query.message.edit_text(
        text=_texts_menu_text(),
        reply_markup=await ik_account_texts_menu(),
    )
    await state.set_state(AccountTextsState.choose_category)


@router.callback_query(
    AccountTextsState.choose_category, F.data == "test_account_texts"
)
async def test_account_texts(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    _, created = await _ensure_texts(session, account.id)
    if created:
        await session.commit()

    await query.message.edit_text(
        text="Введите название товара для теста",
        reply_markup=await ik_cancel_action(back_to="cancel_test_texts"),
    )
    await state.set_state(AccountTextsState.enter_item_name)


@router.callback_query(
    AccountTextsState.choose_category, BackFactory.filter(F.to == "account_actions")
)
async def texts_back_to_actions(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    markup = (
        await ik_action_with_account(back_to=await account_back_to(state))
        if account.is_connected
        else await ik_connect_account(back_to=await account_back_to(state))
    )
    await query.message.edit_text(text="Действия с аккаунтом", reply_markup=markup)
    await state.set_state(AccountState.actions)


@router.callback_query(AccountTextsState.choose_category, AccountTextFactory.filter())
async def choose_text_category(
    query: CallbackQuery,
    callback_data: AccountTextFactory,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    field = callback_data.field
    cfg = TEXT_FIELDS.get(field)
    if not cfg:
        await query.answer(text="Неизвестная категория", show_alert=True)
        return

    texts = await _load_texts(session, account.id)
    await state.update_data(text_field=field)
    await query.message.edit_text(
        text=await _category_actions_text(session, texts, field),
        reply_markup=await ik_account_texts_category_actions(),
    )
    await state.set_state(AccountTextsState.choose_category)


@router.callback_query(
    AccountTextsState.choose_category,
    BackFactory.filter(F.to == "account_texts_menu"),
)
async def back_to_texts_menu(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    await state.update_data(text_field=None)
    await query.message.edit_text(
        text=_texts_menu_text(),
        reply_markup=await ik_account_texts_menu(),
    )
    await state.set_state(AccountTextsState.choose_category)


@router.callback_query(AccountTextsState.choose_category, F.data == "account_texts_add")
async def start_add_texts(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    data = await state.get_data()
    field = data.get("text_field")
    cfg = TEXT_FIELDS.get(field)
    if not cfg:
        await query.answer(text="Сначала выберите категорию", show_alert=True)
        return

    texts = await _load_texts(session, account.id)
    items_text = await _category_items_text(session, texts, cfg.model)
    await query.message.edit_text(
        text=(
            f"{cfg.label}\n"
            "Отправьте новые тексты, один вариант на строку.\n"
            "Новые строки будут добавлены к существующим.\n\n"
            f"Текущие тексты:\n{items_text}"
        ),
        reply_markup=await ik_cancel_action(back_to="cancel_add_texts"),
    )
    await state.set_state(AccountTextsState.enter_text)


@router.callback_query(
    AccountTextsState.choose_category, F.data == "account_texts_delete"
)
async def start_delete_texts(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    data = await state.get_data()
    field = data.get("text_field")
    cfg = TEXT_FIELDS.get(field)
    if not cfg:
        await query.answer(text="Сначала выберите категорию", show_alert=True)
        return

    texts = await _load_texts(session, account.id)
    if not texts:
        await query.answer(text="Нет текстов для удаления", show_alert=True)
        return

    items = await _load_text_models(session, texts.id, cfg.model)
    if not items:
        await query.answer(text="Нет текстов для удаления", show_alert=True)
        return

    items_text = _format_text_items([item.text for item in items])
    await query.message.edit_text(
        text=(
            f"{cfg.label}\n\n"
            f"Текущие тексты:\n{items_text}\n\n"
            "Введите номера для удаления (например: 1 3 5 или 2-4)."
        ),
        reply_markup=await ik_cancel_action(back_to="cancel_delete_texts"),
    )
    await state.set_state(AccountTextsState.delete_text)


@router.callback_query(
    AccountTextsState.enter_text,
    CancelFactory.filter(F.to == "cancel_add_texts"),
)
async def cancel_add_texts(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    data = await state.get_data()
    field = data.get("text_field")
    cfg = TEXT_FIELDS.get(field)
    if not cfg:
        await query.message.edit_text(
            text=_texts_menu_text(prefix="Добавление отменено"),
            reply_markup=await ik_account_texts_menu(),
        )
        await state.set_state(AccountTextsState.choose_category)
        return

    texts = await _load_texts(session, account.id)
    base_text = await _category_actions_text(session, texts, field)
    await query.message.edit_text(
        text=f"Добавление отменено\n\n{base_text}",
        reply_markup=await ik_account_texts_category_actions(),
    )
    await state.set_state(AccountTextsState.choose_category)


@router.callback_query(
    AccountTextsState.delete_text,
    CancelFactory.filter(F.to == "cancel_delete_texts"),
)
async def cancel_delete_texts(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return

    data = await state.get_data()
    field = data.get("text_field")
    cfg = TEXT_FIELDS.get(field)
    if not cfg:
        await query.message.edit_text(
            text=_texts_menu_text(prefix="Удаление отменено"),
            reply_markup=await ik_account_texts_menu(),
        )
        await state.set_state(AccountTextsState.choose_category)
        return

    texts = await _load_texts(session, account.id)
    base_text = await _category_actions_text(session, texts, field)
    await query.message.edit_text(
        text=f"Удаление отменено\n\n{base_text}",
        reply_markup=await ik_account_texts_category_actions(),
    )
    await state.set_state(AccountTextsState.choose_category)


@router.callback_query(
    AccountTextsState.enter_item_name,
    CancelFactory.filter(F.to == "cancel_test_texts"),
)
async def cancel_test_texts(
    query: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(state, session, alert_notifier(query), user)
    if not account:
        return
    await query.message.edit_text(
        text=_texts_menu_text(),
        reply_markup=await ik_account_texts_menu(),
    )
    await state.set_state(AccountTextsState.choose_category)


@router.message(AccountTextsState.enter_item_name)
async def send_test_texts(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(
        state,
        session,
        partial(message.answer),
        user,
    )
    if not account:
        return

    texts = await _load_texts(session, account.id)
    if not texts:
        await message.answer("Сначала добавьте тексты")
        return

    greetings_morning = await _load_text_items(session, texts.id, GreetingMorning)
    greetings_day = await _load_text_items(session, texts.id, GreetingDay)
    greetings_evening = await _load_text_items(session, texts.id, GreetingEvening)
    greetings_night = await _load_text_items(session, texts.id, GreetingNight)
    greetings_anytime = await _load_text_items(session, texts.id, GreetingAnytime)
    clarifying_texts = await _load_text_items(session, texts.id, ClarifyingText)
    follow_up_texts = await _load_text_items(session, texts.id, FollowUpText)
    lead_in_texts = await _load_text_items(
        session, texts.id, LeadInText, keep_empty=True
    )
    closing_texts = await _load_text_items(
        session, texts.id, ClosingText, keep_empty=True
    )

    missing = []
    if not (
        greetings_morning
        or greetings_day
        or greetings_evening
        or greetings_night
        or greetings_anytime
    ):
        missing.append("Приветствия")
    if not clarifying_texts:
        missing.append("Уточняющие")
    if not follow_up_texts:
        missing.append("Развивающие диалог")
    if missing:
        await message.answer(f"Не хватает текстов для генерации: {', '.join(missing)}")
        await message.answer(
            text=_texts_menu_text(),
            reply_markup=await ik_account_texts_menu(),
        )
        await state.set_state(AccountTextsState.choose_category)
        return

    if not lead_in_texts:
        lead_in_texts = [""]

    async def randomize_text_message(item_name: str) -> str | list[str]:
        item = item_name.strip() or "товар"

        def _pick_greeting() -> str:
            hour = datetime.now().hour
            candidates: list[str] = []
            if 5 <= hour < 12:
                candidates.extend(greetings_morning)
            elif 12 <= hour < 17:
                candidates.extend(greetings_day)
            elif 17 <= hour < 23:
                candidates.extend(greetings_evening)
            else:
                candidates.extend(greetings_night)
            candidates.extend(greetings_anytime)
            return random.choice(candidates) if candidates else ""

        def _with_punctuation(
            text: str, *, mark: str = ".", probability: float = 0.3
        ) -> str:
            if not text:
                return ""
            if text.endswith((".", "!", "?")):
                return text
            return f"{text}{mark}" if random.random() < probability else text

        def _format_greeting(greeting_text: str) -> tuple[str, bool]:
            # Иногда без восклицательного знака, чтобы звучало естественнее.
            punct = random.choices(["", "!", "."], weights=[0.35, 0.45, 0.2])[0]
            text = f"{greeting_text}{punct}".strip()
            has_punct = punct in ("!", ".", "?")
            return text, has_punct

        greeting = _pick_greeting()
        lead_in = random.choice(lead_in_texts)
        if lead_in:
            lead_in = f"{lead_in.rstrip()} "
        question = random.choice(clarifying_texts).format(item=item)

        # Если вопрос уже начинается с "расскажите/подскажите/скажите",
        # убираем вводную часть, чтобы избежать тавтологии.
        question_start = question.lstrip().lower()
        ask_prefixes = (
            "расскажите",
            "подскажите",
            "скажите",
            "интересуюсь",
            "интересует",
            "можно",
            "уточните",
            "хочу уточнить",
            "я хочу",
            "я хотела",
        )
        if question_start.startswith(ask_prefixes):
            lead_in = ""
        follow_up = random.choice(follow_up_texts)
        follow_has_gratitude = any(
            kw in follow_up.lower()
            for kw in ("благодар", "признател", "рада", "спасибо")
        )

        closing_choice = random.choice(closing_texts) if closing_texts else ""
        closing = (
            _with_punctuation(closing_choice.capitalize(), probability=0.3)
            if closing_choice
            else ""
        )

        # Если follow_up уже содержит благодарность, убираем похожее закрытие,
        # чтобы не повторяться.
        if follow_has_gratitude and closing_choice:
            closing_has_gratitude = any(
                kw in closing_choice.lower()
                for kw in ("благодар", "признател", "спасибо", "рада")
            )
            if closing_has_gratitude:
                closing = ""

        base_question = f"{lead_in}{question}"
        base_question = base_question[0].upper() + base_question[1:]
        base_question_inline = base_question

        messages: list[str] = []

        # Случайно решаем, отправлять ли приветствие и разделять ли сообщения.
        split_greeting = random.random() < 0.5
        greeting_formatted, greeting_has_punct = _format_greeting(greeting)
        if not greeting_has_punct and base_question:
            base_question_inline = base_question[0].lower() + base_question[1:]

        if split_greeting:
            messages.append(greeting_formatted)
            messages.append(base_question)
        else:
            messages.append(f"{greeting_formatted} {base_question_inline}".strip())

        use_follow_up = random.random() < 0.75
        if use_follow_up:
            follow_sentence = _with_punctuation(follow_up.capitalize(), probability=0.3)
            if closing:
                follow_sentence = f"{follow_sentence} {closing}".strip()

            split_follow = random.random() < 0.5
            if split_follow:
                messages.append(follow_sentence)
            else:
                messages[-1] = f"{messages[-1]} {follow_sentence}"
        elif closing and random.random() < 0.4:
            # Иногда добавляем только вежливое завершение без уточнений.
            messages[-1] = f"{messages[-1]} {closing}"

        return messages if len(messages) > 1 else messages[0]

    result = await randomize_text_message(message.text or "")
    if isinstance(result, list):
        for part in result:
            await message.answer(part)
    else:
        await message.answer(result)

    await message.answer(
        text=_texts_menu_text(),
        reply_markup=await ik_account_texts_menu(),
    )
    await state.set_state(AccountTextsState.choose_category)


@router.message(AccountTextsState.enter_text)
async def save_texts(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(
        state,
        session,
        partial(message.answer),
        user,
    )
    if not account:
        return

    raw_text = message.text or ""
    lines = [line.strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        await message.answer("Текст не может быть пустым")
        return

    data = await state.get_data()
    field = data.get("text_field")
    cfg = TEXT_FIELDS.get(field)
    if not cfg:
        await message.answer("Неизвестная категория")
        return

    texts, _ = await _ensure_texts(session, account.id)

    session.add_all([cfg.model(account_texts_id=texts.id, text=line) for line in lines])
    await session.commit()

    await message.answer(f"Добавлено: {cfg.label} (+{len(lines)})")
    base_text = await _category_actions_text(session, texts, field)
    await message.answer(
        text=base_text,
        reply_markup=await ik_account_texts_category_actions(),
    )
    await state.set_state(AccountTextsState.choose_category)


@router.message(AccountTextsState.delete_text)
async def delete_texts(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: UserDB,
) -> None:
    account = await account_from_state(
        state,
        session,
        partial(message.answer),
        user,
    )
    if not account:
        return

    data = await state.get_data()
    field = data.get("text_field")
    cfg = TEXT_FIELDS.get(field)
    if not cfg:
        await message.answer("Неизвестная категория")
        await message.answer(
            text=_texts_menu_text(),
            reply_markup=await ik_account_texts_menu(),
        )
        await state.set_state(AccountTextsState.choose_category)
        return

    texts = await _load_texts(session, account.id)
    if not texts:
        await message.answer("Нет текстов для удаления")
        await message.answer(
            text=_texts_menu_text(),
            reply_markup=await ik_account_texts_menu(),
        )
        await state.set_state(AccountTextsState.choose_category)
        return

    items = await _load_text_models(session, texts.id, cfg.model)
    if not items:
        await message.answer("Нет текстов для удаления")
        base_text = await _category_actions_text(session, texts, field)
        await message.answer(
            text=base_text,
            reply_markup=await ik_account_texts_category_actions(),
        )
        await state.set_state(AccountTextsState.choose_category)
        return

    indices = _parse_indices(message.text or "", max_index=len(items))
    if not indices:
        await message.answer("Не удалось распознать номера. Пример: 1 3 5 или 2-4.")
        return

    ids = [items[index - 1].id for index in indices]
    await session.execute(delete(cfg.model).where(cfg.model.id.in_(ids)))
    await session.commit()

    await message.answer(f"Удалено: {cfg.label} ({len(ids)})")
    base_text = await _category_actions_text(session, texts, field)
    await message.answer(
        text=base_text,
        reply_markup=await ik_account_texts_category_actions(),
    )
    await state.set_state(AccountTextsState.choose_category)
