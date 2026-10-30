// Tokens de la sesion en sessionStorage: se borran al cerrar la pestana.
// El acceso a sessionStorage puede fallar (modo privado, sitio bloqueado): se tolera.

export interface Tokens {
  accessToken: string
  refreshToken: string
}

const KEY = 'botconfigurable.tokens'

export function loadTokens(): Tokens | null {
  try {
    const raw = sessionStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as Tokens) : null
  } catch {
    return null
  }
}

export function saveTokens(tokens: Tokens): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(tokens))
  } catch {
    // Sin almacenamiento la sesion dura hasta recargar la pagina.
  }
}

export function clearTokens(): void {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    // Nada que limpiar.
  }
}
