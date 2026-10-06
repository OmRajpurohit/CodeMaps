from app.services.user_service import UserService

def get_router():
    return lambda f: f

get = get_router()

class UserController:
    def __init__(self, service: UserService):
        self.service = service

    @get("/users/{user_id}")
    def get_user_profile(self, user_id: int):
        return self.service.get_user(user_id)
