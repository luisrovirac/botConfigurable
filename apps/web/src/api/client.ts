import { clearTokens, loadTokens, saveTokens, type Tokens } from './session'

const BASE = '/api/v1'

export interface ConversationSummary {
  id: string
  contact_phone: string | null
  contact_name: string | null
  status: string
  last_message_body: string | null
  last_message_direction: 'inbound' | 'outbound' | null
  last_message_at: string | null
}

export interface MessageView {
  id: string
  direction: 'inbound' | 'outbound'
  type: string
  body: string | null
  status: string | null
  created_at: string
}

export class UnauthorizedError extends Error {}

interface TokenResponse {
  access_token: string
  refresh_token: string
}

function toTokens(response: TokenResponse): Tokens {
  return { accessToken: response.access_token, refreshToken: response.refresh_token }
}

export async function login(email: string, password: string): Promise<Tokens> {
  const response = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (response.status === 401) throw new UnauthorizedError('Email o contrasena incorrectos')
  if (!response.ok) throw new Error(`No se pudo iniciar sesion (HTTP ${response.status})`)
  const tokens = toTokens((await response.json()) as TokenResponse)
  saveTokens(tokens)
  return tokens
}

async function refresh(tokens: Tokens): Promise<Tokens | null> {
  const response = await fetch(`${BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: tokens.refreshToken }),
  })
  if (!response.ok) return null
  const renewed = toTokens((await response.json()) as TokenResponse)
  saveTokens(renewed)
  return renewed
}

// GET autenticado. Si el token de acceso vencio, lo renueva una vez y reintenta.
async function get<T>(path: string): Promise<T> {
  let tokens = loadTokens()
  if (!tokens) throw new UnauthorizedError('Sesion no iniciada')
  let response = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${tokens.accessToken}` },
  })
  if (response.status === 401) {
    tokens = await refresh(tokens)
    if (!tokens) {
      clearTokens()
      throw new UnauthorizedError('La sesion expiro')
    }
    response = await fetch(`${BASE}${path}`, {
      headers: { Authorization: `Bearer ${tokens.accessToken}` },
    })
  }
  if (!response.ok) throw new Error(`Error del servidor (HTTP ${response.status})`)
  return (await response.json()) as T
}

export const fetchConversations = () => get<ConversationSummary[]>('/conversations')

export const fetchMessages = (conversationId: string) =>
  get<MessageView[]>(`/conversations/${conversationId}/messages`)
