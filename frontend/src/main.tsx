import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.tsx'
import './index.css'
import { ActorProvider } from './lib/actor'
import { queryClient } from './lib/queryClient'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ActorProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ActorProvider>
    </QueryClientProvider>
  </StrictMode>,
)
