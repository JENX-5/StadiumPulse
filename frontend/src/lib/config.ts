/**
 * Central runtime configuration, sourced from env vars (see `.env.example`).
 * Every module that needs the API/WS base URL should import from here
 * rather than reading `process.env` directly, so there is one place to
 * change defaults or add validation.
 */
const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? (baseUrl ? `${baseUrl}/api/v1` : "http://127.0.0.1:8000/api/v1"),
  wsUrl: process.env.NEXT_PUBLIC_WS_URL ?? (baseUrl ? `${baseUrl.replace('http', 'ws')}/ws` : "ws://127.0.0.1:8000/ws"),
};
