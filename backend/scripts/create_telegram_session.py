import asyncio
import os

from telethon import TelegramClient
from telethon.sessions import StringSession


async def main() -> None:
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    if not api_id or not api_hash:
        raise SystemExit("Set TELEGRAM_API_ID and TELEGRAM_API_HASH before running this script.")

    phone = input("Telegram phone number, including country code: ").strip()
    client = TelegramClient(StringSession(), int(api_id), api_hash)
    await client.start(phone=phone)
    try:
        print("\nSet this Railway variable as TELEGRAM_SESSION_STRING:\n")
        print(client.session.save())
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
