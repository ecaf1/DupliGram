import asyncio
from tkinter import dialog

from dynaconf import settings
from telethon import TelegramClient


async def get_client():

    client = TelegramClient("tg_session", settings.API_ID, settings.API_HASH)
    await client.connect()
    await client.start()  # type: ignore
    return client



async def main():
    client = await get_client()
    print(await client.is_user_authorized())

    dialogs = await client.get_dialogs()

    for dialog in dialogs:
        print(dialog.id)


asyncio.run(main())
