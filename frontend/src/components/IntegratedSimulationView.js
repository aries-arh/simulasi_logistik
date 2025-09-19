import React, { useState, useEffect, useCallback } from 'react';

const API_URL = 'http://localhost:8000';

// New component for file uploads
function FileUpload({ title, uploadUrl, onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
    setSuccess(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first.');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(uploadUrl, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const result = await response.json();
      setSuccess(result.message || 'File uploaded successfully!');
      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="file-upload-card p-2 mt-2">
      <label className="form-label small fw-bold">Update {title}</label>
      <div className="input-group">
        <input type="file" className="form-control form-control-sm" onChange={handleFileChange} />
        <button className="btn btn-sm btn-outline-primary" onClick={handleUpload} disabled={uploading || !file}>
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </div>
      {error && <div className="text-danger small mt-1">{error}</div>}
      {success && <div className="text-success small mt-1">{success}</div>}
    </div>
  );
}

function IntegratedSimulationView({ onBack }) {
  const [prodScenarios, setProdScenarios] = useState([]);
  const [logScenarios, setLogScenarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [prodStatus, setProdStatus] = useState(null);
  const [logStatus, setLogStatus] = useState(null);
  const [simulationSpeed, setSimulationSpeed] = useState(1.0);
  const [isPaused, setIsPaused] = useState(false);

  const [selectedProdSetupId, setSelectedProdSetupId] = useState('');
  const [selectedLogSetupId, setSelectedLogSetupId] = useState('');
  const [useMasterLocations, setUseMasterLocations] = useState(true);
  const [masterLocations, setMasterLocations] = useState([]);
  const [masterTransportUnits, setMasterTransportUnits] = useState([]);
  const [customTransportUnits, setCustomTransportUnits] = useState([]);
  const [useCustomLogistics, setUseCustomLogistics] = useState(true);
  const [assemblyOperators, setAssemblyOperators] = useState(2);
  const [packingOperators, setPackingOperators] = useState(1);
  const [dataSummary, setDataSummary] = useState({
    schedule: null,
    mrp: null,
    bom: null
  });
  const [taskConfig, setTaskConfig] = useState({
    origin: '',
    destination: 'Assembly',
    material: 'V874062',
    lots_required: 1,
    distance: 100,
    travel_time: 30,
    loading_time: 10,
    unloading_time: 10,
    return_time: 30,
    unit_start_delay: 0,
  });

  const loadDataSummaries = useCallback(async () => {
    try {
      const [scheduleRes, mrpRes, bomRes] = await Promise.all([
        fetch(`${API_URL}/data/schedule/summary`),
        fetch(`${API_URL}/data/mrp/summary`),
        fetch(`${API_URL}/data/bom/summary`)
      ]);
      
      if (scheduleRes.ok) {
        const scheduleData = await scheduleRes.json();
        setDataSummary(prev => ({ ...prev, schedule: scheduleData }));
      }
      
      if (mrpRes.ok) {
        const mrpData = await mrpRes.json();
        setDataSummary(prev => ({ ...prev, mrp: mrpData }));
      }
      
      if (bomRes.ok) {
        const bomData = await bomRes.json();
        setDataSummary(prev => ({ ...prev, bom: bomData }));
      }
    } catch (err) {
      console.error('Error loading data summaries:', err);
    }
  }, []);

  const fetchSetups = async () => {
    setLoading(true);
    try {
      const [prodRes, logRes] = await Promise.all([
        fetch(`${API_URL}/setups/production/`),
        fetch(`${API_URL}/setups/logistics/`)
      ]);
      if (!prodRes.ok || !logRes.ok) {
        throw new Error('Gagal mengambil data setup.');
      }
      const prodData = await prodRes.json();
      const logData = await logRes.json();
      setProdScenarios(prodData);
      setLogScenarios(logData);

      if (prodData.length > 0 && !selectedProdSetupId) {
        setSelectedProdSetupId(prodData[0].id);
      }
      if (logData.length > 0 && !selectedLogSetupId) {
        setSelectedLogSetupId(logData[0].id);
      }

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSetups();

    const fetchMasterData = async () => {
      try {
        const [locationsRes, transportUnitsRes] = await Promise.all([
          fetch(`${API_URL}/master/locations/`),
          fetch(`${API_URL}/master/transport-units/`)
        ]);

        if (locationsRes.ok) {
          const data = await locationsRes.json();
          setMasterLocations(data.map(l => l.name));
          if (!taskConfig.origin && data.length > 0) {
            setTaskConfig(prev => ({ ...prev, origin: data[0].name }));
          }
        }

        if (transportUnitsRes.ok) {
          const data = await transportUnitsRes.json();
          setMasterTransportUnits(data);
        }

      } catch (err) {
        console.error("Failed to fetch master data:", err);
      }
    };

    fetchMasterData();
    loadDataSummaries();
  }, [loadDataSummaries]);

  const handleCustomTransportUnitChange = (index, event) => {
    const { name, value } = event.target;
    const newUnits = [...customTransportUnits];
    if (name === 'name') {
        const selectedMasterUnit = masterTransportUnits.find(unit => unit.name === value);
        if (selectedMasterUnit) {
            newUnits[index] = { 
                ...newUnits[index], 
                name: selectedMasterUnit.name, 
                type: selectedMasterUnit.type, 
                num_sub_units: selectedMasterUnit.num_sub_units || 1, 
                capacity_per_sub_unit: selectedMasterUnit.capacity_per_sub_unit || 1 
            };
        }
    } else {
                newUnits[index] = { ...newUnits[index], [name]: parseInt(value, 10) || 0 };
    }
    setCustomTransportUnits(newUnits);
  };

  const handleAddCustomTransportUnit = (e) => { 
    e.preventDefault(); 
    setCustomTransportUnits([...customTransportUnits, { name: '', type: '', num_sub_units: 1, capacity_per_sub_unit: 1 }]); 
  };

  const handleRemoveCustomTransportUnit = (index) => { 
    const nu = [...customTransportUnits]; 
    nu.splice(index, 1); 
    setCustomTransportUnits(nu); 
  };

  const buildTransportUnits = () => {
    const validUnits = customTransportUnits.filter(u => u.name);
    return validUnits.length > 0 ? validUnits : [
      { name: 'Forklift 1', type: 'Forklift', num_sub_units: 1, capacity_per_sub_unit: 10 },
      { name: 'Forklift 2', type: 'Forklift', num_sub_units: 1, capacity_per_sub_unit: 10 },
      { name: 'Forklift 3', type: 'Forklift', num_sub_units: 1, capacity_per_sub_unit: 10 }
    ];
  };

  const buildLocations = () => {
    const names = masterLocations && masterLocations.length ? masterLocations : ['WAREHOUSE', 'Assembly'];
    return names.map(n => ({ name: n, stock: {} }));
  };

  const buildTasks = (units) => {
    const unitNames = units.map(u => u.name);
    return [{
      origin: taskConfig.origin || 'WAREHOUSE',
      destination: taskConfig.destination || 'Assembly',
      material: taskConfig.material || 'V874062',
      lots_required: Number(taskConfig.lots_required || 1),
      distance: Number(taskConfig.distance || 100),
      travel_time: Number(taskConfig.travel_time || 30),
      loading_time: Number(taskConfig.loading_time || 10),
      unloading_time: Number(taskConfig.unloading_time || 10),
      return_time: Number(taskConfig.return_time || 30),
      transport_unit_names: unitNames.length ? unitNames : ['Forklift 1', 'Forklift 2', 'Forklift 3'],
      unit_start_delay: Number(taskConfig.unit_start_delay || 0),
    }];
  };

  const createLogisticsSetup = async () => {
    const units = buildTransportUnits();
    const locations = buildLocations();
    const tasks = buildTasks(units);
    const payload = {
      name: `Integrated UI Setup ${new Date().toISOString()}`,
      description: 'Created from IntegratedSimulationView UI',
      setup_data: {
        locations,
        transport_units: units,
        tasks,
        workday_start_time: 0,
        workday_end_time: 28800,
        shifts: [{ start_time: 0, end_time: 28800 }],
        scheduled_events: [],
        abnormality_rate: 0,
        abnormality_duration: 0,
      },
    };
    const res = await fetch(`${API_URL}/setups/logistics/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(`Gagal membuat setup logistik: ${JSON.stringify(errorData.detail)}`);
    }
    const data = await res.json();
    return data.id;
  };

  const handleStartIntegrated = async () => {
    if (!selectedProdSetupId || !selectedLogSetupId) {
      alert('Harap pilih setup produksi dan logistik.');
      return;
    }

    try {
      setSimulationRunning(true);
      const params = new URLSearchParams();
      if (useMasterLocations) params.append('use_master_locations', 'true');
      params.append('assembly_operators', assemblyOperators);
      params.append('packing_operators', packingOperators);
      let logSetupIdToUse = selectedLogSetupId;
      if (useCustomLogistics) {
        logSetupIdToUse = await createLogisticsSetup();
        setSelectedLogSetupId(logSetupIdToUse);
      }

      const response = await fetch(`${API_URL}/simulation/start-integrated/${selectedProdSetupId}/${logSetupIdToUse}?${params.toString()}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Gagal memulai simulasi terintegrasi.');
      }

      const result = await response.json();
      alert(result.message);
      
      // Start polling for status updates
      startStatusPolling();

    } catch (err) {
      alert(`Error: ${err.message}`);
      setSimulationRunning(false);
    }
  };

  const startStatusPolling = () => {
    const interval = setInterval(async () => {
      try {
        const [prodRes, logRes] = await Promise.all([
          fetch(`${API_URL}/production/status`),
          fetch(`${API_URL}/logistics/status`)
        ]);

        let prodData = null;
        if (prodRes.ok) {
          prodData = await prodRes.json();
          setProdStatus(prodData);
        }

        let logData = null;
        if (logRes.ok) {
          logData = await logRes.json();
          setLogStatus(logData);
          setIsPaused(logData.is_paused || false);
          setSimulationSpeed(logData.simulation_speed || 1.0);
        }

        // Now check the status using the variables
        if (prodData && logData && prodData.status === 'finished' && (logData.status === 'finished' || logData.status === 'stopped')) {
          clearInterval(interval);
          setSimulationRunning(false);
        }
      } catch (err) {
        console.error('Error fetching status:', err);
        // Optional: Stop polling on error to avoid flooding the console
        // clearInterval(interval);
        // setSimulationRunning(false);
      }
    }, 2000);

    // Store interval ID to clear it on component unmount
    return interval;
  };

  const handlePause = async () => {
    try {
      const response = await fetch(`${API_URL}/logistics/pause`, { method: 'POST' });
      if (response.ok) {
        setIsPaused(true);
      } else {
        alert('Failed to pause simulation');
      }
    } catch (err) {
      alert('Error pausing simulation: ' + err.message);
    }
  };

  const handleResume = async () => {
    try {
      const response = await fetch(`${API_URL}/logistics/resume`, { method: 'POST' });
      if (response.ok) {
        setIsPaused(false);
      } else {
        alert('Failed to resume simulation');
      }
    } catch (err) {
      alert('Error resuming simulation: ' + err.message);
    }
  };

  const handleSetSpeed = async (speed) => {
    try {
      const response = await fetch(`${API_URL}/logistics/set-speed/${speed}`, { method: 'POST' });
      if (response.ok) {
        setSimulationSpeed(speed);
      } else {
        alert('Failed to set simulation speed');
      }
    } catch (err) {
      alert('Error setting speed: ' + err.message);
    }
  };

  if (loading) {
    return (
      <div className="text-center">
        <div className="loading-spinner"></div>
        <p className="mt-3">Memuat setup simulasi...</p>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="alert alert-modern alert-danger-modern">
        <h5><i className="fas fa-exclamation-triangle"></i> Error</h5>
        <p>{error}</p>
        <button onClick={onBack} className="btn btn-modern btn-secondary-modern">
          <i className="fas fa-arrow-left"></i> Kembali
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2><i className="fas fa-sync-alt"></i> Simulasi Terintegrasi</h2>
        <button onClick={onBack} className="btn btn-modern btn-secondary-modern">
          <i className="fas fa-arrow-left"></i> Kembali
        </button>
      </div>
      
      <p className="lead mb-4">Mulai simulasi produksi dan logistik secara bersamaan untuk analisis holistik sistem.</p>

      {/* Data Summary Section */}
      <div className="simulation-card p-3 mb-3">
        <h4 className="mb-3"><i className="fas fa-database text-info"></i> Data Summary</h4>
        <div className="row">
          <div className="col-md-4">
            <div className="data-summary-card p-2">
              <h6><i className="fas fa-calendar-alt text-primary"></i> Production Schedule</h6>
              {dataSummary.schedule ? (
                <div>
                  <div className="small text-muted">Total Rows: {dataSummary.schedule.total_rows}</div>
                  <div className="small text-muted">Columns: {dataSummary.schedule.columns?.length || 0}</div>
                  {dataSummary.schedule.summary && dataSummary.schedule.summary.today_summary && (
                    <div className="mt-2">
                      <div className="small fw-bold">Ringkasan untuk Hari Ini ({dataSummary.schedule.summary.today_summary.day_name || 'N/A'})</div>
                      {dataSummary.schedule.summary.today_summary.found ? (
                        <>
                          <div className="small">Total Units: {dataSummary.schedule.summary.today_summary.total_units || 0}</div>
                          <div className="small">Unique Models: {dataSummary.schedule.summary.today_summary.unique_models || 0}</div>
                          <div className="small">Unique Part Nos: {dataSummary.schedule.summary.today_summary.unique_part_nos || 0}</div>
                        </>
                      ) : (
                        <div className="small text-warning">Tidak ada jadwal untuk hari ini.</div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-muted small">Loading...</div>
              )}
              <FileUpload title="Schedule" uploadUrl={`${API_URL}/upload/schedule`} onUploadSuccess={loadDataSummaries} />
            </div>
          </div>
          <div className="col-md-4">
            <div className="data-summary-card p-2">
              <h6><i className="fas fa-boxes text-success"></i> MRP Data</h6>
              {dataSummary.mrp ? (
                <div>
                  <div className="small text-muted">Materials: {dataSummary.mrp.materials_count}</div>
                  <div className="small text-muted">Locations: {dataSummary.mrp.unique_locations?.length || 0}</div>
                  <div className="small text-muted">Status: <span className="text-success">Loaded</span></div>
                </div>
              ) : (
                <div className="text-muted small">Loading...</div>
              )}
              <FileUpload title="MRP" uploadUrl={`${API_URL}/upload/mrp`} onUploadSuccess={loadDataSummaries} />
            </div>
          </div>
          <div className="col-md-4">
            <div className="data-summary-card p-2">
              <h6><i className="fas fa-sitemap text-warning"></i> BOM Data</h6>
              {dataSummary.bom ? (
                <div>
                  <div className="small text-muted">Parent Parts: {dataSummary.bom.parent_parts_count}</div>
                  <div className="small text-muted">Total Components: {dataSummary.bom.total_components}</div>
                  <div className="small text-muted">Avg Components: {dataSummary.bom.average_components_per_parent}</div>
                </div>
              ) : (
                <div className="text-muted small">Loading...</div>
              )}
              <FileUpload title="BOM" uploadUrl={`${API_URL}/upload/bom`} onUploadSuccess={loadDataSummaries} />
            </div>
          </div>
        </div>
      </div>

      <div className="simulation-card p-3 mb-3">
        <h4 className="mb-3"><i className="fas fa-play-circle"></i> Mulai Simulasi Terintegrasi</h4>
        
        <div className="row">
          <div className="col-md-6 mb-3">
            <label htmlFor="prodSetupSelect" className="form-label fw-bold">
              <i className="fas fa-cogs text-primary"></i> Pilih Setup Produksi:
            </label>
          <select 
            id="prodSetupSelect" 
              className="form-select form-select-lg" 
            value={selectedProdSetupId} 
            onChange={(e) => setSelectedProdSetupId(e.target.value)}
          >
            {prodScenarios.length === 0 ? (
              <option value="">Tidak ada setup produksi</option>
            ) : (
              prodScenarios.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))
            )}
          </select>
        </div>

          <div className="col-md-6 mb-3">
            <label htmlFor="logSetupSelect" className="form-label fw-bold">
              <i className="fas fa-truck text-success"></i> Pilih Setup Logistik:
            </label>
          <select 
            id="logSetupSelect" 
              className="form-select form-select-lg" 
            value={selectedLogSetupId} 
            onChange={(e) => setSelectedLogSetupId(e.target.value)}
          >
            {logScenarios.length === 0 ? (
              <option value="">Tidak ada setup logistik</option>
            ) : (
              logScenarios.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))
            )}
          </select>
          </div>
        </div>

        <div className="row">
          <div className="col-md-4 mb-3">
            <label className="form-label fw-bold">Assembly Operators</label>
            <input type="number" className="form-control" value={assemblyOperators} onChange={(e) => setAssemblyOperators(parseInt(e.target.value, 10) || 1)} />
          </div>
          <div className="col-md-4 mb-3">
            <label className="form-label fw-bold">Packing Operators</label>
            <input type="number" className="form-control" value={packingOperators} onChange={(e) => setPackingOperators(parseInt(e.target.value, 10) || 1)} />
          </div>
          <div className="col-md-4 mb-3">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="useMasterLocations"
                checked={useMasterLocations}
                onChange={(e) => setUseMasterLocations(e.target.checked)}
              />
              <label className="form-check-label fw-bold" htmlFor="useMasterLocations">
                Gunakan Master Locations
              </label>
            </div>
            <small className="text-muted">Jika aktif, lokasi logistik diambil dari master lokasi.</small>
          </div>
        </div>

        {/* Custom Logistics Config */}
        <div className="row">
          <div className="col-md-12 mb-3">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                id="useCustomLogistics"
                checked={useCustomLogistics}
                onChange={(e) => setUseCustomLogistics(e.target.checked)}
              />
              <label className="form-check-label fw-bold" htmlFor="useCustomLogistics">
                Gunakan konfigurasi logistik khusus (kendaraan & tugas)
              </label>
            </div>
          </div>
        </div>

        {useCustomLogistics && (
          <>
            <div className="row">
              <div className="col-md-6 mb-3">
                <h6 className="mb-2"><i className="fas fa-shipping-fast"></i> Kendaraan</h6>
                {customTransportUnits.map((unit, index) => (
                  <div key={index} className="p-3 mb-3 border rounded bg-light">
                    <h5>Unit #{index + 1}</h5>
                    <div className="row">
                      <div className="col-md-6 mb-2"><label>Pilih Unit</label><select className="form-control" name="name" value={unit.name} onChange={(e) => handleCustomTransportUnitChange(index, e)}><option value="">Pilih</option>{masterTransportUnits.map(mtu => <option key={mtu.id} value={mtu.name}>{mtu.name}</option>)}</select></div>
                      <div className="col-md-6 mb-2"><label>Tipe</label><input type="text" className="form-control" value={unit.type || ''} readOnly /></div>
                      <div className="col-md-6 mb-2"><label>Jml Sub-unit</label><input type="number" className="form-control" name="num_sub_units" value={unit.num_sub_units || 1} onChange={(e) => handleCustomTransportUnitChange(index, e)} /></div>
                      <div className="col-md-6 mb-2"><label>Kapasitas/Sub-unit</label><input type="number" className="form-control" name="capacity_per_sub_unit" value={unit.capacity_per_sub_unit || 1} onChange={(e) => handleCustomTransportUnitChange(index, e)} /></div>
                    </div>
                    <button type="button" className="btn btn-sm btn-danger mt-2" onClick={() => handleRemoveCustomTransportUnit(index)}>Hapus</button>
                  </div>
                ))}
                <button type="button" className="btn btn-secondary mb-3" onClick={handleAddCustomTransportUnit}>+ Tambah Unit</button>
              </div>

              <div className="col-md-6 mb-3">
                <h6 className="mb-2"><i className="fas fa-route"></i> Tugas</h6>
                <div className="row g-2">
                  <div className="col-6">
                    <label className="form-label">Asal</label>
                    <select className="form-select" value={taskConfig.origin} onChange={(e)=>setTaskConfig({...taskConfig, origin: e.target.value})}>
                      {masterLocations.length ? masterLocations.map(n => (
                        <option key={n} value={n}>{n}</option>
                      )) : <option value="WAREHOUSE">WAREHOUSE</option>}
                    </select>
                  </div>
                  <div className="col-6">
                    <label className="form-label">Tujuan</label>
                    <input className="form-control" value={taskConfig.destination} onChange={(e)=>setTaskConfig({...taskConfig, destination: e.target.value})} />
                  </div>
                  <div className="col-6">
                    <label className="form-label">Material</label>
                    <input className="form-control" value={taskConfig.material} onChange={(e)=>setTaskConfig({...taskConfig, material: e.target.value})} />
                  </div>
                  <div className="col-6">
                    <label className="form-label">Lots</label>
                    <input type="number" className="form-control" value={taskConfig.lots_required} onChange={(e)=>setTaskConfig({...taskConfig, lots_required: e.target.value})} />
                  </div>
                  <div className="col-6">
                    <label className="form-label">Jarak</label>
                    <input type="number" className="form-control" value={taskConfig.distance} onChange={(e)=>setTaskConfig({...taskConfig, distance: e.target.value})} />
                  </div>
                  <div className="col-6">
                    <label className="form-label">Travel (detik)</label>
                    <input type="number" className="form-control" value={taskConfig.travel_time} onChange={(e)=>setTaskConfig({...taskConfig, travel_time: e.target.value})} />
                  </div>
                  <div className="col-6">
                    <label className="form-label">Loading (detik)</label>
                    <input type="number" className="form-control" value={taskConfig.loading_time} onChange={(e)=>setTaskConfig({...taskConfig, loading_time: e.target.value})} />
                  </div>
                  <div className="col-6">
                    <label className="form-label">Unloading (detik)</label>
                    <input type="number" className="form-control" value={taskConfig.unloading_time} onChange={(e)=>setTaskConfig({...taskConfig, unloading_time: e.target.value})} />
                  </div>
                  <div className="col-6">
                    <label className="form-label">Return (detik)</label>
                    <input type="number" className="form-control" value={taskConfig.return_time} onChange={(e)=>setTaskConfig({...taskConfig, return_time: e.target.value})} />
                  </div>
                  <div className="col-6">
                    <label className="form-label">Start Delay (detik)</label>
                    <input type="number" className="form-control" value={taskConfig.unit_start_delay} onChange={(e)=>setTaskConfig({...taskConfig, unit_start_delay: e.target.value})} />
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        <div className="text-center">
        <button 
            className="btn btn-modern btn-info-modern btn-lg" 
          onClick={handleStartIntegrated}
            disabled={prodScenarios.length === 0 || logScenarios.length === 0 || simulationRunning}
          >
            {simulationRunning ? (
              <>
                <div className="loading-spinner me-2" style={{width: '20px', height: '20px'}}></div>
                Simulasi Berjalan...
              </>
            ) : (
              <>
                <i className="fas fa-play"></i> Mulai Simulasi Terintegrasi
              </>
            )}
        </button>
        </div>
      </div>

      {/* Alerts */}
      {isPaused && (
        <div className="alert alert-warning alert-modern alert-dismissible fade show" role="alert">
          <i className="fas fa-pause-circle"></i> Simulasi sedang dijeda. Klik Resume untuk melanjutkan.
          <button type="button" className="btn-close" onClick={() => setIsPaused(false)} aria-label="Close"></button>
        </div>
      )}

      {/* Status Display */}
      {(simulationRunning || prodStatus || logStatus) && (
        <div className="row">
          <div className="col-md-6">
            <div className="simulation-card p-3">
              <h5 className="mb-3"><i className="fas fa-cogs text-primary"></i> Status Produksi</h5>
              {prodStatus ? (
                <div>
                  <div className="row mb-3">
                    <div className="col-6">
                      <div className="metric-card">
                    <div className="metric-value text-primary">{prodStatus.completed_units || 0}</div>
                    <div className="metric-label">Unit Selesai</div>
                  </div>
                    </div>
                    <div className="col-6">
                      <div className="metric-card">
                    <div className="metric-value text-danger">{prodStatus.scrapped_units || 0}</div>
                    <div className="metric-label">Unit Gagal</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="row mb-3">
                    <div className="col-6">
                      <div className="metric-card">
                        <div className="metric-value text-info">{prodStatus.total_production_target || 0}</div>
                        <div className="metric-label">Target Total</div>
                      </div>
                    </div>
                    <div className="col-6">
                      <div className="metric-card">
                        <div className="metric-value text-warning">{prodStatus.remaining_orders || 0}</div>
                        <div className="metric-label">Orders Tersisa</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="status-card mb-3">
                    <strong>Status: </strong>{prodStatus.status || 'Tidak diketahui'}
                  </div>
                  
                  {prodStatus.production_progress !== undefined && (
                    <div className="mb-3">
                      <div className="d-flex justify-content-between small mb-1">
                        <span>Progress Produksi</span>
                        <span>{prodStatus.production_progress.toFixed(1)}%</span>
                      </div>
                      <div className="progress progress-modern">
                        <div className="progress-bar bg-primary" role="progressbar" 
                             style={{width: `${prodStatus.production_progress}%`}} 
                             aria-valuenow={prodStatus.production_progress} 
                             aria-valuemin="0" aria-valuemax="100"></div>
                      </div>
                    </div>
                  )}

                  {/* Detail per line */}
                  <div className="mt-4">
                    <h6 className="mb-3"><i className="fas fa-industry"></i> Status Per Line Produksi</h6>
                    {prodStatus.lines && Object.keys(prodStatus.lines).map((lineName) => {
                      const line = prodStatus.lines[lineName];
                      return (
                        <div key={lineName} className="line-card mb-4 p-3 border rounded">
                          <div className="d-flex justify-content-between align-items-center mb-3">
                            <h5 className="mb-0"><i className="fas fa-stream text-primary"></i> Line {lineName}</h5>
                            <div className="d-flex gap-2">
                              <span className={`badge ${line.status === 'running' ? 'bg-success' : 'bg-secondary'}`}>
                                {line.status}
                              </span>
                              <span className="badge bg-info">
                                Target: {line.total_line_target}
                              </span>
                              <span className="badge bg-warning">
                                Tersisa: {line.remaining_orders}
                              </span>
                            </div>
                          </div>

                          {/* Produk yang sedang diproses */}
                          {line.current_processing_products && line.current_processing_products.length > 0 && (
                            <div className="mb-3">
                              <h6 className="mb-2"><i className="fas fa-cogs text-primary"></i> Produk Sedang Diproses</h6>
                              <div className="row">
                                {line.current_processing_products.map((product, idx) => (
                                  <div className="col-md-6 mb-2" key={idx}>
                                    <div className="product-card p-2 border rounded bg-light">
                                      <div className="d-flex justify-content-between align-items-center mb-1">
                                        <strong className="small">{product.part_no}</strong>
                                        <span className="badge bg-info">{product.progress}%</span>
                                      </div>
                                      <div className="small text-muted mb-1">Model: {product.model}</div>
                                      <div className="progress progress-modern">
                                        <div className="progress-bar bg-primary" role="progressbar"
                                             style={{width: `${product.progress}%`}}
                                             aria-valuenow={product.progress}
                                             aria-valuemin="0" aria-valuemax="100"></div>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Proses dalam line ini */}
                          <div className="row">
                            {line.processes && Object.keys(line.processes).map((procName) => {
                              const p = line.processes[procName];
                              return (
                                <div className="col-md-6 mb-3" key={procName}>
                                  <div className="process-card p-2 border rounded bg-light">
                                    <div className="d-flex justify-content-between align-items-center mb-2">
                                      <strong>{p.name}</strong>
                                      <span className="badge bg-primary">{p.num_operators} opr</span>
                                    </div>
                                    <div className="small text-muted mb-1">
                                      Queue In: {p.queue_in} | Queue Out: {p.queue_out}
                                    </div>
                                    <div className="small text-muted mb-1">
                                      Stock: {p.stock ? Object.keys(p.stock).length : 0} item(s)
                                    </div>
                                    {p.pending_requests && p.pending_requests.length > 0 && (
                                      <div className="small text-warning mb-1">
                                        <i className="fas fa-exclamation-triangle"></i> Waiting for: {p.pending_requests.join(', ')}
                                      </div>
                                    )}
                                    {p.is_waiting_for_material && (
                                      <div className="small text-danger mb-1">
                                        <i className="fas fa-clock"></i> Waiting for materials
                                      </div>
                                    )}
                                    {p.materials_waiting_for && p.materials_waiting_for.length > 0 && (
                                      <div className="small text-info mb-1">
                                        <i className="fas fa-list"></i> Materials needed: {p.materials_waiting_for.map(m => `${m.material} (${m.needed})`).join(', ')}
                                      </div>
                                    )}

                                    {/* Units in process */}
                                    {p.units_in_process && p.units_in_process.length > 0 && (
                                      <div className="mt-2">
                                        <div className="small fw-bold mb-1">Units in Process:</div>
                                        {p.units_in_process.map((u, idx) => (
                                          <div className="mb-2" key={idx}>
                                            <div className="d-flex justify-content-between small mb-1">
                                              <span>Part: {u.part_no || 'Unknown'} | Model: {u.model || 'Unknown'}</span>
                                              <span>{u.progress || 0}%</span>
                                            </div>
                                            <div className="progress progress-modern">
                                              <div className="progress-bar" role="progressbar"
                                                   style={{width: `${u.progress || 0}%`}}
                                                   aria-valuenow={u.progress || 0}
                                                   aria-valuemin="0" aria-valuemax="100"></div>
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <p className="text-muted">Menunggu data status...</p>
              )}
            </div>
          </div>
          
          <div className="col-md-6">
            <div className="simulation-card p-3">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h5 className="mb-0"><i className="fas fa-truck text-success"></i> Status Logistik</h5>
                <div className="d-flex gap-2">
                  {isPaused ? (
                    <button className="btn btn-sm btn-success" onClick={handleResume}>
                      <i className="fas fa-play"></i> Resume
                    </button>
                  ) : (
                    <button className="btn btn-sm btn-warning" onClick={handlePause}>
                      <i className="fas fa-pause"></i> Pause
                    </button>
                  )}
                  <div className="btn-group" role="group">
                    <button className="btn btn-sm btn-outline-secondary" onClick={() => handleSetSpeed(0.5)}>0.5x</button>
                    <button className="btn btn-sm btn-outline-secondary" onClick={() => handleSetSpeed(1.0)}>1x</button>
                    <button className="btn btn-sm btn-outline-secondary" onClick={() => handleSetSpeed(2.0)}>2x</button>
                  </div>
                  <span className="badge bg-info">Speed: {simulationSpeed}x</span>
                </div>
              </div>
              {logStatus ? (
                <div>
                  <div className="row mb-3">
                    <div className="col-4">
                      <div className="metric-card">
                    <div className="metric-value text-success">{logStatus.completed_tasks_count || 0}</div>
                    <div className="metric-label">Task Selesai</div>
                  </div>
                    </div>
                    <div className="col-4">
                      <div className="metric-card">
                    <div className="metric-value text-warning">{logStatus.remaining_tasks_count || 0}</div>
                    <div className="metric-label">Task Tersisa</div>
                      </div>
                    </div>
                    <div className="col-4">
                      <div className="metric-card">
                        <div className="metric-value text-info">{logStatus.in_progress_tasks_count || 0}</div>
                        <div className="metric-label">Sedang Berjalan</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="status-card mb-3">
                    <strong>Status: </strong>{logStatus.status || 'Tidak diketahui'}
                  </div>
                  
                  {logStatus.material_requests_pending !== undefined && (
                    <div className="small text-muted mb-2">
                      <i className="fas fa-list"></i> Material Requests Pending: {logStatus.material_requests_pending}
                    </div>
                  )}
                  
                  {logStatus.mrp_data_loaded && (
                    <div className="small text-success mb-2">
                      <i className="fas fa-check-circle"></i> MRP Data Loaded ({logStatus.mrp_materials_count} materials)
                    </div>
                  )}

                  {/* Transport Units */}
                  <div className="mt-4">
                    <h6 className="mb-2"><i className="fas fa-shipping-fast"></i> Transport Unit</h6>
                    <div className="row">
                      {logStatus.transport_units && logStatus.transport_units.map((u) => (
                        <div className="col-md-6 mb-2" key={u.name}>
                          <div className="process-card p-2">
                            <div className="d-flex justify-content-between align-items-center mb-1">
                              <strong>{u.name}</strong>
                              <span className={`badge ${u.status === 'idle' ? 'bg-secondary' : 'bg-success'}`}>{u.status}</span>
                            </div>
                            <div className="small text-muted mb-1">Tipe: {u.type} | Lokasi: {u.current_location || '-'}</div>
                            {u.current_task ? (
                              <div className="small text-muted mb-1">
                                Task: {u.current_task.material} → {u.current_task.destination}
                              </div>
                            ) : (
                              <div className="small text-muted mb-1">Task: Idle</div>
                            )}
                            {u.current_task && u.current_task.progress_percentage !== undefined && (
                              <div className="small text-muted mb-1">
                                Progress: {u.current_task.progress_percentage.toFixed(1)}%
                              </div>
                            )}
                            <div className="progress progress-modern">
                              <div className="progress-bar bg-success" role="progressbar" 
                                   style={{width: `${Math.min(100, u.current_task?.progress_percentage || u.progress || 0)}%`}} 
                                   aria-valuenow={u.current_task?.progress_percentage || u.progress || 0} 
                                   aria-valuemin="0" aria-valuemax="100"></div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Locations */}
                  <div className="mt-3">
                    <h6 className="mb-2"><i className="fas fa-map-marker-alt"></i> Lokasi</h6>
                    <div className="d-flex flex-wrap gap-2">
                      {logStatus.locations && logStatus.locations.map(l => (
                        <span className="badge bg-light text-dark" key={l.name}>{l.name}</span>
                      ))}
                    </div>
                  </div>

                  {/* Performance Metrics */}
                  {logStatus.performance_metrics && (
                    <div className="mt-3">
                      <h6 className="mb-2"><i className="fas fa-chart-line"></i> Performance Metrics</h6>
                      <div className="row">
                        <div className="col-6">
                          <div className="metric-card">
                            <div className="metric-value text-primary">{logStatus.performance_metrics.total_requests_processed || 0}</div>
                            <div className="metric-label">Requests Processed</div>
                          </div>
                        </div>
                        <div className="col-6">
                          <div className="metric-card">
                            <div className="metric-value text-success">{logStatus.performance_metrics.total_tasks_completed || 0}</div>
                            <div className="metric-label">Tasks Completed</div>
                          </div>
                        </div>
                        <div className="col-6">
                          <div className="metric-card">
                            <div className="metric-value text-info">{logStatus.performance_metrics.average_processing_time ? logStatus.performance_metrics.average_processing_time.toFixed(2) : 0}</div>
                            <div className="metric-label">Avg Processing Time (s)</div>
                          </div>
                        </div>
                        <div className="col-6">
                          <div className="metric-card">
                            <div className="metric-value text-warning">{logStatus.performance_metrics.throughput ? logStatus.performance_metrics.throughput.toFixed(2) : 0}</div>
                            <div className="metric-label">Throughput (tasks/time)</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Event Log */}
                  <div className="mt-3">
                    <h6 className="mb-2"><i className="fas fa-list"></i> Event Log</h6>
                    <div className="status-card" style={{maxHeight: 200, overflowY: 'auto'}}>
                      {(logStatus.event_log || []).slice().reverse().map((e, idx) => (
                        <div key={idx} className="small">{e}</div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-muted">Menunggu data status...</p>
              )}
            </div>
          </div>
      </div>
      )}
      
      
    </div>
  );
}

export default IntegratedSimulationView;