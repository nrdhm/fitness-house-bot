import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .fh_scrape import scrape_fh_schedule

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

activities = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global activities
    activities = scrape_fh_schedule()
    dates = sorted(
        set(x["date"] for x in activities),
        key=lambda x: tuple(reversed(x.split(",")[0].split("."))),
    )
    keyboard = [[InlineKeyboardButton(date, callback_data=date)] for date in dates]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери дату:", reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    chosen = [x for x in activities if x["date"] == query.data]
    assert chosen
    header = f"Расписание на {query.data}"
    body = [f'{x["time"]}: {x["name"]}' for x in chosen]
    await query.edit_message_text(text="\n".join([header, *body]))


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=update.message.text
    )


async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = " ".join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Sorry, I didn't understand that command.",
    )
