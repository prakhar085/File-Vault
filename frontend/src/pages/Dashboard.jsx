import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import FileUpload from '../components/FileUpload.jsx'
import FileList from '../components/FileList.jsx'
import Filters from '../components/Filters.jsx'
import StorageStats from '../components/StorageStats.jsx'
import { Toast } from '../components/Toast.jsx'

export default function Dashboard() {
  const navigate = useNavigate()
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [toast, setToast] = useState(null)
  const [rateLimited, setRateLimited] = useState(false)

  const userId = localStorage.getItem('userId')

  // Re-enable interactions after rate limit cooldown (1.5 seconds)
  useEffect(() => {
    if (rateLimited) {
      const timer = setTimeout(() => {
        setRateLimited(false)
      }, 1500) // 1.5 seconds cooldown
      return () => clearTimeout(timer)
    }
  }, [rateLimited])

  const buildQuery = (params) => {
    const url = new URL('/api/files/', window.location.origin)
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && String(v).length > 0) url.searchParams.set(k, v)
    })
    return url.toString().replace(window.location.origin, '')
  }

  const fetchFiles = useCallback(async (queryFilters = null) => {
    if (rateLimited) return // Don't make requests when rate limited
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(buildQuery(queryFilters || filters), {
        headers: { 'UserId': userId },
      })
      if (res.status === 429) {
        setRateLimited(true)
        setToast({ message: 'Rate Limit Hit — Try Again', type: 'error' })
        return
      }
      if (!res.ok) throw new Error('Failed to fetch files')
      const data = await res.json()
      // If paginated, data.results exists
      setFiles(Array.isArray(data) ? data : data.results || [])
    } catch (e) {
      setError(e.message || 'Failed to fetch files')
    } finally {
      setLoading(false)
    }
  }, [userId, rateLimited])

  // Only fetch on mount and when refreshKey changes (not on filter changes)
  useEffect(() => { fetchFiles() }, [refreshKey])

  function onUploaded() {
    // Delay refresh to avoid hitting rate limit immediately after upload
    setTimeout(() => {
      setRefreshKey((k) => k + 1)
    }, 500)
  }

  function onFiltersChange(next) {
    setFilters(next)
  }

  async function onDelete(id) {
    if (rateLimited) return // Don't allow delete when rate limited
    try {
      const res = await fetch(`/api/files/${id}/`, { method: 'DELETE', headers: { 'UserId': userId } })
      if (res.status === 409) {
        setToast({ message: 'File has references and cannot be deleted', type: 'error' })
        return
      }
      if (res.status === 429) {
        setRateLimited(true)
        setToast({ message: 'Rate Limit Hit — Try Again', type: 'error' })
        return
      }
      if (!res.ok) throw new Error('Delete failed')
      // Delay refresh to avoid hitting rate limit immediately after delete
      setTimeout(() => {
        setRefreshKey((k) => k + 1)
      }, 600) // Wait 600ms before refreshing
    } catch (e) {
      setToast({ message: e.message || 'Delete failed', type: 'error' })
    }
  }

  return (
    <div style={{ maxWidth: 1000, margin: '20px auto', padding: 16, fontFamily: 'sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Dashboard</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span>User: <strong>{userId}</strong></span>
          <button
            onClick={() => {
              localStorage.removeItem('userId')
              navigate('/')
            }}
            style={{ padding: '6px 12px', cursor: 'pointer' }}
          >
            Logout
          </button>
        </div>
      </div>

      {rateLimited && (
        <div style={{ padding: '10px', backgroundColor: '#ffc107', color: '#000', marginBottom: '16px', borderRadius: '4px' }}>
          ⚠️ Rate limit active. Please wait before making more requests.
        </div>
      )}

      <section style={{ marginTop: 16 }}>
        <h3>Upload File</h3>
        <FileUpload onUploaded={onUploaded} rateLimited={rateLimited} onRateLimit={() => setRateLimited(true)} />
      </section>

      <section style={{ marginTop: 16 }}>
        <h3>Search & Filters</h3>
        <Filters value={filters} onChange={onFiltersChange} disabled={rateLimited} />
        <button 
          onClick={() => fetchFiles(filters)} 
          style={{ marginTop: 8, opacity: (rateLimited || loading) ? 0.6 : 1, cursor: (rateLimited || loading) ? 'not-allowed' : 'pointer' }}
          disabled={rateLimited || loading}
        >
          Search
        </button>
      </section>

      <section style={{ marginTop: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <h3>Files</h3>
          <button 
            onClick={() => fetchFiles(filters)}
            style={{ opacity: (rateLimited || loading) ? 0.6 : 1, cursor: (rateLimited || loading) ? 'not-allowed' : 'pointer' }}
            disabled={rateLimited || loading}
          >
            Refresh
          </button>
        </div>
        {loading && <div>Loading...</div>}
        {error && <div style={{ color: 'red' }}>{error}</div>}
        <FileList items={files} onDelete={onDelete} rateLimited={rateLimited} />
      </section>

      <section style={{ marginTop: 16 }}>
        <h3>Storage Stats</h3>
        <StorageStats refreshKey={refreshKey} userId={userId} />
      </section>
      
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  )
}


