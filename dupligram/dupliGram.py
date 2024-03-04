import asyncio

from dynaconf import settings
from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest

from .database import db_manager


async def get_client():

    client = TelegramClient("tg_session", settings.API_ID, settings.API_HASH)
    await client.connect()
    await client.start()  # type: ignore
    return client


async def get_stl(client: TelegramClient, chat_id, limit):
    dialogs = await client.get_messages(chat_id, limit)
    for dialog in dialogs:
        if hasattr(dialog, "media") and hasattr(dialog.media, "document"):
            message_id = dialog.id
            file_type = dialog.media.document.mime_type
            file_size = dialog.media.document.size
            name = dialog.media.document.attributes[0].file_name
            update_at = dialog.media.document.date
            db_manager.insert_file(
                name, file_type, file_size, update_at, message_id, chat_id
            )
        # TODO: salvar a mensagem no db com suas informações (características "únicas") pra depois encontrar as duplicatas

        # print(name, file_type, file_size, update_at, message_id, chat_id)


async def create_channel(client: TelegramClient):
    channel_id = db_manager.check_chat()
    if not channel_id:
        result = await client(
            CreateChannelRequest(
                title="dupliGram", about="dupliGram", megagroup=True
            )
        )
        # print(result.stringify())  # type: ignore
        channel_id = result.chats[0].id  # type: ignore
        db_manager.inser_chat_id(int("-100" + str(channel_id)))
    return db_manager.check_chat()


async def forward_message(client, from_chat_id, to_chat_id, message_id):
    await client.forward_messages(
        from_peer=from_chat_id,
        entity=to_chat_id,
        messages=message_id,
    )


async def forward_messages(client, to_chat_id, list_tupla):
    for (
        id,
        message_id,
        from_chat_id,
    ) in list_tupla:
        await forward_message(client, from_chat_id, to_chat_id, message_id)


async def main():
    client = await get_client()
    # print(await client.is_user_authorized())
    await get_stl(client, -1002042540697, 100000)

    channel_id = await create_channel(client)
    await forward_messages(client, channel_id, db_manager.find_duplicates())


def run():
    asyncio.run(main())
