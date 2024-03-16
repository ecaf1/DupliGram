import asyncio
import importlib
import json
import os
import random
import sqlite3
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings(action="ignore")
CLEAR_SCREEN_CMD = "cls" if os.name == "nt" else "clear"
PYTHYON_PATH = sys.executable
CMD_INSTALL_TELETHON = f'"{PYTHYON_PATH}" -m pip install -U telethon'


def clear_screen():
    os.system(CLEAR_SCREEN_CMD)


try:
    telethon = importlib.import_module("telethon")
except ImportError:
    os.system(CMD_INSTALL_TELETHON)
    clear_screen()
    print("Dependencia instalada com sucesso")

from telethon import TelegramClient, functions
from telethon.tl.functions.channels import CreateChannelRequest

SETTINGS_PATH = Path("settings.json")


class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = self.connect()
        self.create_table()

    def connect(self):
        try:
            conn = sqlite3.connect(self.db_path)
            return conn
        except sqlite3.Error as e:
            print(f"Erro ao conectar ao banco de dados SQLite: {e}")
            exit(1)

    def create_table(self):
        query_files = """
        CREATE TABLE IF NOT EXISTS files_stl (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            size INTEGER NOT NULL,
            update_at DATETIME NOT NULL,
            message_id INTEGER NOT NULL UNIQUE,
            chat_id INTEGER NOT NULL
        )
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(query_files)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Erro ao criar a tabela: {e}")

    def insert_file(self, name, file_type, file_size, update_at, message_id, chat_id):
        query = """
        INSERT INTO files_stl (name, type, size, update_at, message_id, chat_id) VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                query,
                (
                    name,
                    file_type,
                    file_size,
                    update_at,
                    message_id,
                    chat_id,
                ),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            if "UNIQUE constraint failed" in str(e):
                pass
            else:
                print(f"Erro ao inserir no banco de dados: {e}")

    def is_duplicate(self, name, size, chat_id, message_id):
        query = """
        SELECT id, message_id, chat_id
        FROM files_stl
        WHERE name = ? AND size = ? AND chat_id = ? AND message_id != ?;
        """
        cursor = self.conn.cursor()
        cursor.execute(query, (name, size, chat_id, message_id))
        result = cursor.fetchone()
        return result

    def get_max_id(self, chat_id):
        query = "SELECT MAX(message_id) FROM files_stl WHERE chat_id = ?"
        cursor = self.conn.cursor()
        cursor.execute(query, (chat_id,))
        result = cursor.fetchone()

        return result[0] if result[0] is not None else 0

    def count_messages(self) -> int:
        query = "select count(*) from files_stl"

        cursor = self.conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        return result[0]

    def close(self):
        self.conn.close()


db_manager = DatabaseManager("dupligram.db")


async def get_client(api_id: int, api_hash: str):

    client = TelegramClient("tg_session", api_id, api_hash)
    await client.connect()
    await client.start()  # type: ignore [start method is awaitable]
    return client


async def get_files(client: TelegramClient, settings: dict):
    chat_id = settings["target_id"]
    print(f"Buscando arquivos no chat {chat_id}")
    total_messages = (await client.get_messages(chat_id)).total

    start_message_id = db_manager.get_max_id(chat_id) + 1
    itered_messages = db_manager.count_messages()
    async for message in client.iter_messages(
        chat_id, reverse=True, min_id=start_message_id
    ):
        itered_messages += 1
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

            db_manager.insert_file(
                name, file_type, file_size, update_at, message_id, chat_id
            )
            if db_manager.is_duplicate(name, file_size, chat_id, message_id):
                await client.forward_messages(
                    entity=settings["output_id"],
                    messages=message_id,
                    from_peer=chat_id,
                )
                await client.delete_messages(chat_id, message_id)
                time.sleep(random.uniform(0.1, 1.5))

            print(
                f"\r\tMensagens salvas: {itered_messages}/{total_messages} | MessageID Atual: {message_id}...",
                end="",
                flush=True,
            )
    print()


async def check_channel(client: TelegramClient, settings: dict):
    if not settings.get("output_id"):
        result = await client(
            CreateChannelRequest(title="dupliGram", about="dupliGram", megagroup=True)
        )
        output_id = getattr(result, "chats")[0].id
        output_id = int("-100" + str(output_id))
        settings.update({"output_id": output_id})
        dump_config(settings)


def dump_config(settings: dict):
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)


async def main(settings: dict):
    client = await get_client(settings["api_id"], settings["api_hash"])

    await check_channel(client, settings)
    await get_files(client, settings)

    client.disconnect()


def change_input_channel(settings):
    target_id = int(input("Insira o ID do canal/grupo que deseja clonar:\n>> "))
    settings.update({"target_id": target_id})
    dump_config(settings)


def change_output_channel(settings):
    output_id = int(input("Insira o ID do canal/grupo que receberá as duplicatas:\n>> "))
    settings.update({"output_id": output_id})
    dump_config(settings)


def change_both_channels(settings):
    target_id = int(input("Insira o ID do canal/grupo que deseja clonar:\n>> "))
    output_id = int(input("Insira o ID do canal/grupo que receberá as duplicatas:\n>> "))
    settings.update({"target_id": target_id, "output_id": output_id})
    dump_config(settings)


def exit_program(_):
    print("Saindo do programa...")
    exit()


def get_app():
    opts = [
        ("Continuar com canais existentes", lambda settings: asyncio.run(main(settings))),
        ("Mudar Canal de Entrada", change_input_channel),
        ("Mudar Canal de Saída", change_output_channel),
        ("Mudar Ambos os Canais", change_both_channels),
        ("Encerrar Programa", exit_program),
    ]

    print("\nMenu de Opções:")
    for i, (opt, _) in enumerate(opts, 1):
        print(f"{i}. {opt}")
    choice = int(input("Escolha uma opção: ")) - 1

    try:
        return opts[choice][1]
    except IndexError:
        return None


def run():
    while True:
        if SETTINGS_PATH.is_file():
            settings = json.load(SETTINGS_PATH.open("r", encoding="utf-8"))
            app = get_app()
            if app:
                app(settings)
            else:
                print("Opção inválida, tente novamente...")
                continue

        else:
            settings = {
                "api_id": int(input("Insira a API_ID: ")),
                "api_hash": input("Insira a API_HASH: "),
                "target_id": int(
                    input("Insira o ID do canal/grupo que deseja clonar:\n>> ")
                ),
                "output_id": int(
                    input(
                        "Insira o ID do canal/grupo que receberá as duplicatas:\n[Enter para criar automaticamente]\n>> "
                    )
                    or 0
                ),
            }

        dump_config(settings)


if __name__ == "__main__":
    clear_screen()
    try:
        run()
    except KeyboardInterrupt:
        print("\nInterrupção detectada, saindo...")
