import React, { useState } from 'react'
import { Toast } from './Toast.jsx'

export default function FileUpload({ onUploaded, rateLimited = false, onRateLimit }) {
  const [file, setFile] = useState(null)
  const [message, setMessage] = useState('')
  const [toast, setToast] = useState(null)

  async function onSubmit(e) {
    e.preventDefault()
    if (rateLimited) return // Don't allow upload when rate limited
    setMessage('')
    if (!file) return
    const userId = localStorage.getItem('userId')
    if (!userId) {
      window.location.href = '/login'
      return
    }
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/files/', { method: 'POST', body: form, headers: { 'UserId': userId } })
      if (res.status === 429) {
        const body = await res.json().catch(() => ({}))
        if ((body.detail || '').includes('Quota')) {
          setToast({ message: 'Storage Quota Exceeded', type: 'error' })
        } else {
          setToast({ message: 'Rate Limit Hit — Try Again', type: 'error' })
          onRateLimit && onRateLimit()
        }
        return
      }
      if (!res.ok) throw new Error('Upload failed')
      const data = await res.json()
      if (data.is_reference) {
        setMessage('Uploaded as reference (duplicate detected)')
      } else {
        setMessage('Uploaded successfully')
      }
      setFile(null)
      // Reset file input
      const fileInput = document.querySelector('input[type="file"]')
      if (fileInput) fileInput.value = ''
      // Call onUploaded callback after a short delay to avoid rate limit
      setTimeout(() => {
        onUploaded && onUploaded()
      }, 100)
    } catch (e) {
      setMessage(e.message || 'Upload failed')
    }
  }

  return (
    <>
      <form onSubmit={onSubmit}>
        <input 
          type="file" 
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          disabled={rateLimited}
        />
        <button 
          type="submit" 
          style={{ marginLeft: 8, opacity: rateLimited ? 0.6 : 1, cursor: rateLimited ? 'not-allowed' : 'pointer' }}
          disabled={rateLimited}
        >
          Upload
        </button>
        {message && <div style={{ marginTop: 8, color: message.includes('successfully') ? 'green' : 'inherit' }}>{message}</div>}
      </form>
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </>
  )
}


