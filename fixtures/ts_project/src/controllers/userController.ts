import { UserService } from '../services/userService';

export class UserController {
  private service: UserService;

  constructor(service: UserService) {
    this.service = service;
  }

  public handleRequest(userId: string) {
    return this.service.getUser(userId);
  }
}
