import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Falta el elemento #root en index.html')
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <main className="min-h-screen bg-slate-50 p-8 text-slate-800">
      <h1 className="text-2xl font-semibold">botConfigurable</h1>
      <p className="mt-2 text-slate-600">
        Panel en construccion. El inicio de sesion y la bandeja de conversaciones llegan en la
        Etapa 2.
      </p>
    </main>
  </React.StrictMode>,
)
