from app.db.database import Database

class BaseRepository:
    def count(self):
        return 1

class UserRepository(BaseRepository):
    def __init__(self, db: Database):
        self.db = db

    def find_by_id(self, user_id: int):
        return self.db.query("SELECT * FROM users WHERE id = %s")

    def save(self, user_data: dict):
        return self.db.execute("INSERT INTO users VALUES (...)")
