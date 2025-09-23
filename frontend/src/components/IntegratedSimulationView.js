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
        onUploadSuccess(result.filename);
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
  
  const [scheduleFile, setScheduleFile] = useState('');
  const [bomFile, setBomFile] = useState('');
  const [mrpFile, setMrpFile] = useState('');

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

  const loadDataSummaries = useCallback(async (files) => {
    const { schedule, bom, mrp } = files;
    try {
      const [scheduleRes, mrpRes, bomRes] = await Promise.all([
        schedule ? fetch(`${API_URL}/data/schedule/summary?filename=${schedule}`) : Promise.resolve(null),
        mrp ? fetch(`${API_URL}/data/mrp/summary?filename=${mrp}`) : Promise.resolve(null),
        bom ? fetch(`${API_URL}/data/bom/summary?filename=${bom}`) : Promise.resolve(null)
      ]);
      
      if (scheduleRes && scheduleRes.ok) {
        const scheduleData = await scheduleRes.json();
        setDataSummary(prev => ({ ...prev, schedule: scheduleData }));
      }
      
      if (mrpRes && mrpRes.ok) {
        const mrpData = await mrpRes.json();
        setDataSummary(prev => ({ ...prev, mrp: mrpData }));
      }
      
      if (bomRes && bomRes.ok) {
        const bomData = await bomRes.json();
        setDataSummary(prev => ({ ...prev, bom: bomData }));
      }
    } catch (err) {
      console.error('Error loading data summaries:', err);
    }
  }, []);

  const handleScheduleUpload = (filename) => {
    setScheduleFile(filename);
    loadDataSummaries({ schedule: filename, bom: bomFile, mrp: mrpFile });
  };

  const handleBomUpload = (filename) => {
    setBomFile(filename);
    loadDataSummaries({ schedule: scheduleFile, bom: filename, mrp: mrpFile });
  };

  const handleMrpUpload = (filename) => {
    setMrpFile(filename);
    loadDataSummaries({ schedule: scheduleFile, bom: bomFile, mrp: filename });
  };

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
    loadDataSummaries({ schedule: scheduleFile, bom: bomFile, mrp: mrpFile });
  }, [loadDataSummaries, scheduleFile, bomFile, mrpFile]);

  // ... (rest of the component is the same)
}

export default IntegratedSimulationView;