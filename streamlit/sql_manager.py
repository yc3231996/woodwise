import sqlite3
from typing import List, Dict
import os

class SQLManager:
    def __init__(self, db_path: str = "volumns/chat_records.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._initialize_database()

    def _initialize_database(self):
        """Initialize the database and create the table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_records (
                    thread_id TEXT PRIMARY KEY,
                    user TEXT NOT NULL,
                    video_path TEXT,
                    video_info TEXT,
                    video_analysis TEXT,
                    created_script TEXT,
                    translated_script TEXT,
                    others TEXT
                )
            """)
            conn.commit()

    def upsert_thread(self, thread: Dict[str, str]) -> str:
        """Insert a new thread or update if it already exists."""
        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO chat_records (
                    thread_id, user, video_path, video_info, video_analysis, 
                    created_script, translated_script, others
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(thread_id) DO UPDATE SET
                    user=excluded.user,
                    video_path=excluded.video_path,
                    video_info=excluded.video_info,
                    video_analysis=excluded.video_analysis,
                    created_script=excluded.created_script,
                    translated_script=excluded.translated_script,
                    others=excluded.others
            """, (
                thread['thread_id'], thread['user'], thread.get('video_path', ''),
                thread.get('video_info', ''), thread.get('video_analysis', ''),
                thread.get('created_script', ''), thread.get('translated_script', ''),
                thread.get('others', '')
            ))
            conn.commit()
            return thread['thread_id']

    def get_threads_by_user(self, user: str) -> List[Dict[str, str]]:
        """Retrieve all records for a specific user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chat_records WHERE user = ?", (user,))
            rows = cursor.fetchall()
            return [
                {
                    "thread_id": row[0],
                    "user": row[1],
                    "video_path": row[2],
                    "video_info": row[3],
                    "video_analysis": row[4],
                    "created_script": row[5],
                    "translated_script": row[6],
                    "others": row[7],
                }
                for row in rows
            ]

    def update_thread(self, thread_id: str, updates: Dict[str, str]) -> bool:
        """Update a record in the database."""
        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            cursor = conn.cursor()
            fields = ", ".join(f"{key} = ?" for key in updates.keys())
            values = list(updates.values())
            values.append(thread_id)
            cursor.execute(f"UPDATE chat_records SET {fields} WHERE thread_id = ?", values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_thread(self, thread_id: str) -> bool:
        """Delete a record from the database."""
        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_records WHERE thread_id = ?", (thread_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_threads_by_user(self, user: str) -> int:
        """Delete all records for a specific user."""
        with sqlite3.connect(self.db_path, timeout=10.0) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_records WHERE user = ?", (user,))
            conn.commit()
            return cursor.rowcount



# 用法示例
if __name__ == "__main__":
    manager = SQLManager()

    # 添加一条记录
    record_id = manager.upsert_thread({
        "thread_id": "12345",
        "user": "john_doe",
        "video_path": "/path/to/video.mp4",
        "video_info": "Video info here",
        "video_analysis": "Analysis results",
        "created_script": "Generated script",
        "translated_script": "Translated script",
        "others": "Additional data"
    })
    print(f"New record ID: {record_id}")

    # 获取某个用户的所有记录
    records = manager.get_threads_by_user("john_doe")
    print(f"Records for user john_doe: {records}")

    # 更新一条记录
    updated = manager.update_thread("12345", {"video_info": "Updated video info"})
    print(f"Record updated: {updated}")

    # 删除一条记录
    deleted = manager.delete_thread("12345")
    print(f"Record deleted: {deleted}")

    # 删除某个用户的所有记录
    deleted_count = manager.delete_threads_by_user("john_doe")
    print(f"Deleted {deleted_count} records for user john_doe")
