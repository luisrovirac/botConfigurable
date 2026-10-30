import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  fetchConversations,
  fetchMessages,
  UnauthorizedError,
  type ConversationSummary,
  type MessageView,
} from './api/client'

const REFRESH_MS = 3000

const STATUS_LABELS: Record<string, string> = {
  pending: 'Enviando...',
  sent: 'Enviado',
  delivered: 'Entregado',
  read: 'Leido',
  failed: 'No se pudo enviar',
  blocked_window: 'Bloqueado: ventana de 24 h cerrada',
  blocked_consent: 'Bloqueado: el contacto pidio no recibir mensajes',
}

interface Props {
  onLogout: () => void
}

export function InboxPage({ onLogout }: Props) {
  const [selected, setSelected] = useState<string | null>(null)
  const conversations = useQuery({
    queryKey: ['conversations'],
    queryFn: fetchConversations,
    refetchInterval: REFRESH_MS,
  })

  useEffect(() => {
    if (conversations.error instanceof UnauthorizedError) onLogout()
  }, [conversations.error, onLogout])

  return (
    <div className="flex h-screen flex-col bg-slate-100 text-slate-800">
      <header className="flex items-center justify-between bg-emerald-700 px-4 py-3 text-white">
        <h1 className="font-semibold">Conversaciones</h1>
        <button onClick={onLogout} className="text-sm underline">
          Salir
        </button>
      </header>
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <aside className="max-h-64 overflow-y-auto border-b bg-white md:max-h-none md:w-80 md:border-b-0 md:border-r">
          {conversations.isLoading && <p className="p-4 text-sm">Cargando...</p>}
          {conversations.data?.length === 0 && (
            <p className="p-4 text-sm text-slate-500">
              Aun no hay conversaciones. Envia un mensaje con scripts\simulate.bat.
            </p>
          )}
          {conversations.data?.map((c) => (
            <ConversationItem
              key={c.id}
              conversation={c}
              active={c.id === selected}
              onSelect={() => setSelected(c.id)}
            />
          ))}
        </aside>
        <section className="min-h-0 flex-1">
          {selected ? (
            <Thread conversationId={selected} />
          ) : (
            <p className="p-6 text-slate-500">Elige una conversacion.</p>
          )}
        </section>
      </div>
    </div>
  )
}

function ConversationItem({
  conversation,
  active,
  onSelect,
}: {
  conversation: ConversationSummary
  active: boolean
  onSelect: () => void
}) {
  const prefix = conversation.last_message_direction === 'outbound' ? 'Bot: ' : ''
  return (
    <button
      onClick={onSelect}
      className={`block w-full border-b px-4 py-3 text-left hover:bg-slate-50 ${active ? 'bg-emerald-50' : ''}`}
    >
      <p className="font-medium">{conversation.contact_name || conversation.contact_phone}</p>
      <p className="truncate text-sm text-slate-500">
        {prefix}
        {conversation.last_message_body ?? '(sin texto)'}
      </p>
    </button>
  )
}

function Thread({ conversationId }: { conversationId: string }) {
  const messages = useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => fetchMessages(conversationId),
    refetchInterval: REFRESH_MS,
  })
  if (messages.isLoading) return <p className="p-6">Cargando...</p>
  if (messages.error) return <p className="p-6 text-red-600">{messages.error.message}</p>
  return (
    <div className="h-full space-y-2 overflow-y-auto p-4">
      {messages.data?.map((m) => <Bubble key={m.id} message={m} />)}
    </div>
  )
}

function Bubble({ message }: { message: MessageView }) {
  const outbound = message.direction === 'outbound'
  const blocked = message.status?.startsWith('blocked') || message.status === 'failed'
  return (
    <div className={`flex ${outbound ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] whitespace-pre-line rounded-lg px-3 py-2 shadow-sm ${
          outbound ? 'bg-emerald-100' : 'bg-white'
        } ${blocked ? 'border border-red-300 opacity-80' : ''}`}
      >
        <p>{message.body ?? `(${message.type})`}</p>
        <p className={`mt-1 text-right text-xs ${blocked ? 'text-red-600' : 'text-slate-500'}`}>
          {new Date(message.created_at).toLocaleTimeString()}
          {outbound && message.status ? ` · ${STATUS_LABELS[message.status] ?? message.status}` : ''}
        </p>
      </div>
    </div>
  )
}
