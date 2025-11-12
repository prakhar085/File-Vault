import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'

function RequireUser({ children }) {
  const userId = localStorage.getItem('userId')
  if (!userId) return <Navigate to="/login" replace />
  return children
}

function RequireGuest({ children }) {
  const userId = localStorage.getItem('userId')
  if (userId) return <Navigate to="/" replace />
  return children
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <RequireGuest>
              <Login />
            </RequireGuest>
          }
        />
        <Route
          path="/"
          element={
            <RequireUser>
              <Dashboard />
            </RequireUser>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)


