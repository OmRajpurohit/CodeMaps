# Database access module
class Database:
    def __init__(self, connection_string: str = "sqlite:///:memory:"):
        self.connection_string = connection_string

    def query(self, sql: str):
        return [{"id": 1, "username": "alice"}]

    def execute(self, sql: str):
        return True
