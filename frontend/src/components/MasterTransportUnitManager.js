import React, { useState, useEffect } from 'react';

const API_URL = 'http://localhost:8000';

function MasterTransportUnitManager({ onBack }) {
  const [units, setUnits] = useState([]);
  const [newName, setNewName] = useState('');
  const [newType, setNewType] = useState('Kururu');
  // FIXED: Changed state to match backend model
  const [newNumSubUnits, setNewNumSubUnits] = useState(1);
  const [newCapacityPerSubUnit, setNewCapacityPerSubUnit] = useState(1);
  const [newDescription, setNewDescription] = useState('');
  const [editingUnit, setEditingUnit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchUnits = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/master/transport-units/`);
      if (!response.ok) {
        throw new Error('Gagal mengambil daftar unit transportasi.');
      }
      const data = await response.json();
      setUnits(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnits();
  }, []);

  const handleAddOrUpdateUnit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!newName.trim() || !newType.trim()) {
      setError('Nama dan Tipe unit tidak boleh kosong.');
      return;
    }

    // FIXED: Payload now matches the MasterTransportUnitCreate schema
    const payload = {
      name: newName,
      type: newType,
      num_sub_units: parseInt(newNumSubUnits, 10) || 1,
      capacity_per_sub_unit: parseInt(newCapacityPerSubUnit, 10) || 1,
      description: newDescription || null,
    };

    try {
      let response;
      if (editingUnit) {
        response = await fetch(`${API_URL}/master/transport-units/${editingUnit.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        response = await fetch(`${API_URL}/master/transport-units/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Gagal menyimpan unit transportasi.');
      }

      // Reset form
      setNewName('');
      setNewType('Kururu');
      setNewNumSubUnits(1);
      setNewCapacityPerSubUnit(1);
      setNewDescription('');
      setEditingUnit(null);
      fetchUnits(); // Refresh list
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEditClick = (unit) => {
    setEditingUnit(unit);
    setNewName(unit.name);
    setNewType(unit.type);
    // FIXED: Set state for the correct fields
    setNewNumSubUnits(unit.num_sub_units || 1);
    setNewCapacityPerSubUnit(unit.capacity_per_sub_unit || 1);
    setNewDescription(unit.description || '');
  };

  const handleDeleteUnit = async (id) => {
    if (!window.confirm('Apakah Anda yakin ingin menghapus unit transportasi ini?')) {
      return;
    }
    setError(null);
    try {
      const response = await fetch(`${API_URL}/master/transport-units/${id}`, { method: 'DELETE' });
      if (!response.ok) {
        throw new Error('Gagal menghapus unit transportasi.');
      }
      fetchUnits(); // Refresh list
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="card shadow-sm">
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h2 className="card-title">Manajemen Unit Transportasi Master</h2>
          <button className="btn btn-secondary" onClick={onBack}>Kembali</button>
        </div>

        {error && <div className="alert alert-danger">{error}</div>}

        <form onSubmit={handleAddOrUpdateUnit} className="mb-4 p-3 border rounded bg-light">
          <h5>{editingUnit ? 'Edit Unit Transportasi' : 'Tambah Unit Transportasi Baru'}</h5>
          <div className="row">
            <div className="col-md-6 mb-3">
              <label htmlFor="unitName" className="form-label">Nama Unit</label>
              <input type="text" className="form-control" id="unitName" value={newName} onChange={(e) => setNewName(e.target.value)} required />
            </div>
            <div className="col-md-6 mb-3">
              <label htmlFor="unitType" className="form-label">Tipe Unit</label>
              <select className="form-control" id="unitType" value={newType} onChange={(e) => setNewType(e.target.value)} required>
                <option value="Kururu">Kururu</option>
                <option value="Forklift">Forklift</option>
                <option value="AGV">AGV</option>
                <option value="Manual">Manual</option>
              </select>
            </div>
            {/* FIXED: Changed form inputs to match backend model */}
            <div className="col-md-6 mb-3">
              <label htmlFor="numSubUnits" className="form-label">Jumlah Sub-unit (e.g., Gerbong)</label>
              <input type="number" className="form-control" id="numSubUnits" value={newNumSubUnits} onChange={(e) => setNewNumSubUnits(e.target.value)} />
            </div>
            <div className="col-md-6 mb-3">
              <label htmlFor="capacityPerSubUnit" className="form-label">Kapasitas per Sub-unit (Lot)</label>
              <input type="number" className="form-control" id="capacityPerSubUnit" value={newCapacityPerSubUnit} onChange={(e) => setNewCapacityPerSubUnit(e.target.value)} />
            </div>
            <div className="col-md-12 mb-3">
              <label htmlFor="unitDescription" className="form-label">Deskripsi (Opsional)</label>
              <textarea className="form-control" id="unitDescription" rows="2" value={newDescription} onChange={(e) => setNewDescription(e.target.value)}></textarea>
            </div>
          </div>
          <button type="submit" className="btn btn-primary me-2">
            {editingUnit ? 'Update Unit' : 'Tambah Unit'}
          </button>
          {editingUnit && (
            <button type="button" className="btn btn-outline-secondary" onClick={() => {
              setEditingUnit(null);
              setNewName('');
              setNewType('Kururu');
              setNewNumSubUnits(1);
              setNewCapacityPerSubUnit(1);
              setNewDescription('');
            }}>Batal</button>
          )}
        </form>

        <h4>Daftar Unit Transportasi</h4>
        {loading ? (
          <p>Memuat unit transportasi...</p>
        ) : units.length === 0 ? (
          <p>Belum ada unit transportasi master yang tersimpan.</p>
        ) : (
          <ul className="list-group">
            {units.map(unit => (
              <li key={unit.id} className="list-group-item d-flex justify-content-between align-items-center">
                <div>
                  <h6 className="mb-1">{unit.name} ({unit.type})</h6>
                  <small className="text-muted">Sub-unit: {unit.num_sub_units}, Kapasitas: {unit.capacity_per_sub_unit} lot/sub-unit</small>
                  {unit.description && <small className="d-block text-muted">{unit.description}</small>}
                </div>
                <div>
                  <button className="btn btn-sm btn-warning me-2" onClick={() => handleEditClick(unit)}>Edit</button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDeleteUnit(unit.id)}>Hapus</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default MasterTransportUnitManager;