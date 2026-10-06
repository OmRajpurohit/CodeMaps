from app.repositories.user_repository import UserRepository

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_user(self, user_id: int):
        if user_id <= 0:
            return None
        return self.repo.find_by_id(user_id)

    def create_user(self, username: str, email: str):
        if not username or not email:
            raise ValueError("Invalid user details")
        return self.repo.save({"username": username, "email": email})
