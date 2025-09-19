import React, { useState, useEffect } from 'react';

const API_URL = 'http://localhost:8000';

function MasterLocationManager({ onBack }) {
  const [locations, setLocations] = useState([]);
  const [newLocationName, setNewLocationName] = useState('');
  const [newLocationDescription, setNewLocationDescription] = useState('');
  const [editingLocation, setEditingLocation] = useState(null); // null or { id, name, description }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchLocations = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/master/locations/`);
      if (!response.ok) {
        throw new Error('Gagal mengambil daftar lokasi.');
      }
      const data = await response.json();
      setLocations(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLocations();
  }, []);

  const handleAddOrUpdateLocation = async (e) => {
    e.preventDefault();
    setError(null);
    if (!newLocationName.trim()) {
      setError('Nama lokasi tidak boleh kosong.');
      return;
    }

    const payload = {
      name: newLocationName,
      description: newLocationDescription || null,
    };

    try {
      let response;
      if (editingLocation) {
        // Update existing location
        response = await fetch(`${API_URL}/master/locations/${editingLocation.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        // Add new location
        response = await fetch(`${API_URL}/master/locations/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Gagal menyimpan lokasi.');
      }

      setNewLocationName('');
      setNewLocationDescription('');
      setEditingLocation(null);
      fetchLocations(); // Refresh list
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEditClick = (location) => {
    setEditingLocation(location);
    setNewLocationName(location.name);
    setNewLocationDescription(location.description || '');
  };

  const handleDeleteLocation = async (id) => {
    if (!window.confirm('Apakah Anda yakin ingin menghapus lokasi ini?')) {
      return;
    }
    setError(null);
    try {
      const response = await fetch(`${API_URL}/master/locations/${id}`, { method: 'DELETE' });
      if (!response.ok) {
        throw new Error('Gagal menghapus lokasi.');
      }
      fetchLocations(); // Refresh list
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="card shadow-sm">
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h2 className="card-title">Manajemen Lokasi Master</h2>
          <button className="btn btn-secondary" onClick={onBack}>Kembali</button>
        </div>

        {error && <div className="alert alert-danger">{error}</div>}

        <form onSubmit={handleAddOrUpdateLocation} className="mb-4 p-3 border rounded bg-light">
          <h5>{editingLocation ? 'Edit Lokasi' : 'Tambah Lokasi Baru'}</h5>
          <div className="mb-3">
            <label htmlFor="locationName" className="form-label">Nama Lokasi</label>
            <input
              type="text"
              className="form-control"
              id="locationName"
              value={newLocationName}
              onChange={(e) => setNewLocationName(e.target.value)}
              required
            />
          </div>
          <div className="mb-3">
            <label htmlFor="locationDescription" className="form-label">Deskripsi (Opsional)</label>
            <textarea
              className="form-control"
              id="locationDescription"
              rows="2"
              value={newLocationDescription}
              onChange={(e) => setNewLocationDescription(e.target.value)}
            ></textarea>
          </div>
          <button type="submit" className="btn btn-primary me-2">
            {editingLocation ? 'Update Lokasi' : 'Tambah Lokasi'}
          </button>
          {editingLocation && (
            <button type="button" className="btn btn-outline-secondary" onClick={() => {
              setEditingLocation(null);
              setNewLocationName('');
              setNewLocationDescription('');
            }}>Batal</button>
          )}
        </form>

        <h4>Daftar Lokasi</h4>
        {loading ? (
          <p>Memuat lokasi...</p>
        ) : locations.length === 0 ? (
          <p>Belum ada lokasi master yang tersimpan.</p>
        ) : (
          <ul className="list-group">
            {locations.map(loc => (
              <li key={loc.id} className="list-group-item d-flex justify-content-between align-items-center">
                <div>
                  <h6 className="mb-1">{loc.name}</h6>
                  <small className="text-muted">{loc.description || 'Tidak ada deskripsi.'}</small>
                </div>
                <div>
                  <button className="btn btn-sm btn-warning me-2" onClick={() => handleEditClick(loc)}>Edit</button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDeleteLocation(loc.id)}>Hapus</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default MasterLocationManager;
