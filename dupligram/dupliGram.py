import asyncio
import json
import random
import sys
import time
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.types import Message

from .database import db_manager

SETTINGS_PATH = Path("settings.json")


async def get_client(api_id: int, api_hash: str):

    client = TelegramClient("tg_session", api_id, api_hash)
    await client.connect()
    await client.start()  # type: ignore [start method is awaitable]
    return client


async def get_files(client: TelegramClient, settings: dict):
    chat_id = settings["target_id"]
    async for message in client.iter_messages(
        chat_id, reverse=True, min_id=settings["start_message_id"]
    ):
        if hasattr(message, "media") and hasattr(message.media, "document"):
            message_id = message.id
            file_type = message.media.document.mime_type
            file_size = message.media.document.size
            first_atribute = (
                message.media.document.attributes[0]
                if message.media.document.attributes
                else None
            )
            name = getattr(first_atribute, "file_name", str(message_id))
            update_at = message.media.document.date
            if not db_manager.is_duplicate(name, file_size):
                db_manager.insert_file(
                    name, file_type, file_size, update_at, message_id, chat_id
                )
            else:
                await forward_message(
                    client,settings["output_id"], message_id,  chat_id
                )
                time.sleep(random.uniform(0.1, 1.5))

            sys.stdout.write("\r Salvando mensagens ...")
            settings.update({"start_message_id": message_id})
            dump_config(settings)
    sys.stdout.flush()
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
        channel_id = getattr(result, "chats")[0].id

        db_manager.inser_chat_id(int("-100" + str(channel_id)))
    return db_manager.check_chat()


async def forward_message(
    client: TelegramClient,
    to_chat_id: int,
    # entry_id: int,
    message_id: int,
    from_chat_id: int,
) -> None:
    sent_message = await client.forward_messages(
        entity=to_chat_id,
        messages=message_id,
        from_peer=from_chat_id,
    )

    if not isinstance(sent_message, Message):
        sent_message = sent_message[0]

    normalized_chat_id = str(to_chat_id).removeprefix("-100")
    await client.send_message(
        entity=to_chat_id,
        message=f"link para a mensagem: https://t.me/c/{normalized_chat_id}/{message_id}",
        reply_to=sent_message.id,
    )

    # db_manager.update_flag(entry_id)


async def forward_messages(client, output_id, duplicates: list[tuple]):
    for tupla in duplicates:
        await forward_message(client, output_id, *tupla)


def dump_config(settings: dict):
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)


async def main(settings: dict):
    client = await get_client(settings["api_id"], settings["api_hash"])

    if not settings.get("output_id"):
        output_id = await create_channel(client)
        settings.update({"output_id": output_id})
        dump_config(settings)

    await get_files(client, settings)

    # await forward_messages(
    #     client, settings["output_id"], db_manager.find_duplicates()
    # )


def run():
    if SETTINGS_PATH.is_file():
        settings = json.load(SETTINGS_PATH.open("r", encoding="utf-8"))
    else:
        settings = {
            "api_id": int(input("Insira a API_ID: ")),
            "api_hash": input("Insira a API_HASH: "),
            "target_id": input(
                "Insira o ID do canal/grupo que deseja clonar:\n>> "
            ),
            "output_id": input(
                "Insira o ID do canal/grupo que receberá as duplicatas:\n[Enter para criar automaticamente]\n>> "
            ),
            "start_message_id": 0,
        }

    dump_config(settings)
    asyncio.run(main(settings))
