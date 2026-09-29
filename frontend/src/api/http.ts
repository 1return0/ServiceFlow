export class ApiRequestError extends Error {
  constructor(
    readonly status: number,
    readonly detail: unknown,
  ) {
    super(`API request failed with HTTP ${status}`);
  }
}

type AccessTokenProvider = () => string | null;

export interface ApiClient {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: unknown, headers?: Record<string, string>): Promise<T>;
  patch<T>(path: string, body?: unknown): Promise<T>;
}

export function createApiClient(
  baseUrl: string,
  getAccessToken: AccessTokenProvider = () => null,
): ApiClient {
  async function request<T>(method: string, path: string, body?: unknown, extraHeaders: Record<string, string> = {}): Promise<T> {
    const token = getAccessToken();
    const response = await fetch(`${baseUrl}${path}`, {
      method,
      headers: {
        Accept: "application/json",
        ...extraHeaders,
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });

    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      throw new ApiRequestError(response.status, payload);
    }
    return payload as T;
  }

  return {
    get: (path) => request("GET", path),
    post: (path, body, headers) => request("POST", path, body, headers),
    patch: (path, body) => request("PATCH", path, body),
  };
}
