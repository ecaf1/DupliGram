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

    def is_duplicate(self, name, size):
        query = """
        SELECT id, message_id, chat_id
        FROM files_stl
        WHERE name = ? AND size = ? ;
        """
        cursor = self.conn.cursor()
        cursor.execute(query, (name, size))
        result = cursor.fetchone()
        return False if result is None else True

    def close(self):
        self.conn.close()


db_manager = DatabaseManager("dupligram.db")
