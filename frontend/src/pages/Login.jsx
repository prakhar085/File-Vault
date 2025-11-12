import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const [userId, setUserId] = useState('')
  const navigate = useNavigate()

  // Redirect to dashboard if already logged in
  useEffect(() => {
    const storedUserId = localStorage.getItem('userId')
    if (storedUserId) {
      navigate('/', { replace: true })
    }
  }, [navigate])

  function onSubmit(e) {
    e.preventDefault()
    if (!userId.trim()) return
    localStorage.setItem('userId', userId.trim())
    navigate('/', { replace: true })
  }

  return (
    <div style={{ maxWidth: 420, margin: '80px auto', fontFamily: 'sans-serif' }}>
      <h2>Abnormal File Vault</h2>
      <p>Enter a User ID to continue</p>
      <form onSubmit={onSubmit}>
        <input
          type="text"
          placeholder="User ID"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          style={{ width: '100%', padding: 10, marginBottom: 12 }}
        />
        <button type="submit" style={{ padding: '10px 16px' }}>Continue</button>
      </form>
    </div>
  )
}


