from app.db.database import Database

class BadController:
    """Architectural layer violation: Controller directly accesses Database!"""
    def __init__(self, db: Database):
        self.db = db

    def bypass_service_layer(self):
        return self.db.query("SELECT * FROM sensitive_data")
