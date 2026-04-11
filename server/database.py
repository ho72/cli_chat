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
            cursor.execute("PRAGMA foreign_keys = ON")

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

            # 3. Room_Members 테이블 - User <-> Room 다대다
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Room_Members (
                    room_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (room_id, user_id),
                    FOREIGN KEY (room_id) REFERENCES Rooms(room_id),
                    FOREIGN KEY (user_id) REFERENCES Users(user_id)
                )
            ''')

            # 4. Messages 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER,
                    sender_id TEXT,
                    ip_address TEXT,
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

    # ---------------
    # 로그인 검증
    # ---------------

    def authenticate_user(self, user_id, password):
        """유저 인증 확인"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT password FROM Users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            if result and result[0] == password:
                return True
            return False

    # ---------------
    # 방 관리
    # ---------------

    def join_room(self, room_id, user_id):
        """유저를 채팅방에 참가시킴 (중복 무시)"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO Room_Members (room_id, user_id) VALUES (?, ?)",
                (room_id, user_id)
            )
            self.conn.commit()

    def leave_room(self, room_id, user_id):
        """유저를 채팅방에서 제거"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "DELETE FROM Room_Members WHERE room_id = ? AND user_id = ?",
                (room_id, user_id)
            )
            self.conn.commit()

    def get_room_members(self, room_id):
        """해당 방의 참가자 목록 반환"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT user_id, joined_at FROM Room_Members WHERE room_id = ? ORDER BY joined_at",
                (room_id,)
            )
            return cursor.fetchall()

    def get_user_rooms(self, user_id):
        """유저가 참가 중인 방 목록 반환"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT r.room_id, r.room_name, rm.joined_at
                FROM Room_Members rm
                JOIN Rooms r ON rm.room_id = r.room_id
                WHERE rm.user_id = ?
            ''', (user_id,))
            return cursor.fetchall()

    # ---------------
    # 채팅 관련
    # ---------------

    def save_message(self, room_id, sender_id, ip_address, content):
        """메시지 DB 저장"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO Messages (room_id, sender_id, ip_address, content) VALUES (?, ?, ?, ?)",
                (room_id, sender_id, ip_address, content)
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
                    ORDER BY timestamp DESC LIMIT ?
                ) ORDER BY timestamp ASC
            ''', (room_id, limit))
            return cursor.fetchall()