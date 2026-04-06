import sqlite3
import json
import os
from datetime import datetime

class Database:
    def __init__(self, db_path='bot_database.db'):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 사용자 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    last_notified_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # 사용자 설정 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    chat_id INTEGER,
                    setting_key TEXT,
                    setting_value TEXT,
                    PRIMARY KEY (chat_id, setting_key),
                    FOREIGN KEY (chat_id) REFERENCES users (chat_id)
                )
            ''')
            # 알림 기록 테이블 (중복 방지용)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    pblanc_id TEXT PRIMARY KEY,
                    title TEXT,
                    pub_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def add_user(self, chat_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO users (chat_id) VALUES (?)', (chat_id,))
            conn.commit()

    def set_user_setting(self, chat_id, key, value):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_settings (chat_id, setting_key, setting_value)
                VALUES (?, ?, ?)
            ''', (chat_id, key, value))
            conn.commit()

    def get_user_settings(self, chat_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT setting_key, setting_value FROM user_settings WHERE chat_id = ?', (chat_id,))
            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_all_users(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT chat_id FROM users')
            return [row[0] for row in cursor.fetchall()]

    def is_notified(self, pblanc_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM notifications WHERE pblanc_id = ?', (pblanc_id,))
            return cursor.fetchone() is not None

    def add_notification(self, pblanc_id, title, pub_date):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO notifications (pblanc_id, title, pub_date) VALUES (?, ?, ?)', 
                           (pblanc_id, title, pub_date))
            conn.commit()
