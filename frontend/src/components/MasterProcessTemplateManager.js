import React, { useState, useEffect } from 'react';

const API_URL = 'http://localhost:8000';

function MasterProcessTemplateManager({ onBack }) {
  const [templates, setTemplates] = useState([]);
  const [newName, setNewName] = useState('');
  const [newCycleTime, setNewCycleTime] = useState('');
  const [newNumOperators, setNewNumOperators] = useState('');
  const [newNgRate, setNewNgRate] = useState('');
  const [newRepairTime, setNewRepairTime] = useState('');
  const [newInputFromNames, setNewInputFromNames] = useState([]);
  const [newOutputToNames, setNewOutputToNames] = useState([]);
  const [newJoinType, setNewJoinType] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [editingTemplate, setEditingTemplate] = useState(null); // null or { id, name, ... }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTemplates = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/master/process-templates/`);
      if (!response.ok) {
        throw new Error('Gagal mengambil daftar template proses.');
      }
      const data = await response.json();
      setTemplates(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleAddOrUpdateTemplate = async (e) => {
    e.preventDefault();
    setError(null);
    if (!newName.trim() || newCycleTime === '' || newNumOperators === '' || newNgRate === '' || newRepairTime === '') {
      setError('Semua bidang wajib diisi.');
      return;
    }

    const payload = {
      name: newName,
      cycle_time: parseFloat(newCycleTime),
      num_operators: parseInt(newNumOperators, 10),
      ng_rate: parseFloat(newNgRate),
      repair_time: parseFloat(newRepairTime),
      input_from_names: newInputFromNames,
      output_to_names: newOutputToNames,
      join_type: newJoinType || null,
      description: newDescription || null,
    };

    try {
      let response;
      if (editingTemplate) {
        // Update existing template
        response = await fetch(`${API_URL}/master/process-templates/${editingTemplate.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        // Add new template
        response = await fetch(`${API_URL}/master/process-templates/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Gagal menyimpan template proses.');
      }

      setNewName('');
      setNewCycleTime('');
      setNewNumOperators('');
      setNewNgRate('');
      setNewRepairTime('');
      setNewInputFromNames([]);
      setNewOutputToNames([]);
      setNewJoinType('');
      setNewDescription('');
      setEditingTemplate(null);
      fetchTemplates(); // Refresh list
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEditClick = (template) => {
    setEditingTemplate(template);
    setNewName(template.name);
    setNewCycleTime(template.cycle_time);
    setNewNumOperators(template.num_operators);
    setNewNgRate(template.ng_rate);
    setNewRepairTime(template.repair_time);
    setNewInputFromNames(template.input_from_names || []);
    setNewOutputToNames(template.output_to_names || []);
    setNewJoinType(template.join_type || '');
    setNewDescription(template.description || '');
  };

  const handleDeleteTemplate = async (id) => {
    if (!window.confirm('Apakah Anda yakin ingin menghapus template proses ini?')) {
      return;
    }
    setError(null);
    try {
      const response = await fetch(`${API_URL}/master/process-templates/${id}`, { method: 'DELETE' });
      if (!response.ok) {
        throw new Error('Gagal menghapus template proses.');
      }
      fetchTemplates(); // Refresh list
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="card shadow-sm">
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h2 className="card-title">Manajemen Template Proses Master</h2>
          <button className="btn btn-secondary" onClick={onBack}>Kembali</button>
        </div>

        {error && <div className="alert alert-danger">{error}</div>}

        <form onSubmit={handleAddOrUpdateTemplate} className="mb-4 p-3 border rounded bg-light">
          <h5>{editingTemplate ? 'Edit Template Proses' : 'Tambah Template Proses Baru'}</h5>
          <div className="row">
            <div className="col-md-6 mb-3">
              <label htmlFor="templateName" className="form-label">Nama Template</label>
              <input
                type="text"
                className="form-control"
                id="templateName"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
              />
            </div>
            <div className="col-md-6 mb-3">
              <label htmlFor="cycleTime" className="form-label">Waktu Siklus (detik)</label>
              <input
                type="number"
                step="0.01"
                className="form-control"
                id="cycleTime"
                value={newCycleTime}
                onChange={(e) => setNewCycleTime(e.target.value)}
                required
              />
            </div>
            <div className="col-md-6 mb-3">
              <label htmlFor="numOperators" className="form-label">Jumlah Operator</label>
              <input
                type="number"
                className="form-control"
                id="numOperators"
                value={newNumOperators}
                onChange={(e) => setNewNumOperators(e.target.value)}
                required
              />
            </div>
            <div className="col-md-6 mb-3">
              <label htmlFor="ngRate" className="form-label">Rate NG (0.0 - 1.0)</label>
              <input
                type="number"
                step="0.01"
                className="form-control"
                id="ngRate"
                value={newNgRate}
                onChange={(e) => setNewNgRate(e.target.value)}
                required
              />
            </div>
            <div className="col-md-6 mb-3">
              <label htmlFor="repairTime" className="form-label">Waktu Perbaikan (detik)</label>
              <input
                type="number"
                step="0.01"
                className="form-control"
                id="repairTime"
                value={newRepairTime}
                onChange={(e) => setNewRepairTime(e.target.value)}
                required
              />
            </div>
            <div className="col-md-6 mb-3">
              <label htmlFor="joinType" className="form-label">Tipe Gabungan (Join Type)</label>
              <select
                className="form-control"
                id="joinType"
                value={newJoinType}
                onChange={(e) => setNewJoinType(e.target.value)}
              >
                <option value="">Pilih Tipe Gabungan</option>
                <option value="AND">AND</option>
                <option value="OR">OR</option>
              </select>
            </div>
            <div className="col-md-12 mb-3">
              <label htmlFor="templateDescription" className="form-label">Deskripsi (Opsional)</label>
              <textarea
                className="form-control"
                id="templateDescription"
                rows="2"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
              ></textarea>
            </div>
          </div>
          <button type="submit" className="btn btn-primary me-2">
            {editingTemplate ? 'Update Template' : 'Tambah Template'}
          </button>
          {editingTemplate && (
            <button type="button" className="btn btn-outline-secondary" onClick={() => {
              setEditingTemplate(null);
              setNewName('');
              setNewCycleTime('');
              setNewNumOperators('');
              setNewNgRate('');
              setNewRepairTime('');
              setNewInputFromNames([]);
              setNewOutputToNames([]);
              setNewJoinType('');
              setNewDescription('');
            }}>Batal</button>
          )}
        </form>

        <h4>Daftar Template Proses</h4>
        {loading ? (
          <p>Memuat template proses...</p>
        ) : templates.length === 0 ? (
          <p>Belum ada template proses master yang tersimpan.</p>
        ) : (
          <ul className="list-group">
            {templates.map(tpl => (
              <li key={tpl.id} className="list-group-item d-flex justify-content-between align-items-center">
                <div>
                  <h6 className="mb-1">{tpl.name}</h6>
                  <small className="text-muted">Siklus: {tpl.cycle_time}s, Operator: {tpl.num_operators}, NG Rate: {tpl.ng_rate}</small>
                  {tpl.description && <small className="d-block text-muted">{tpl.description}</small>}
                </div>
                <div>
                  <button className="btn btn-sm btn-warning me-2" onClick={() => handleEditClick(tpl)}>Edit</button>
                  <button className="btn btn-sm btn-danger" onClick={() => handleDeleteTemplate(tpl.id)}>Hapus</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default MasterProcessTemplateManager;
