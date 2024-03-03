import asyncio
from datetime import datetime

from dynaconf import settings
from telethon import TelegramClient

from .database import DatabaseManager


async def get_client():

    client = TelegramClient("tg_session", settings.API_ID, settings.API_HASH)
    await client.connect()
    await client.start()  # type: ignore
    return client


async def get_stl(client: TelegramClient, chat_id, limit):
    db_manager = DatabaseManager("dupligram.db")
    dialogs = await client.get_messages(chat_id, limit)
    for dialog in dialogs:
        if getattr(dialog, "media", None):
            message_id = dialog.id
            file_type = dialog.media.document.mime_type
            file_size = dialog.media.document.size
            name = dialog.media.document.attributes[0].file_name
            update_at = dialog.media.document.date
            db_manager.insert_db(
                name, file_type, file_size, update_at, message_id, chat_id
            )
        # TODO: salvar a mensagem no db com suas informações (características "únicas") pra depois encontrar as duplicatas

        # print(name, file_type, file_size, update_at, message_id, chat_id)


async def main():
    client = await get_client()
    print(await client.is_user_authorized())
    await get_stl(client, -1001393256003, 3)
    messages = await client.get_messages(
        -1001393256003,
        limit=3,
    )


def run():
    asyncio.run(main())
