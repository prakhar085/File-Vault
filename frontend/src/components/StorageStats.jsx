import React, { useEffect, useState } from 'react'

function fmtBytes(bytes) {
  if (!bytes && bytes !== 0) return '0 B'
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export default function StorageStats({ refreshKey = 0, userId }) {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const currentUserId = userId || localStorage.getItem('userId')
    if (!currentUserId) return
    
    // Debounce stats fetch to avoid rate limiting
    const timer = setTimeout(() => {
      setLoading(true)
      fetch('/api/files/storage_stats/', { headers: { 'UserId': currentUserId } })
        .then(async (r) => {
          if (!r.ok) {
            if (r.status === 429) throw new Error('Rate Limit Hit — Try Again')
            throw new Error(`Failed to fetch stats: ${r.status}`)
          }
          const d = await r.json()
          setStats(d)
          setError(null)
          setLoading(false)
        })
        .catch((e) => {
          // Only show error for rate limit, not for other errors (they'll retry silently)
          if (e.message.includes('Rate Limit')) {
            setError(e.message)
          } else {
            setError(null) // Don't show error, just retry
          }
          setStats(null)
          setLoading(false)
          // Retry after 2 seconds on error
          setTimeout(() => {
            const retryUserId = userId || localStorage.getItem('userId')
            if (retryUserId) {
              fetch('/api/files/storage_stats/', { headers: { 'UserId': retryUserId } })
                .then(async (r) => {
                  if (r.ok) {
                    const d = await r.json()
                    setStats(d)
                    setError(null)
                  }
                })
                .catch(() => {})
            }
          }, 2000)
        })
    }, 300) // 300ms debounce
    
    return () => clearTimeout(timer)
  }, [refreshKey, userId])

  if (loading && !stats) return <div>Loading...</div>
  if (error && !stats) return <div style={{ color: 'red' }}>{error}</div>
  if (!stats) return <div>No stats available</div>

  return (
    <div>
      <div>Total storage used: <strong>{fmtBytes(stats.total_storage_used)}</strong></div>
      <div>Original storage used: <strong>{fmtBytes(stats.original_storage_used)}</strong></div>
      <div>Savings: <strong>{fmtBytes(stats.storage_savings)} ({stats.savings_percentage}%)</strong></div>
    </div>
  )
}


