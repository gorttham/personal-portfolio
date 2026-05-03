const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit,
  token: string,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers ?? {}),
    },
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`)
  }
  return res.json() as Promise<T>
}

export async function apiFetchRaw(
  path: string,
  token: string,
  options?: RequestInit,
): Promise<Response> {
  return fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options?.headers ?? {}),
    },
  })
}
