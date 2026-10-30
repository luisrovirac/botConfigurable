import { useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { clearTokens, loadTokens } from './api/session'
import { InboxPage } from './InboxPage'
import { LoginPage } from './LoginPage'

export function App() {
  const queryClient = useQueryClient()
  const [loggedIn, setLoggedIn] = useState(() => loadTokens() !== null)

  const logout = useCallback(() => {
    clearTokens()
    queryClient.clear()
    setLoggedIn(false)
  }, [queryClient])

  return loggedIn ? (
    <InboxPage onLogout={logout} />
  ) : (
    <LoginPage onLoggedIn={() => setLoggedIn(true)} />
  )
}
