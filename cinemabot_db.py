import sqlite3
import re
import os
from aiogram import html

DB_FOLDER = os.path.dirname(__file__)
DB_PATH = os.path.join(DB_FOLDER, 'bot_database.sqlite3')


def normalize_query(query: str) -> str:
    """Преобразуем все в нижний регистр и удаляем все спецсимволы"""
    query = query.lower()
    query = re.sub(r'[^a-zа-я0-9\s]', '', query)
    return query.strip()


def create_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = '''
    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        query TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    '''
    cursor.execute(query)

    query = '''
    CREATE TABLE IF NOT EXISTS statistics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        query TEXT NOT NULL
    )
    '''
    cursor.execute(query)

    conn.commit()
    conn.close()


def add_search_history(user_id, query):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    normalized_query = normalize_query(query)

    query = '''
    INSERT INTO search_history (user_id, query)
    VALUES (?, ?)
    '''
    cursor.execute(query, (user_id, normalized_query))

    conn.commit()
    conn.close()


def add_to_statistics(user_id, query):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    normalized_query = normalize_query(query)

    query = '''
    INSERT INTO statistics (user_id, query)
    VALUES (?, ?)
    '''
    cursor.execute(query, (user_id, normalized_query))

    conn.commit()
    conn.close()


def get_statistics(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = '''
    SELECT query, COUNT(*)
    FROM statistics
    WHERE user_id = ?
    GROUP BY query
    '''
    cursor.execute(query, (user_id,))
    result = cursor.fetchall()

    conn.close()

    if result:
        stats_message = f"{html.bold('Your statistics:')}\n\n"
        for query_text, count in result:
            stats_message += f"{query_text}: {count}\n"
    else:
        stats_message = "There are no statistics yet.."

    return stats_message


def get_history(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = '''
    SELECT query, timestamp
    FROM search_history
    WHERE user_id = ?
    ORDER BY timestamp DESC
    '''
    cursor.execute(query, (user_id,))
    result = cursor.fetchall()

    conn.close()

    if result:
        history_message = f"{html.bold('Your search history:')}\n\n"
        for query_text, timestamp in result:
            history_message += f"{timestamp} - {query_text}\n"
    else:
        history_message = "There is no history yet.."
    return history_message
