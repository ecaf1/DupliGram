import sqlite3


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
            size INTERGER NOT NULL,
            update_at DATETIME NOT NULL,
            message_id INTEGER NOT NULL UNIQUE,
            chat_id INTEGER NOT NULL,
            send_flag INTEGER DEFAULT 0
        )
        """
        query_channel = """
        CREATE TABLE IF NOT EXISTS chat_id (
            id INTEGER PRIMARY KEY
        )
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(query_files)
            cursor.execute(query_channel)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Erro ao criar a tabela: {e}")

    def insert_file(
        self, name, file_type, file_size, update_at, message_id, chat_id
    ):
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

    def inser_chat_id(self, chat_id):
        query = """
        INSERT INTO chat_id (id) VALUES (?)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, (chat_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            if "UNIQUE constraint failed" in str(e):
                pass
            else:
                print(f"Erro ao inserir no banco de dados: {e}")

    def check_chat(self):
        query = """
        SELECT id FROM chat_id  
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return None
        except sqlite3.Error as e:
            print(f"Erro ao inserir no banco de dados: {e}")

    def find_duplicates(self):
        # "select id, message_id, chat_id from files_stl where id not in (select min(id) from files_stl group by name, size)"
        # AND (name, size) IN (
        #     SELECT name, size
        #     FROM files_stl
        #     GROUP BY name, size
        #     HAVING COUNT(*) > 1
        #     )
        query = """
        SELECT id, message_id, chat_id
        FROM files_stl
        WHERE id NOT IN (
        SELECT MIN(id)
        FROM files_stl
        GROUP BY name, size
        )
        AND send_flag = 0;
        """
        cursor = self.conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        return result

    def update_flag(self, entry_id: int):
        query = "UPDATE files_stl SET send_flag = 1 WHERE id = ?"
        cursor = self.conn.cursor()

        cursor.execute(query, (entry_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()


db_manager = DatabaseManager("dupligram.db")
