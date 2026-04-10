import sqlite3
import threading

class Database:
    def __init__(self, db_name="chat_history.db"):
        self.db_name = db_name
        # SQLite 멀티스레드 접근 허용 및 락 설정
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.lock = threading.Lock()
        self.init_db()

    def init_db(self):
        """테이블 초기화 및 기본 데이터 세팅"""
        with self.lock:
            cursor = self.conn.cursor()

            # 1. Users 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Users (
                    user_id TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )
            ''')

            # 2. Rooms 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Rooms (
                    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_name TEXT NOT NULL
                )
            ''')

            # 3. Messages 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER,
                    sender_id TEXT,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (room_id) REFERENCES Rooms(room_id),
                    FOREIGN KEY(sender_id) REFERENCES Users(user_id)
                )
            ''')

            # 기본 방 1개 생성
            cursor.execute('''INSERT OR IGNORE INTO Rooms (room_id, room_name) VALUES (1, 'Global Room')''')

            # 기존 하드코딩 유저 마이그레이션 (초기 세팅용)
            users = [('roro', '1234'), ('friend', '1234')]
            cursor.executemany('''INSERT OR IGNORE INTO USERS (user_id, password) VALUES (?, ?)''', users)

            self.conn.commit()

    def authenticate_user(self, user_id, password):
        """유저 인증 확인"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT password FROM Users WHERE user_if = ?", (user_id,))
            result = cursor.fetchone()
            if result and result[0] == password:
                return True
            return False

    def save_message(self, room_id, sender_id, content):
        """메시지 DB 저장"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO Messages (room_id, sender_id, content) VALUES (?, ?, ?)",
                (room_id, sender_id, content)
            )
            self.conn.commit()

    def get_recent_messages(self, room_id, limit=50):
        """최근 메시지 불러오기"""
        with self.lock:
            cursor = self.conn.cursor()
            # 최신 순으로 가져와서 다시 과거 순으로 정렬 (채팅창 흐름)
            cursor.execute('''
                SELECT sender_id, content, datetime(timestamp, 'localtime')
                FROM (
                    SELECT * FROM Messages
                    WHERE room_id = ?
                    ORDER BY timestampt DESC LIMIT ?
                ) ORDER BY timestamp ASC
            ''', (room_id, limit))
            return cursor.fetchall()