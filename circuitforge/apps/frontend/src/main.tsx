import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#1f2937',
            color: '#e2e8f0',
            border: '1px solid #374151',
          },
          success: { iconTheme: { primary: '#22d3ee', secondary: '#0a0f1e' } },
          error: { iconTheme: { primary: '#f87171', secondary: '#0a0f1e' } },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
)
