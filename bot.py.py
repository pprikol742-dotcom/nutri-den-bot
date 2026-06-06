"""
НутриДень — Telegram Bot + Stars Payment
Бот для Mini App с приёмом оплаты звёздами

Установка:
    pip install aiogram==3.13.0

Запуск:
    python bot.py

Переменные окружения (создай файл .env):
    BOT_TOKEN=ваш_токен_от_BotFather
"""

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery, SuccessfulPayment,
    WebAppInfo, MenuButtonWebApp
)
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

# ── Настройки ──────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_ТОКЕН_СЮДА")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://ТВОЙ_ЛОГИН.github.io/nutri-den-tg/")

# Цена: 250 звёзд ≈ 300 рублей
PRO_STARS = 250
PRO_TITLE = "НутриДень Pro — 1 месяц"
PRO_DESCRIPTION = "Холестерин, витамины, время приёма, ИИ-меню 60 дней, категории блюд, графики"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


# ── /start ─────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🥗 Открыть НутриДень",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ], [
        InlineKeyboardButton(text="⭐ Купить Pro — 250 звёзд", callback_data="buy_pro")
    ]])

    await msg.answer(
        "🌿 <b>НутриДень</b> — умный трекер питания\n\n"
        "Считай калории, КБЖУ и следи за питанием прямо в Telegram.\n\n"
        "Бесплатно:\n"
        "• Счётчик калорий\n"
        "• База 50+ продуктов\n"
        "• История 7 дней\n\n"
        "⭐ <b>Pro (250 звёзд/мес ≈ 300 ₽):</b>\n"
        "• Холестерин и витамины\n"
        "• Время приёма пищи\n"
        "• Категории блюд\n"
        "• 60-дневное ИИ-меню\n"
        "• Графики и сводки",
        reply_markup=kb
    )


# ── /help ──────────────────────────────────────────────────────
@dp.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "🌿 <b>НутриДень — помощь</b>\n\n"
        "/start — запустить бот\n"
        "/pro — купить Pro-подписку\n"
        "/status — проверить статус подписки\n\n"
        "По вопросам: @Meloman_rekords"
    )


# ── /pro — инициировать покупку ────────────────────────────────
@dp.message(Command("pro"))
async def cmd_pro(msg: Message):
    await send_invoice(msg.chat.id)


@dp.callback_query(F.data == "buy_pro")
async def cb_buy_pro(cb: CallbackQuery):
    await cb.answer()
    await send_invoice(cb.message.chat.id)


async def send_invoice(chat_id: int):
    """Отправить инвойс для оплаты звёздами"""
    await bot.send_invoice(
        chat_id=chat_id,
        title=PRO_TITLE,
        description=PRO_DESCRIPTION,
        payload="pro_monthly_subscription",   # внутренний идентификатор
        currency="XTR",                        # XTR = Telegram Stars
        prices=[LabeledPrice(label="Pro на 1 месяц", amount=PRO_STARS)],
        # Для Stars: provider_token НЕ нужен (пустая строка)
        provider_token="",
    )


# ── Pre-checkout — подтверждаем заказ ─────────────────────────
@dp.pre_checkout_query()
async def pre_checkout(pcq: PreCheckoutQuery):
    """Telegram спрашивает — можем ли принять этот заказ?"""
    if pcq.invoice_payload == "pro_monthly_subscription":
        await pcq.answer(ok=True)
    else:
        await pcq.answer(ok=False, error_message="Неизвестный товар")


# ── Успешная оплата ────────────────────────────────────────────
@dp.message(F.successful_payment)
async def payment_done(msg: Message):
    """Пользователь оплатил — активируем Pro"""
    payment: SuccessfulPayment = msg.successful_payment
    user_id = msg.from_user.id
    stars = payment.total_amount

    log.info(f"✅ Оплата: user_id={user_id}, stars={stars}, charge_id={payment.telegram_payment_charge_id}")

    # Здесь сохраняем в БД или отмечаем в файле
    # Пока — просто отвечаем пользователю и отправляем Pro-токен в Mini App
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🥗 Открыть НутриДень Pro",
            web_app=WebAppInfo(url=WEBAPP_URL + f"?pro=1&uid={user_id}")
        )
    ]])

    await msg.answer(
        f"🎉 <b>Pro активирован!</b>\n\n"
        f"Списано: {stars} ⭐\n"
        f"Подписка: 30 дней\n\n"
        f"Все функции разблокированы. Открывай приложение!",
        reply_markup=kb
    )


# ── /status — статус подписки ─────────────────────────────────
@dp.message(Command("status"))
async def cmd_status(msg: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🥗 Открыть НутриДень",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    ]])
    await msg.answer(
        "ℹ️ Проверка статуса в разработке.\n"
        "Если вы оплатили — нажмите кнопку ниже и откройте приложение.\n"
        "При оплате URL содержит ?pro=1 — подписка активируется автоматически.",
        reply_markup=kb
    )


# ── Настройка кнопки меню ─────────────────────────────────────
async def setup_menu_button():
    """Устанавливает кнопку Mini App в меню бота"""
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🥗 НутриДень",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
        log.info("Menu button set successfully")
    except Exception as e:
        log.warning(f"Could not set menu button: {e}")


# ── Запуск ────────────────────────────────────────────────────
async def main():
    log.info("🌿 НутриДень Bot starting...")
    await setup_menu_button()
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
