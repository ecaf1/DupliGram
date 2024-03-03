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
            return None

    def create_table(self):
        if self.conn:
            query = """
            CREATE TABLE IF NOT EXISTS files_stl (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                size INTERGER NOT NULL,
                update_at DATETIME NOT NULL,
                message_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL
            )
            """
            try:
                cursor = self.conn.cursor()
                cursor.execute(query)
                self.conn.commit()
            except sqlite3.Error as e:
                print(f"Erro ao criar a tabela: {e}")

    def insert_db(self, name, file_type, file_size, update_at, message_id, chat_id):
        if self.conn:
            query = """
            INSERT INTO files_stl (name, type, size, update_at, message_id, chat_id) VALUES (?, ?, ?, ?, ?, ?)
            """
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    query, (name, file_type,file_size, update_at, message_id, chat_id)
                )
                self.conn.commit()
            except sqlite3.Error as e:
                print(f"Erro ao inserir no banco de dados: {e}")

    def close(self):
        if self.conn:
            self.conn.close()
