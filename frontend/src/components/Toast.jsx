import React, { useEffect } from 'react'

export function Toast({ message, type = 'error', onClose, duration = 3000 }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose && onClose()
    }, duration)
    return () => clearTimeout(timer)
  }, [duration, onClose])

  if (!message) return null

  const bgColor = type === 'error' ? '#ff4444' : type === 'success' ? '#44ff44' : '#ffaa00'
  const textColor = '#fff'

  return (
    <div
      style={{
        position: 'fixed',
        top: 20,
        right: 20,
        padding: '12px 16px',
        backgroundColor: bgColor,
        color: textColor,
        borderRadius: 4,
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
        zIndex: 10000,
        minWidth: 200,
        maxWidth: 400,
      }}
    >
      {message}
    </div>
  )
}

