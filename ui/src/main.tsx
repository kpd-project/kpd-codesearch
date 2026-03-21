import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import SettingsPage from './pages/settings/settings-page.tsx'
import { StatusProvider } from '@/hooks/use-api'
import { ServicesWaitingGate } from '@/components/services-waiting-overlay'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <StatusProvider>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
        <ServicesWaitingGate />
      </StatusProvider>
    </BrowserRouter>
  </StrictMode>,
)
