import { User, BaseEntity } from '../models/user';

export interface IUserService {
  getUser(id: string): User | null;
}

export class UserService extends BaseEntity implements IUserService {
  getUser(id: string): User | null {
    if (!id) {
      return null;
    }
    return { id, name: "Sample User", email: "user@example.com" };
  }
}
