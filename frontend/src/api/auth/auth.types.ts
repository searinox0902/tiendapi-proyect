export interface ILoginCredentials {
  email: string;
  password: string;
}

export interface ILoginResponse {
  access_token: string;
  token_type: string;
  user?: IAuthUser;
}

export interface IAuthUser {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: "owner" | "member";
  is_active: boolean;
  created_at: string;
}
