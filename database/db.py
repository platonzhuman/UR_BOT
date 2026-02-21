import aiosqlite
import hashlib
import os
from datetime import datetime

DB_PATH = "jurist_bot.db"

def hash_password(password: str, salt: str = None) -> tuple:
    if salt is None:
        salt = os.urandom(16).hex()
    hash_obj = hashlib.sha256((salt + password).encode())
    return salt, hash_obj.hexdigest()

def verify_password(password: str, salt: str, hash_value: str) -> bool:
    _, new_hash = hash_password(password, salt)
    return new_hash == hash_value

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица users с полем secret_word
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                user_type TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                inn TEXT,
                secret_word TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Таблица документов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                doc_key TEXT NOT NULL,
                doc_name TEXT NOT NULL,
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id) ON DELETE CASCADE
            )
        """)
        # Таблица вопросов
        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                answered_at TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users (telegram_id) ON DELETE CASCADE
            )
        """)
        await db.commit()

async def create_user(telegram_id: int, user_type: str, full_name: str, email: str, password: str, secret_word: str, inn: str = None):
    salt, pwd_hash = hash_password(password)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users (telegram_id, user_type, full_name, email, inn, secret_word, password_salt, password_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (telegram_id, user_type, full_name, email, inn, secret_word, salt, pwd_hash)
        )
        await db.commit()

async def get_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def check_password(telegram_id: int, password: str) -> bool:
    user = await get_user(telegram_id)
    if not user:
        return False
    salt = user['password_salt']
    hash_value = user['password_hash']
    return verify_password(password, salt, hash_value)

async def check_secret_word(telegram_id: int, secret_word: str) -> bool:
    user = await get_user(telegram_id)
    if not user:
        return False
    return user['secret_word'] == secret_word

async def update_password(telegram_id: int, new_password: str):
    salt, pwd_hash = hash_password(new_password)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET password_salt = ?, password_hash = ? WHERE telegram_id = ?",
            (salt, pwd_hash, telegram_id)
        )
        await db.commit()

async def update_last_active(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE telegram_id = ?",
            (telegram_id,)
        )
        await db.commit()

async def add_document(telegram_id: int, doc_key: str, doc_name: str, file_path: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO documents (telegram_id, doc_key, doc_name, file_path) VALUES (?, ?, ?, ?)",
            (telegram_id, doc_key, doc_name, file_path)
        )
        await db.commit()

async def get_user_documents(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, doc_name, created_at FROM documents WHERE telegram_id = ? ORDER BY created_at DESC",
            (telegram_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def add_question(telegram_id: int, question: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO questions (telegram_id, question) VALUES (?, ?)",
            (telegram_id, question)
        )
        await db.commit()

async def delete_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
        await db.commit()