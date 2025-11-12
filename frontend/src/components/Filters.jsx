import React, { useEffect, useState } from 'react'

export default function Filters({ value, onChange, disabled = false }) {
  const [fileTypes, setFileTypes] = useState([])
  const [form, setForm] = useState({
    search: value.search || '',
    file_type: value.file_type || '',
    min_size: value.min_size || '',
    max_size: value.max_size || '',
    start_date: value.start_date || '',
    end_date: value.end_date || '',
  })

  useEffect(() => {
    const userId = localStorage.getItem('userId')
    if (!userId) return
    fetch('/api/files/file_types/', { headers: { 'UserId': userId } })
      .then((r) => r.json())
      .then((d) => setFileTypes(Array.isArray(d) ? d : []))
      .catch(() => setFileTypes([]))
  }, [])

  function update(k, v) {
    const next = { ...form, [k]: v }
    setForm(next)
    onChange && onChange(next)
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
      <input 
        placeholder="Search filename" 
        value={form.search} 
        onChange={(e) => update('search', e.target.value)}
        disabled={disabled}
      />
      <select 
        value={form.file_type} 
        onChange={(e) => update('file_type', e.target.value)}
        disabled={disabled}
      >
        <option value="">All types</option>
        {fileTypes.map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
      <input 
        type="number" 
        placeholder="Min size (bytes)" 
        value={form.min_size} 
        onChange={(e) => update('min_size', e.target.value)}
        disabled={disabled}
      />
      <input 
        type="number" 
        placeholder="Max size (bytes)" 
        value={form.max_size} 
        onChange={(e) => update('max_size', e.target.value)}
        disabled={disabled}
      />
      <input 
        type="datetime-local" 
        value={form.start_date} 
        onChange={(e) => update('start_date', e.target.value)}
        disabled={disabled}
      />
      <input 
        type="datetime-local" 
        value={form.end_date} 
        onChange={(e) => update('end_date', e.target.value)}
        disabled={disabled}
      />
    </div>
  )
}


