import asyncio
import datetime as dt
import json
import os
import random
import sqlite3
import time
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest

DB_PATH = Path("database.db")
SETTINGS_PATH = Path("settings.json")
CLEAR_SCREEN_CMD = "cls" if os.name == "nt" else "clear"


def clear_screen():
    os.system(CLEAR_SCREEN_CMD)


class DatabaseManager:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.__create_initial_table()

    def __create_initial_table(self):
        query = """
        create table if not exists messages (
            message_id integer,
            chat_id integer,
            name text,
            size integer,
            content_type text
        )
        """

        self.cursor.execute(query)
        self.conn.commit()

    def is_duplicate(self, name: str, size: int, content_type: str, chat_id: int):
        query = """
        select count(*) from messages
        where name like ? and size = ? and content_type = ? and chat_id = ?
        """
        result = self.cursor.execute(query, (name, size, content_type, chat_id)).fetchone()

        return next(iter(result), 0) > 0

    def insert_message(
        self, message_id: int, chat_id: int, name: str, size: int, content_type: str
    ):
        query = """
        insert into messages (message_id, chat_id, name, size, content_type) values (?, ?, ?, ?, ?)
        """
        self.cursor.execute(query, (message_id, chat_id, name, size, content_type))
        self.conn.commit()

    def already_analyzed(self, chat_id: int, message_id: int):
        query = """
        select count(*) from messages
        where message_id = ? and chat_id = ?
        """
        result = self.cursor.execute(query, (message_id, chat_id)).fetchone()
        return next(iter(result), 0) > 0

    def close(self):
        self.conn.close()


class Dupligram:
    def __init__(self):
        self.db = DatabaseManager(DB_PATH)
        self.__get_settings()

    def __dump_settings(self):
        must_be_int = ["api_id", "target_id", "output_id"]
        for key in must_be_int:
            try:
                self.settings[key] = int(self.settings[key])
            except ValueError:
                continue
        with SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=4)

    def __get_settings(self):
        clear_screen()
        print("Carregando o arquivo de configuração...")

        if SETTINGS_PATH.exists():
            self.settings = json.loads(SETTINGS_PATH.read_text())
        else:
            self.settings: dict = {
                "api_id": input("Insira a API_ID: "),
                "api_hash": input("Insira a API_HASH: "),
                "target_id": input("Insira o ID do canal/grupo que deseja clonar:\n>> "),
                "output_id": input(
                    "Insira o ID do canal/grupo que receberá as duplicatas:\n[Enter para criar automaticamente]\n>> "
                ),
            }

            self.__dump_settings()

    async def __init_telegram_client(self):
        api_id = int(self.settings["api_id"])
        api_hash = self.settings["api_hash"]
        self.client = TelegramClient("tg_session", api_id, api_hash)
        await self.client.connect()
        await self.client.start()  # type: ignore [start method is awaitable]

    async def __verify_output_channel(self):
        current_time = f"{dt.datetime.now():%d/%m/%Y %H:%M}"
        if not self.settings.get("output_id"):
            update = await self.client(
                CreateChannelRequest(
                    title=f"Backup DupliGram {current_time}",
                    about="Um grupo de backup para as mensagens consideradas duplicadas pelo Bot do DupliGram.",
                    megagroup=True,
                )
            )
            output_id = getattr(update, "chats")[0].id
            # o chat_id inicia com "-100" pois é um SuperGrupo ou Canal
            self.settings.update({"output_id": f"-100{output_id}"})
            self.__dump_settings()

    def __sleep_randomly(self):
        print()
        sleep_time = random.uniform(1.2, 5.4)
        chunk = 0.1
        while sleep_time > 0:
            print(f"\r\tEsperando {sleep_time:.1f} para continuar...".ljust(60), end="", flush=True)
            time.sleep(chunk)
            sleep_time -= chunk
        print()
        clear_screen()

    async def __analyse_message(self, message):
        message_id = message.id
        already_analyzed = self.db.already_analyzed(self.settings["target_id"], message_id)
        if already_analyzed:
            return
        file_content_type = message.media.document.mime_type
        file_size = message.media.document.size
        first_attr = next(iter(message.media.document.attributes), None)
        file_name = getattr(first_attr, "file_name", str(message_id))
        chat_id = message.chat_id

        # Verifica se tem outro arquivo com mesmo nome, tamanho e tipo
        is_duplicated = self.db.is_duplicate(file_name, file_size, file_content_type, chat_id)

        if is_duplicated:
            await self.client.forward_messages(
                entity=self.settings["output_id"],
                messages=message_id,
                from_peer=self.settings["target_id"],
                background=True,
            )
            await self.client.delete_messages(self.settings["target_id"], message_id)
            self.__sleep_randomly()
        self.db.insert_message(message_id, chat_id, file_name, file_size, file_content_type)

    async def __verify_duplicates(self):
        await self.__init_telegram_client()

        await self.__verify_output_channel()

        total_messages = (await self.client.get_messages(self.settings["target_id"])).total

        count = 0
        async for message in self.client.iter_messages(self.settings["target_id"], reverse=True):
            count += 1
            print(f"\r\tVerificando mensagem {count} de {total_messages}", end="", flush=True)
            media = getattr(message, "media", None)
            if getattr(media, "document", None):
                await self.__analyse_message(message)
        print("")

    async def __exit(self):
        self.client.disconnect()
        self.db.close()
        exit(0)

    async def __edit_settings(
        self,
    ):
        clear_screen()
        self.settings.update(
            {
                "target_id": input(
                    f"Insira novo ID do canal que será clonado (Enter para manter o atual {self.settings['target_id']}):\n>> "
                )
                or self.settings["target_id"],
                "output_id": input(
                    f"Insira novo ID do canal que receberá as duplicatas (Enter para manter o atual {self.settings['output_id']}):\n>> "
                ),
            }
        )
        self.__dump_settings()
        clear_screen()
        print("Configurações salvas!")
        print("Preview:")
        print(json.dumps(self.settings, indent=4, ensure_ascii=False))
        input("Pressione Enter para voltar ao menu...")

    def run(self):
        clear_screen()
        apps = [
            (
                f"Verificar Duplicatas no Canal Especificado ({self.settings['target_id']})",
                self.__verify_duplicates,
            ),
            ("Editar Canal de Entrada e/ou Saida", self.__edit_settings),
            ("Sair", self.__exit),
        ]

        print("Escolha o que fazer:")
        for i, (app_name, _) in enumerate(apps, start=1):
            print(f"[{i}] {app_name}")

        choice = int(input(">> ")) - 1

        callback = apps[choice][1]
        asyncio.run(callback())


if __name__ == "__main__":
    dupligram = Dupligram()
    dupligram.run()
