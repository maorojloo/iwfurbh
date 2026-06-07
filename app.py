import csv
import os
import re
import time
from dataclasses import dataclass
from datetime import date
from io import StringIO
from typing import Optional

import jdatetime
import requests


BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
SHEET_CSV_URL = os.environ["GOOGLE_SHEET_CSV_URL"]

DEFAULT_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "3"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))

TELEGRAM_API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


PERSIAN_DIGITS_MAP = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)

MONTHS = {
    "فروردین": 1,
    "فروردين": 1,
    "اردیبهشت": 2,
    "ارديبهشت": 2,
    "خرداد": 3,
    "تیر": 4,
    "تير": 4,
    "مرداد": 5,
    "شهریور": 6,
    "شهريور": 6,
    "شهزیور": 6,
    "مهر": 7,
    "آبان": 8,
    "ابان": 8,
    "آذر": 9,
    "اذر": 9,
    "دی": 10,
    "دي": 10,
    "بهمن": 11,
    "اسفند": 12,
}


@dataclass(frozen=True)
class Birthday:
    name: str
    raw_date: str
    month: int
    day: int


@dataclass(frozen=True)
class BirthdayStatus:
    birthday: Birthday
    days_remaining: int
    next_gregorian_date: date
    next_jalali_date: jdatetime.date


