import React from 'react'

function fmtBytes(b) {
  if (!b && b !== 0) return ''
  return `${(b / (1024 * 1024)).toFixed(2)} MB`
}

export default function FileList({ items, onDelete, rateLimited = false }) {
  if (!items || items.length === 0) return <div>No files</div>
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Name</th>
            <th style={{ textAlign: 'left' }}>Type</th>
            <th style={{ textAlign: 'left' }}>Size</th>
            <th style={{ textAlign: 'left' }}>Uploaded</th>
            <th style={{ textAlign: 'left' }}>Reference?</th>
            <th style={{ textAlign: 'left' }}>Refs</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((f) => (
            <tr key={f.id}>
              <td>{f.original_filename}</td>
              <td>{f.file_type}</td>
              <td>{fmtBytes(f.size)}</td>
              <td>{new Date(f.uploaded_at).toLocaleString()}</td>
              <td>{f.is_reference ? 'Yes' : 'No'}</td>
              <td>{f.reference_count ?? 0}</td>
              <td>
                <button 
                  onClick={() => onDelete && onDelete(f.id)}
                  style={{ opacity: rateLimited ? 0.6 : 1, cursor: rateLimited ? 'not-allowed' : 'pointer' }}
                  disabled={rateLimited}
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


