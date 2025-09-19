import React, { useState, useEffect, useMemo, useRef } from 'react';
import axios from 'axios';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const API_URL = 'http://localhost:8000';

const transportIcons = {
  Kururu: '/scooter_orbit.png',
  Forklift: '📦',
  AGV: '🤖',
  Manual: '🚶',
};

const statusColors = {
  idle: 'secondary',
  loading: 'primary',
  traveling: 'success',
  unloading: 'info',
  returning: 'warning',
  charging: 'danger',
  abnormal: 'dark',
  on_break: 'light',
  off_shift: 'light',
  event: 'light',
  waiting_to_start: 'light',
};

const StockModal = ({ show, handleClose, location, comparisonData }) => {
  if (!show || !location) return null;

  const onModalDialogClick = (e) => e.stopPropagation();

  const backdropStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100vw',
    height: '100vh',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    zIndex: 1040,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  const dialogStyle = {
    backgroundColor: 'white',
    padding: '20px',
    borderRadius: '8px',
    zIndex: 1050,
    width: '90%',
    maxWidth: '800px',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
  };

  const headerStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid #dee2e6',
    paddingBottom: '1rem',
    flexShrink: 0,
  };

  const bodyStyle = {
    paddingTop: '1rem',
    overflowY: 'auto',
    flexGrow: 1,
  };

  const footerStyle = {
    borderTop: '1px solid #dee2e6',
    paddingTop: '1rem',
    textAlign: 'right',
    flexShrink: 0,
  };

  return (
    <div style={backdropStyle} onClick={handleClose}>
      <div style={dialogStyle} onClick={onModalDialogClick}>
        <div style={headerStyle}>
          <h5 className="modal-title">Detail Stok di {location.name}</h5>
          <button type="button" className="btn-close" onClick={handleClose} aria-label="Close"></button>
        </div>
        <div style={bodyStyle}>
          {Object.keys(location.stock).length > 0 ? (
            Object.keys(location.stock).map(materialName => {
              const stockDetails = comparisonData.filter(item => item['Material number'] === materialName);
              return (
                <div key={materialName} className="mb-4">
                  <h5>{materialName}</h5>
                  <p className="mb-1"><strong>Total Stok Saat Ini: {location.stock[materialName]}</strong></p>
                  {stockDetails.length > 0 ? (
                    <table className="table table-sm table-bordered">
                      <thead className="table-light">
                        <tr>
                          <th>Kebutuhan Awal (Req.)</th>
                          <th>Rounding Val.</th>
                          <th>Tujuan Asal (Rec.)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stockDetails.map((detail, index) => (
                          <tr key={index}>
                            <td>{detail['Reqmts qty']}</td>
                            <td>{detail['Rounding val.']}</td>
                            <td>{detail['Recipient']}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : <p className="text-muted fst-italic">Tidak ada rincian data permintaan untuk material ini.</p>}
                </div>
              )
            })
          ) : (
            <p>(Lokasi ini kosong)</p>
          )}
        </div>
        <div style={footerStyle}>
          <button type="button" className="btn btn-secondary" onClick={handleClose}>Tutup</button>
        </div>
      </div>
    </div>
  );
};

const LogisticsSimulationDisplay = ({ config, comparisonData, onBack }) => {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const [historyData, setHistoryData] = useState([]);
  const [eventLog, setEventLog] = useState([]);
  const eventLogRef = useRef(null);

  const [isPaused, setIsPaused] = useState(false);
  const [simulationSpeed, setSimulationSpeed] = useState(1.0);

  const [showStockModal, setShowStockModal] = useState(false);
  const [modalLocation, setModalLocation] = useState(null);

  const locationPositions = useMemo(() => {
    const positions = {};
    config.locations.forEach((location, index) => {
      positions[location.name] = {
        top: 50,
        left: 50 + index * 250,
      };
    });
    return positions;
  }, [config.locations]);

  useEffect(() => {
    const fetchStatus = () => {
      axios.get(`${API_URL}/logistics/status`)
        .then(response => {
          const newStatus = response.data;
          setStatus(newStatus);
          setEventLog(newStatus.event_log || []);
          setIsPaused(newStatus.is_paused);
          setSimulationSpeed(newStatus.simulation_speed);

          if (newStatus.status !== 'not_started') {
            setHistoryData(prev => [
              ...prev,
              {
                time: newStatus.current_time,
                completed_tasks_count: newStatus.completed_tasks_count,
                remaining_tasks_count: newStatus.remaining_tasks_count,
                completed_tasks_per_unit: newStatus.completed_tasks_per_unit
              }
            ]);
          }
        })
        .catch(err => {
          console.error("Gagal mengambil status:", err);
          setError('Gagal mengambil status simulasi dari server.');
        });
    };

    fetchStatus();

    let intervalId;
    if (status?.status !== 'finished') {
      const intervalDuration = isPaused ? 1000 : 1000 / simulationSpeed;
      intervalId = setInterval(fetchStatus, intervalDuration);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [config, isPaused, simulationSpeed, status?.status]);

  useEffect(() => {
    if (eventLogRef.current) {
      eventLogRef.current.scrollTop = eventLogRef.current.scrollHeight;
    }
  }, [eventLog]);

  const handlePauseToggle = async () => {
    const endpoint = isPaused ? '/logistics/resume' : '/logistics/pause';
    try {
      await axios.post(`${API_URL}${endpoint}`);
      setIsPaused(!isPaused);
    } catch (err) {
      console.error(`Gagal ${isPaused ? 'melanjutkan' : 'menjeda'} simulasi:`, err);
      setError("Gagal mengubah status simulasi.");
    }
  };

  const handleSpeedChange = async (newSpeed) => {
    try {
      await axios.post(`${API_URL}/logistics/speed`, { speed: newSpeed });
      setSimulationSpeed(newSpeed);
    } catch (err) {
      console.error("Gagal mengubah kecepatan simulasi:", err);
      setError("Gagal mengubah kecepatan simulasi.");
    }
  };
  
  const handleShowStockModal = (location) => {
    setModalLocation(location);
    setShowStockModal(true);
  };

  const handleCloseStockModal = () => {
    setShowStockModal(false);
    setModalLocation(null);
  };

  const getUnitPosition = (unit, index) => {
    const offset = index * 10;
    const defaultPosition = { top: 50 + offset, left: 50 + offset };

    if (!locationPositions || Object.keys(locationPositions).length === 0) return defaultPosition;

    const getSafePosition = (locationName) => {
      if (locationName && locationPositions[locationName]) return locationPositions[locationName];
      if (config.locations && config.locations.length > 0) return locationPositions[config.locations[0].name];
      return null;
    };

    let position = null;
    if (!unit.current_task || ['idle', 'charging', 'abnormal', 'on_break', 'off_shift', 'event', 'waiting_to_start'].includes(unit.status)) {
      position = getSafePosition(unit.current_location);
    } else {
      const originPos = getSafePosition(unit.current_task.origin);
      const destPos = getSafePosition(unit.current_task.destination);
      if (originPos && destPos) {
        let progress = 0;
        if (unit.status === 'traveling' && unit.current_task.travel_time > 0) {
          progress = Math.min(unit.progress / unit.current_task.travel_time, 1);
          position = { top: originPos.top + (destPos.top - originPos.top) * progress, left: originPos.left + (destPos.left - originPos.left) * progress };
        } else if (unit.status === 'returning' && unit.current_task.return_time > 0) {
          progress = Math.min(unit.progress / unit.current_task.return_time, 1);
          position = { top: destPos.top + (originPos.top - destPos.top) * progress, left: destPos.left + (originPos.left - destPos.left) * progress };
        } else {
          position = getSafePosition(unit.current_location);
        }
      }
    }

    if (!position) position = getSafePosition(unit.current_location);
    if (position) return { top: position.top + offset, left: position.left + offset };
    return defaultPosition;
  };

  const getTaskProgress = (unit) => {
    if (!unit.current_task || unit.status === 'idle') return 0;
    const task = unit.current_task;
    let totalDuration = 0, currentProgress = 0;
    switch (unit.status) {
      case 'loading': totalDuration = task.loading_time; currentProgress = unit.progress; break;
      case 'traveling': totalDuration = task.travel_time; currentProgress = unit.progress; break;
      case 'unloading': totalDuration = task.unloading_time; currentProgress = unit.progress; break;
      case 'returning': totalDuration = task.return_time; currentProgress = unit.progress; break;
      default: return 0;
    }
    if (totalDuration === 0) return 100;
    return Math.min((currentProgress / totalDuration) * 100, 100);
  };

  if (error) return <div className="alert alert-danger"><p>{error}</p><button onClick={onBack} className="btn btn-secondary">Kembali</button></div>;
  if (!status || status.status === 'not_started') return <div className="alert alert-info">Menyiapkan simulasi logistik, mohon tunggu...</div>;

  const formatTime = (seconds) => new Date(seconds * 1000).toISOString().substr(11, 8);

  const completedTasksChartData = { labels: historyData.map(data => data.time), datasets: [{ label: 'Tugas Selesai Kumulatif', data: historyData.map(data => data.completed_tasks_count), borderColor: 'rgb(75, 192, 192)', backgroundColor: 'rgba(75, 192, 192, 0.5)', tension: 0.1 }] };
  const remainingTasksChartData = { labels: historyData.map(data => data.time), datasets: [{ label: 'Tugas Tersisa', data: historyData.map(data => data.remaining_tasks_count), borderColor: 'rgb(255, 159, 64)', backgroundColor: 'rgba(255, 159, 64, 0.5)', tension: 0.1 }] };
  const completedTasksPerUnitChartData = { labels: historyData.map(data => data.time), datasets: Object.keys(status.transport_units).map((unitName, index) => ({ label: `Tugas Selesai ${unitName}`, data: historyData.map(data => data.completed_tasks_per_unit[unitName] || 0), borderColor: `hsl(${index * 60}, 70%, 50%)`, backgroundColor: `hsla(${index * 60}, 70%, 50%, 0.2)`, tension: 0.1 })) };

  return (
    <div className="card shadow-sm">
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-center flex-wrap">
          <h2 className="card-title mb-2 mb-md-0">Simulasi Logistik Berjalan ({status.status})</h2>
          <button onClick={onBack} className="btn btn-sm btn-outline-secondary">Hentikan & Kembali</button>
        </div>
        
        <div className="d-flex justify-content-between align-items-center flex-wrap my-2">
          <span>Waktu Simulasi: {formatTime(status.current_time)} / {formatTime(status.workday_end_time)}</span>
          <div className="d-flex align-items-center">
            <div className="btn-group btn-group-sm me-2" role="group">
              {[1, 2, 4, 8].map(speed => (
                <button key={speed} type="button" className={`btn ${simulationSpeed === speed ? 'btn-primary' : 'btn-outline-primary'}`} onClick={() => handleSpeedChange(speed)}>{speed}x</button>
              ))}
            </div>
            <button className={`btn btn-sm ${isPaused ? 'btn-success' : 'btn-warning'}`} onClick={handlePauseToggle}>
              {isPaused ? 'Lanjutkan' : 'Jeda'}
            </button>
          </div>
        </div>

        <hr/>
        <div className="row">
          <div className="col-lg-8 mb-3 mb-lg-0">
            <div style={{ position: 'relative', height: '300px', border: '1px solid #ccc', borderRadius: '5px', padding: '10px', overflow: 'hidden' }}>
              {status.locations && status.locations.map(location => (
                <div key={location.name} style={{ position: 'absolute', top: `${locationPositions[location.name].top}px`, left: `${locationPositions[location.name].left}px`, border: '1px solid black', padding: '10px', borderRadius: '5px', backgroundColor: '#f0f0f0', cursor: 'pointer' }} onClick={() => handleShowStockModal(location)}>
                  <div><strong>{location.name}</strong></div>
                  <ul className="list-unstyled mb-0" style={{ fontSize: '0.8rem'}}>{Object.keys(location.stock).length > 0 ? Object.entries(location.stock).slice(0, 3).map(([material, qty]) => <li key={material}>{material}: {qty}</li>) : <li>(Kosong)</li>}</ul>
                  {Object.keys(location.stock).length > 3 && <div style={{fontSize: '0.7rem', color: 'blue'}}>(Klik untuk detail)</div>}
                </div>
              ))}
              {Object.values(status.transport_units).map((unit, index) => {
                const position = getUnitPosition(unit, index);
                return (
                  <div key={unit.name} className={`p-1 rounded bg-${statusColors[unit.status]} text-white`} style={{ position: 'absolute', top: `${position.top}px`, left: `${position.left}px`, transition: 'top 0.5s, left 0.5s' }}>
                    {unit.type === 'Kururu' ? <img src={transportIcons[unit.type]} alt="Kururu" style={{ width: '2rem', height: '2rem' }} /> : <span style={{ fontSize: '2rem' }} title={`${unit.name} (${unit.status})`}>{transportIcons[unit.type]}</span>}
                  </div>
                );
              })}
            </div>
          </div>
          <div className="col-lg-4">
            <h4>Log Aktivitas</h4>
            <div ref={eventLogRef} className="border p-2 rounded" style={{ height: '300px', overflowY: 'scroll', backgroundColor: '#f8f9fa', fontSize: '0.8rem' }}>
              {eventLog.map((log, index) => <div key={index}>{log}</div>)}
            </div>
          </div>
        </div>

        <hr />
        <h4>Status Unit Transportasi</h4>
        <div className="row mt-2">
          {status && Object.values(status.transport_units).map(unit => (
            <div key={unit.name} className="col-md-6 col-lg-4 mb-3">
              <div className="card h-100">
                <div className="card-header d-flex justify-content-between align-items-center"><h6 className="mb-0">{unit.name} ({unit.type})</h6><span className={`badge bg-${statusColors[unit.status]}`}>{unit.status.replace('_', ' ')}</span></div>
                <div className="card-body" style={{ fontSize: '0.9rem' }}>
                  <p className="card-text mb-1"><strong>Muatan: </strong>{Object.keys(unit.current_load_carried_by_unit).length > 0 ? Object.entries(unit.current_load_carried_by_unit).map(([mat, qty]) => `${qty} lot ${mat}`) : 'Kosong'}</p>
                  <p className="card-text mb-2"><strong>Lokasi: </strong>{unit.current_location}</p>
                  <div className="progress" style={{ height: '20px' }}>
                    <div className={`progress-bar progress-bar-striped progress-bar-animated bg-${statusColors[unit.status]}`} role="progressbar" style={{ width: `${getTaskProgress(unit)}%` }} aria-valuenow={getTaskProgress(unit)} aria-valuemin="0" aria-valuemax="100">
                      {unit.status !== 'idle' ? `${Math.round(getTaskProgress(unit))}%` : 'Idle'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <hr />
        <div className="row text-center mt-4">
          <div className="col-md-6"><h4>Tugas Selesai</h4><p className="display-6 text-success">{status.completed_tasks_count}</p></div>
          <div className="col-md-6"><h4>Tugas Antri</h4><p className="display-6 text-warning">{status.remaining_tasks_count}</p></div>
        </div>

        <hr />
        <details>
          <summary style={{ cursor: 'pointer', fontWeight: 'bold', padding: '10px 0' }}>Tampilkan/Sembunyikan Grafik Hasil Simulasi</summary>
          <div className="row mt-3">
            <div className="col-md-6 mb-4"><h5>Tugas Selesai Kumulatif</h5><Line data={completedTasksChartData} /></div>
            <div className="col-md-6 mb-4"><h5>Tugas Tersisa</h5><Line data={remainingTasksChartData} /></div>
            <div className="col-md-12 mb-4"><h5>Tugas Selesai per Unit Transportasi</h5><Line data={completedTasksPerUnitChartData} /></div>
          </div>
        </details>

        <StockModal show={showStockModal} handleClose={handleCloseStockModal} location={modalLocation} comparisonData={comparisonData} />
      </div>
    </div>
  );
};

export default LogisticsSimulationDisplay;