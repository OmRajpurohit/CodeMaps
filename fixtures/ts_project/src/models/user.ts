export interface User {
  id: string;
  name: string;
  email: string;
}

export class BaseEntity {
  createdAt: Date = new Date();
}
