import React, { useState, useEffect } from 'react';
import MasterLocationManager from './MasterLocationManager';
import MasterTransportUnitManager from './MasterTransportUnitManager';
import MasterProcessTemplateManager from './MasterProcessTemplateManager';

const API_URL = 'http://localhost:8000';

function ScenarioManager({ onLoad, onBack }) {
  const [view, setView] = useState('production_scenarios'); // Default view
  const [prodScenarios, setProdScenarios] = useState([]);
  const [logScenarios, setLogScenarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchScenarios = async () => {
    setLoading(true);
    try {
      const [prodRes, logRes] = await Promise.all([
        fetch(`${API_URL}/setups/production/`),
        fetch(`${API_URL}/setups/logistics/`)
      ]);
      if (!prodRes.ok || !logRes.ok) {
        throw new Error('Gagal mengambil data skenario.');
      }
      const prodData = await prodRes.json();
      const logData = await logRes.json();
      setProdScenarios(prodData);
      setLogScenarios(logData);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Only fetch scenarios if we are in a scenario view
    if (['production_scenarios', 'logistics_scenarios'].includes(view)) {
      fetchScenarios();
    }
  }, [view]); 

  const handleDelete = async (type, id) => {
    if (!window.confirm('Apakah Anda yakin ingin menghapus skenario ini?')) {
      return;
    }

    try {
      const response = await fetch(`${API_URL}/setups/${type}/${id}`, { method: 'DELETE' });
      if (!response.ok) {
        throw new Error('Gagal menghapus skenario.');
      }
      // Refresh list after delete
      fetchScenarios(); 
    } catch (err) {
      alert(err.message);
    }
  };

  const handleLoad = async (type, id) => {
    try {
      const response = await fetch(`${API_URL}/setups/${type}/${id}`);
      if (!response.ok) {
        throw new Error(`Gagal memuat skenario ${type} #${id}`);
      }
      const fullScenario = await response.json();
      const setupType = type === 'production' ? 'production_setup' : 'logistics_setup';
      onLoad(setupType, fullScenario.setup_data);
    } catch (err) {
      alert(err.message);
    }
  };

  const renderScenarioList = (scenarios, type) => {
    if (loading) {
      return <p>Memuat skenario...</p>;
    }
    if (error) {
      return <div className="alert alert-danger">{error}</div>;
    }
    if (scenarios.length === 0) {
      return <p>Belum ada skenario yang tersimpan untuk tipe ini.</p>;
    }
    return (
      <ul className="list-group">
        {scenarios.map(s => (
          <li key={s.id} className="list-group-item d-flex justify-content-between align-items-center">
            <div>
              <h5 className="mb-1">{s.name}</h5>
              <p className="mb-1 text-muted">{s.description || 'Tidak ada deskripsi.'}</p>
              <small>Dibuat: {new Date(s.created_at).toLocaleString()}</small>
            </div>
            <div>
              <button className="btn btn-sm btn-primary me-2" onClick={() => handleLoad(type, s.id)}>Muat</button>
              <button className="btn btn-sm btn-danger" onClick={() => handleDelete(type, s.id)}>Hapus</button>
            </div>
          </li>
        ))}
      </ul>
    );
  };

  const renderContent = () => {
    switch (view) {
      case 'production_scenarios':
        return renderScenarioList(prodScenarios, 'production');
      case 'logistics_scenarios':
        return renderScenarioList(logScenarios, 'logistics');
      case 'master_locations':
        return <MasterLocationManager onBack={() => setView('production_scenarios')} />;
      case 'master_transport_units':
        return <MasterTransportUnitManager onBack={() => setView('production_scenarios')} />;
      case 'master_process_templates':
        return <MasterProcessTemplateManager onBack={() => setView('production_scenarios')} />;
      default:
        return <p>Pilih tampilan.</p>;
    }
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2>Manajemen Skenario & Data Master</h2>
        <button className="btn btn-secondary" onClick={onBack}>Kembali ke Menu Utama</button>
      </div>

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item">
          <button className={`nav-link ${view === 'production_scenarios' ? 'active' : ''}`} onClick={() => setView('production_scenarios')}>Skenario Produksi</button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${view === 'logistics_scenarios' ? 'active' : ''}`} onClick={() => setView('logistics_scenarios')}>Skenario Logistik</button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${view === 'master_locations' ? 'active' : ''}`} onClick={() => setView('master_locations')}>Master Lokasi</button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${view === 'master_transport_units' ? 'active' : ''}`} onClick={() => setView('master_transport_units')}>Master Unit Transportasi</button>
        </li>
        <li className="nav-item">
          <button className={`nav-link ${view === 'master_process_templates' ? 'active' : ''}`} onClick={() => setView('master_process_templates')}>Master Template Proses</button>
        </li>
      </ul>

      {renderContent()}
    </div>
  );
}

export default ScenarioManager;