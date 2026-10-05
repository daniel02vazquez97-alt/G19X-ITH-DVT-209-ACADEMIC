// Holder of the session token, in memory only. Created once per `AuthProvider`; it is never
// persisted, never rendered and disappears with the page.
export interface TokenStore {
  get(): string | null;
  set(token: string | null): void;
}

export function createTokenStore(): TokenStore {
  let token: string | null = null;
  return {
    get: () => token,
    set: (value) => {
      token = value;
    },
  };
}
