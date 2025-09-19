import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

const LogisticsSetupForm = ({ onStart, initialData, onBack, onManageMasterData }) => {
  const [scenarioName, setScenarioName] = useState(initialData?.name || 'Scenario');
  const [locations, setLocations] = useState([]);
  const [transportUnits, setTransportUnits] = useState([]);
  const [tasks, setTasks] = useState([
    {
      origin: '',
      destination: '',
      distance: 100,
      travel_time: 60,
      loading_time: 15,
      unloading_time: 15,
      return_time: 60,
      transport_unit_names: [],
      unit_start_delay: 0,
    },
  ]);
  const [workdayTime, setWorkdayTime] = useState(28800);
  const [shifts, setShifts] = useState([{ start_time: 0, end_time: 28800 }]);
  const [scheduledEvents, setScheduledEvents] = useState([
    { name: 'Istirahat', start_time: 14400, duration: 3600, recurrence_rule: 'daily' },
  ]);
  const [abnormalityRate, setAbnormalityRate] = useState(0.01);
  const [abnormalityDuration, setAbnormalityDuration] = useState(300);
  const [selectedFile, setSelectedFile] = useState(null);
  const [masterLocations, setMasterLocations] = useState([]);
  const [masterTransportUnits, setMasterTransportUnits] = useState([]);
  const [loadingMasterData, setLoadingMasterData] = useState(true);
  const [masterDataError, setMasterDataError] = useState(null);

  useEffect(() => {
    const fetchMasterData = async () => {
      setLoadingMasterData(true);
      setMasterDataError(null);
      try {
        const locRes = await axios.get(`${API_URL}/master/locations/`);
        const unitRes = await axios.get(`${API_URL}/master/transport-units/`);
        setMasterLocations(locRes.data);
        setMasterTransportUnits(unitRes.data);
      } catch (err) {
        setMasterDataError(err.response?.data?.detail || err.message);
      } finally {
        setLoadingMasterData(false);
      }
    };
    fetchMasterData();
  }, []);

  useEffect(() => {
    if (initialData) {
      setScenarioName(initialData.name || 'Scenario');
      setLocations(initialData.locations ? initialData.locations.map(loc => ({...loc, stock: loc.stock || {}})) : []);
      setTransportUnits(initialData.transport_units || []);
      setTasks(initialData.tasks || []);
      setWorkdayTime(initialData.workday_end_time || 28800);
      setShifts(initialData.shifts || []);
      setScheduledEvents(initialData.scheduled_events || []);
      setAbnormalityRate(initialData.abnormality_rate || 0);
      setAbnormalityDuration(initialData.abnormality_duration || 0);
    }
  }, [initialData]);

  const handleLocationChange = (index, event) => {
    const { name, value } = event.target;
    const newLocations = [...locations];
    if (name === 'name') {
        const selectedMasterLocation = masterLocations.find(loc => loc.name === value);
        if (selectedMasterLocation) {
            newLocations[index] = { ...newLocations[index], name: selectedMasterLocation.name, stock: selectedMasterLocation.stock || {} };
        }
    } else {
        newLocations[index] = { ...newLocations[index], [name]: parseInt(value, 10) || 0 };
    }
    setLocations(newLocations);
  };
  const handleAddLocation = (e) => { e.preventDefault(); setLocations([...locations, { name: '', stock: {} }]); };
  const handleRemoveLocation = (index) => { const nl = [...locations]; nl.splice(index, 1); setLocations(nl); };
  const handleTransportUnitChange = (index, event) => {
    const { name, value } = event.target;
    const newUnits = [...transportUnits];
    if (name === 'name') {
        const selectedMasterUnit = masterTransportUnits.find(unit => unit.name === value);
        if (selectedMasterUnit) {
            newUnits[index] = { ...newUnits[index], name: selectedMasterUnit.name, type: selectedMasterUnit.type, num_sub_units: selectedMasterUnit.num_sub_units, capacity_per_sub_unit: selectedMasterUnit.capacity_per_sub_unit };
        }
    } else {
        newUnits[index] = { ...newUnits[index], [name]: parseInt(value, 10) || 1 };
    }
    setTransportUnits(newUnits);
  };
  const handleAddTransportUnit = (e) => { e.preventDefault(); setTransportUnits([...transportUnits, { name: '', type: '', num_sub_units: 1, capacity_per_sub_unit: 1 }]); };
  const handleRemoveTransportUnit = (index) => { const nu = [...transportUnits]; nu.splice(index, 1); setTransportUnits(nu); };
  const handleTaskChange = (index, event) => {
    const newTasks = [...tasks];
    const { name, value, options } = event.target;
    if (name === 'transport_unit_names') {
        newTasks[index][name] = Array.from(options).filter(o => o.selected).map(o => o.value);
    } else if (['distance', 'travel_time', 'loading_time', 'unloading_time', 'return_time', 'unit_start_delay'].includes(name)) {
      newTasks[index][name] = parseFloat(value) || 0;
    } else {
      newTasks[index][name] = value;
    }
    setTasks(newTasks);
  };
  const handleAddTask = (e) => { e.preventDefault(); setTasks([...tasks, { origin: '', destination: '', distance: 100, travel_time: 60, loading_time: 15, unloading_time: 15, return_time: 60, transport_unit_names: [], unit_start_delay: 0 }]); };
  const handleRemoveTask = (index) => { const nt = [...tasks]; nt.splice(index, 1); setTasks(nt); };
  const handleShiftChange = (index, event) => { const ns = [...shifts]; ns[index][event.target.name] = parseInt(event.target.value, 10) || 0; setShifts(ns); };
  const handleAddShift = (e) => { e.preventDefault(); setShifts([...shifts, { start_time: 0, end_time: 0 }]); };
  const handleRemoveShift = (index) => { const ns = [...shifts]; ns.splice(index, 1); setShifts(ns); };
  const handleEventChange = (index, event) => {
    const newEvents = [...scheduledEvents];
    const { name, value } = event.target;
    newEvents[index][name] = ['start_time', 'duration'].includes(name) ? parseInt(value, 10) || 0 : value;
    setScheduledEvents(newEvents);
  };
  const handleAddEvent = (e) => { e.preventDefault(); setScheduledEvents([...scheduledEvents, { name: '', start_time: 0, duration: 1, recurrence_rule: 'none' }]); };
  const handleRemoveEvent = (index) => { const ne = [...scheduledEvents]; ne.splice(index, 1); setScheduledEvents(ne); };

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  const getCurrentConfig = () => ({
    name: scenarioName,
    locations: locations.map(loc => ({
        name: loc.name,
        stock: loc.stock && typeof loc.stock === 'object' ? loc.stock : {}
    })),
    transport_units: transportUnits,
    tasks: tasks.map(task => ({
        origin: task.origin,
        destination: task.destination,
        distance: task.distance,
        travel_time: task.travel_time,
        loading_time: task.loading_time,
        unloading_time: task.unloading_time,
        return_time: task.return_time,
        transport_unit_names: task.transport_unit_names,
        unit_start_delay: task.unit_start_delay,
    })),
    workday_start_time: 0,
    workday_end_time: workdayTime,
    shifts,
    scheduled_events: scheduledEvents,
    abnormality_rate: abnormalityRate,
    abnormality_duration: abnormalityDuration,
  });

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selectedFile) {
      alert("Validasi Gagal: Mohon unggah file data material (Excel atau CSV).");
      return;
    }
    if (!tasks || tasks.length === 0) {
        alert("Validasi Gagal: Setidaknya harus ada satu tugas yang dikonfigurasi.");
        return;
    }
    for (const task of tasks) {
      if (!task.transport_unit_names || task.transport_unit_names.length === 0) {
        alert(`Validasi Gagal: Setiap tugas harus memiliki setidaknya satu unit transportasi.`);
        return;
      }
    }

    const config = getCurrentConfig();
    const formData = new FormData();
    formData.append('material_data', selectedFile);
    formData.append('setup_data', JSON.stringify(config));

    try {
      const response = await axios.post(`${API_URL}/logistics/run-with-comparison`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      alert("Simulasi berhasil dimulai dengan data yang telah disesuaikan!");
      onStart(response.data.adjusted_setup, response.data.comparison_data);

    } catch (err) {
      alert(`Error: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleSave = async () => {
    const name = window.prompt("Masukkan nama untuk skenario ini:", scenarioName);
    if (!name) return;
    const payload = { name, description: '', config_data: JSON.stringify(getCurrentConfig()) };
    try {
      await axios.post(`${API_URL}/setups/logistics/`, payload);
      alert(`Skenario '${name}' berhasil disimpan!`);
    } catch (err) {
      alert(err.response?.data?.detail || err.message);
    }
  };

  return (
    <div className="card shadow-sm">
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h2 className="card-title">Konfigurasi Simulasi Logistik</h2>
          <button className="btn btn-secondary" onClick={onBack}>Kembali ke Menu</button>
        </div>

        {masterDataError && <div className="alert alert-danger">{masterDataError}</div>}
        {loadingMasterData && <p>Memuat data master...</p>}

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="form-label">Nama Skenario</label>
            <input type="text" className="form-control" value={scenarioName} onChange={(e) => setScenarioName(e.target.value)} />
          </div>

          <h4>Parameter Simulasi</h4>
          <div className="row">
            <div className="col-md-4 mb-3">
              <label className="form-label">Waktu Kerja (detik)</label>
              <input type="number" className="form-control" value={workdayTime} onChange={(e) => setWorkdayTime(parseInt(e.target.value))}/>
            </div>
            <div className="col-md-4 mb-3">
              <label className="form-label">Rate Abnormalitas (0-1)</label>
              <input type="number" step="0.01" className="form-control" value={abnormalityRate} onChange={(e) => setAbnormalityRate(parseFloat(e.target.value))}/>
            </div>
            <div className="col-md-6 mb-3">
              <label className="form-label">Durasi Abnormalitas (detik)</label>
              <input type="number" className="form-control" value={abnormalityDuration} onChange={(e) => setAbnormalityDuration(parseInt(e.target.value))}/>
            </div>
          </div>

          <h4>Unggah Data Material (Excel atau CSV)</h4>
          <div className="mb-3">
            <label className="form-label">File Data Material (Origin)</label>
            <input type="file" className="form-control" onChange={handleFileChange} accept=".xlsx, .xls, .csv" required />
            <div className="form-text">File ini akan dibandingkan dengan data lot dari server untuk menentukan jumlah pengiriman.</div>
          </div>

          <h4>Shift Kerja</h4>
          {shifts.map((shift, index) => (
            <div key={index} className="row mb-2">
              <div className="col">
                <input type="number" className="form-control" name="start_time" value={shift.start_time} onChange={(e) => handleShiftChange(index, e)} placeholder="Waktu Mulai Shift" />
              </div>
              <div className="col">
                <input type="number" className="form-control" name="end_time" value={shift.end_time} onChange={(e) => handleShiftChange(index, e)} placeholder="Waktu Selesai Shift" />
              </div>
              <div className="col-auto">
                <button type="button" className="btn btn-danger" onClick={() => handleRemoveShift(index)}>Hapus</button>
              </div>
            </div>
          ))}
          <button type="button" className="btn btn-secondary mb-3" onClick={handleAddShift}>+ Tambah Shift</button>

          <h4>Jadwal Kegiatan</h4>
          {scheduledEvents.map((event, index) => (
            <div key={index} className="p-3 mb-3 border rounded bg-light">
              <h5>Kegiatan #{index + 1}</h5>
              <div className="row">
                <div className="col-md-6 mb-2"><label className="form-label">Nama</label><input type="text" className="form-control" name="name" value={event.name} onChange={(e) => handleEventChange(index, e)} /></div>
                <div className="col-md-6 mb-2"><label className="form-label">Durasi (detik)</label><input type="number" className="form-control" name="duration" value={event.duration} onChange={(e) => handleEventChange(index, e)} /></div>
                <div className="col-md-6 mb-2"><label className="form-label">Perulangan</label><select className="form-control" name="recurrence_rule" value={event.recurrence_rule} onChange={(e) => handleEventChange(index, e)}><option value="none">Tidak</option><option value="daily">Harian</option></select></div>
              </div>
              <button type="button" className="btn btn-sm btn-danger mt-2" onClick={() => handleRemoveEvent(index)}>Hapus</button>
            </div>
          ))}
          <button type="button" className="btn btn-info w-100 mb-3" onClick={handleAddEvent}>+ Tambah Kegiatan</button>

          <div className="d-flex justify-content-between align-items-center mb-3">
            <h4>Lokasi</h4>
            <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => onManageMasterData('master_locations')}>Kelola Master</button>
          </div>
          {locations.map((location, index) => (
            <div key={index} className="row mb-2 align-items-center">
              <div className="col"><select className="form-control" name="name" value={location.name} onChange={(e) => handleLocationChange(index, e)}><option value="">Pilih Lokasi</option>{masterLocations.map(ml => <option key={ml.id} value={ml.name}>{ml.name}</option>)}</select></div>
              <div className="col-auto"><button type="button" className="btn btn-danger" onClick={() => handleRemoveLocation(index)}>Hapus</button></div>
            </div>
          ))}
          <button type="button" className="btn btn-secondary mb-3" onClick={handleAddLocation}>+ Tambah Lokasi</button>

          <div className="d-flex justify-content-between align-items-center mb-3">
            <h4>Unit Transportasi</h4>
            <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => onManageMasterData('master_transport_units')}>Kelola Master</button>
          </div>
          {transportUnits.map((unit, index) => (
            <div key={index} className="p-3 mb-3 border rounded bg-light">
              <h5>Unit #{index + 1}</h5>
              <div className="row">
                <div className="col-md-6 mb-2"><label>Pilih Unit</label><select className="form-control" name="name" value={unit.name} onChange={(e) => handleTransportUnitChange(index, e)}><option value="">Pilih</option>{masterTransportUnits.map(mtu => <option key={mtu.id} value={mtu.name}>{mtu.name}</option>)}</select></div>
                <div className="col-md-6 mb-2"><label>Tipe</label><input type="text" className="form-control" value={unit.type || ''} readOnly /></div>
                <div className="col-md-6 mb-2"><label>Jml Sub-unit</label><input type="number" className="form-control" name="num_sub_units" value={unit.num_sub_units} onChange={(e) => handleTransportUnitChange(index, e)} /></div>
                <div className="col-md-6 mb-2"><label>Kapasitas/Sub-unit</label><input type="number" className="form-control" name="capacity_per_sub_unit" value={unit.capacity_per_sub_unit} onChange={(e) => handleTransportUnitChange(index, e)} /></div>
              </div>
              <button type="button" className="btn btn-sm btn-danger mt-2" onClick={() => handleRemoveTransportUnit(index)}>Hapus</button>
            </div>
          ))}
          <button type="button" className="btn btn-secondary mb-3" onClick={handleAddTransportUnit}>+ Tambah Unit</button>

          <h4>Tugas</h4>
          {tasks.map((task, index) => (
            <div key={index} className="p-3 mb-3 border rounded bg-light">
              <h5>Tugas #{index + 1}</h5>
              <div className="row">
                <div className="col-md-6 mb-2"><label>Asal</label><select className="form-control" name="origin" value={task.origin} onChange={(e) => handleTaskChange(index, e)} required><option value="">Pilih</option>{locations.map(l => <option key={l.name} value={l.name}>{l.name}</option>)}</select></div>
                <div className="col-md-6 mb-2"><label>Tujuan</label><select className="form-control" name="destination" value={task.destination} onChange={(e) => handleTaskChange(index, e)} required><option value="">Pilih</option>{locations.map(l => <option key={l.name} value={l.name}>{l.name}</option>)}</select></div>
                <div className="col-md-6 mb-2"><label>Jeda Antar Unit (detik)</label><input type="number" className="form-control" name="unit_start_delay" value={task.unit_start_delay} onChange={(e) => handleTaskChange(index, e)} /></div>
                <div className="col-md-12 mb-2"><label>Unit Transportasi</label><select multiple className="form-control" name="transport_unit_names" value={task.transport_unit_names} onChange={(e) => handleTaskChange(index, e)} required>{transportUnits.map(u => <option key={u.name} value={u.name}>{u.name}</option>)}</select></div>
                <div className="col-md-6 mb-2"><label>Jarak (m)</label><input type="number" className="form-control" name="distance" value={task.distance} onChange={(e) => handleTaskChange(index, e)} /></div>
                <div className="col-md-3 mb-2"><label>Waktu Loading (s)</label><input type="number" className="form-control" name="loading_time" value={task.loading_time} onChange={(e) => handleTaskChange(index, e)} /></div>
                <div className="col-md-3 mb-2"><label>Waktu Tempuh (s)</label><input type="number" className="form-control" name="travel_time" value={task.travel_time} onChange={(e) => handleTaskChange(index, e)} /></div>
                <div className="col-md-3 mb-2"><label>Waktu Unloading (s)</label><input type="number" className="form-control" name="unloading_time" value={task.unloading_time} onChange={(e) => handleTaskChange(index, e)} /></div>
                <div className="col-md-3 mb-2"><label>Waktu Kembali (s)</label><input type="number" className="form-control" name="return_time" value={task.return_time} onChange={(e) => handleTaskChange(index, e)} /></div>
              </div>
              <button type="button" className="btn btn-sm btn-danger mt-2" onClick={() => handleRemoveTask(index)}>Hapus Tugas</button>
            </div>
          ))}
          <button type="button" className="btn btn-info w-100 mb-3" onClick={handleAddTask}>+ Tambah Tugas</button>

          <div className="d-grid gap-2 mt-4">
            <button type="submit" className="btn btn-primary fw-bold">Mulai Simulasi dengan Perbandingan Data</button>
            <button type="button" className="btn btn-info" onClick={handleSave}>Simpan Skenario</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default LogisticsSetupForm;