def normalize_text(value: str) -> str:
    value = value.translate(PERSIAN_DIGITS_MAP)
    value = value.replace("ي", "ی").replace("ك", "ک")
    value = value.replace("\u200c", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_jalali_date(raw_date: str) -> Optional[tuple[int, int]]:
    value = normalize_text(raw_date)

    if not value:
        return None

    unknown_values = {
        "نمیدونم",
        "نمیدانم",
        "نمی دونم",
        "نامشخص",
        "-",
        "_",
    }

    if value in unknown_values:
        return None

    match = re.match(r"^(\d{1,2})\s*([^\d\s]+)$", value)

    if not match:
        return None

    day = int(match.group(1))
    month_name = match.group(2).strip()

    month = MONTHS.get(month_name)

    if not month:
        return None

    if day < 1 or day > 31:
        return None

    if month >= 7 and day > 30:
        return None

    return month, day


def fetch_birthdays() -> list[Birthday]:
    response = requests.get(SHEET_CSV_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    content = response.content.decode("utf-8-sig")
    reader = csv.reader(StringIO(content))

    birthdays: list[Birthday] = []
    seen: set[tuple[str, str]] = set()

    for row in reader:
        if len(row) < 2:
            continue

        name = normalize_text(row[0])
        raw_date = normalize_text(row[1])

        if not name or not raw_date:
            continue

        if name.lower() in {"name", "نام"}:
            continue

        parsed = parse_jalali_date(raw_date)

        if parsed is None:
            continue

        unique_key = (name, raw_date)

        if unique_key in seen:
            continue

        seen.add(unique_key)

        month, day = parsed

        birthdays.append(
            Birthday(
                name=name,
                raw_date=raw_date,
                month=month,
                day=day,
            )
        )

    return birthdays


def calculate_status(birthday: Birthday, today: Optional[date] = None) -> BirthdayStatus:
    today_gregorian = today or date.today()
    today_jalali = jdatetime.date.fromgregorian(date=today_gregorian)

    next_jalali = jdatetime.date(
        year=today_jalali.year,
        month=birthday.month,
        day=birthday.day,
    )

    next_gregorian = next_jalali.togregorian()

    if next_gregorian < today_gregorian:
        next_jalali = jdatetime.date(
            year=today_jalali.year + 1,
            month=birthday.month,
            day=birthday.day,
        )
        next_gregorian = next_jalali.togregorian()

    days_remaining = (next_gregorian - today_gregorian).days

    return BirthdayStatus(
        birthday=birthday,
        days_remaining=days_remaining,
        next_gregorian_date=next_gregorian,
        next_jalali_date=next_jalali,
    )


def get_sorted_statuses() -> list[BirthdayStatus]:
    birthdays = fetch_birthdays()
    statuses = [calculate_status(birthday) for birthday in birthdays]
    return sorted(statuses, key=lambda item: item.days_remaining)


def send_message(chat_id: str | int, text: str) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    response = requests.post(
        f"{TELEGRAM_API_BASE}/sendMessage",
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()


def get_updates(offset: Optional[int]) -> list[dict]:
    params = {
        "timeout": 30,
        "allowed_updates": ["message"],
    }

    if offset is not None:
        params["offset"] = offset

    response = requests.get(
        f"{TELEGRAM_API_BASE}/getUpdates",
        params=params,
        timeout=40,
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        return []

    return data.get("result", [])


def format_status(status: BirthdayStatus) -> str:
    birthday = status.birthday

    if status.days_remaining == 0:
        remaining_text = "امروز 🎂"
    elif status.days_remaining == 1:
        remaining_text = "فردا"
    else:
        remaining_text = f"{status.days_remaining} روز دیگر"

    jalali = status.next_jalali_date

    return (
        f"• <b>{birthday.name}</b>\n"
        f"  تاریخ: {birthday.raw_date}\n"
        f"  مانده: {remaining_text}\n"
        f"  تاریخ بعدی: {jalali.day} {jalali.j_months_fa[jalali.month - 1]} {jalali.year}"
    )


def build_next_birthdays_message(limit: int = 10) -> str:
    statuses = get_sorted_statuses()

    if not statuses:
        return "هیچ تولدی با تاریخ معتبر پیدا نشد."

    lines = ["🎂 <b>نزدیک‌ترین تولدها</b>", ""]

    for status in statuses[:limit]:
        lines.append(format_status(status))
        lines.append("")

    return "\n".join(lines).strip()


def build_today_message() -> str:
    statuses = get_sorted_statuses()
    today_items = [item for item in statuses if item.days_remaining == 0]

    if not today_items:
        return "امروز تولدی ثبت نشده."

    lines = ["🎉 <b>تولدهای امروز</b>", ""]

    for status in today_items:
        lines.append(f"• <b>{status.birthday.name}</b>")

    return "\n".join(lines).strip()


def build_daily_reminder_message() -> str:
    statuses = get_sorted_statuses()

    if not statuses:
        return "هیچ تولدی با تاریخ معتبر پیدا نشد."

    important = [
        item
        for item in statuses
        if item.days_remaining in {0, 1, 3, 7, 14, 30}
    ]

    if not important:
        important = statuses[:5]

    lines = ["🎂 <b>یادآوری تولدها</b>", ""]

    for status in important:
        lines.append(format_status(status))
        lines.append("")

    return "\n".join(lines).strip()


def handle_message(message: dict) -> None:
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = normalize_text(message.get("text", ""))

    if not chat_id or not text:
        return

    if text.startswith("/start"):
        send_message(
            chat_id,
            (
                "بات یادآوری تولد فعال است.\n\n"
                "دستورها:\n"
                "/id گرفتن chat id\n"
                "/next نزدیک‌ترین تولدها\n"
                "/birthdays لیست تولدها\n"
                "/today تولدهای امروز"
            ),
        )
        return

    if text.startswith("/id"):
        send_message(chat_id, f"Chat ID:\n<code>{chat_id}</code>")
        return

    if text.startswith("/today"):
        send_message(chat_id, build_today_message())
        return

    if text.startswith("/next") or text.startswith("/birthdays"):
        send_message(chat_id, build_next_birthdays_message(limit=20))
        return


def run_bot_polling() -> None:
    offset = None

    while True:
        try:
            updates = get_updates(offset)

            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message")

                if message:
                    handle_message(message)

        except Exception as exc:
            print(f"polling_error={exc}", flush=True)
            time.sleep(10)

        time.sleep(POLL_INTERVAL_SECONDS)


def send_daily_reminder_once() -> None:
    if not DEFAULT_CHAT_ID:
        raise RuntimeError("TELEGRAM_CHAT_ID is required for reminder mode")

    message = build_daily_reminder_message()
    send_message(DEFAULT_CHAT_ID, message)


def main() -> None:
    mode = os.getenv("APP_MODE", "bot").strip().lower()

    if mode == "bot":
        run_bot_polling()
        return

    if mode == "reminder":
        send_daily_reminder_once()
        return

    raise ValueError(f"Unsupported APP_MODE: {mode}")


if __name__ == "__main__":
    main()