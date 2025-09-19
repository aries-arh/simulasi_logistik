import React, { useState, useEffect, memo } from 'react';
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

// Register Chart.js components
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

const UnitProgressBar = memo(({ progress }) => (
  <div className="progress" style={{ height: '10px', margin: '2px 0', backgroundColor: '#e9ecef' }}>
    <div
      className="progress-bar bg-info"
      role="progressbar"
      style={{ width: `${progress}%` }}
      aria-valuenow={progress}
      aria-valuemin="0"
      aria-valuemax="100"
    ></div>
  </div>
));

const MaterialsWaiting = memo(({ materials }) => {
    if (!materials || materials.length === 0) {
        return null;
    }
    return (
        <div className="materials-waiting-card">
            <strong className="text-warning"><i className="fas fa-pause-circle"></i> Menunggu Material:</strong>
            <ul className="list-unstyled mb-0 mt-1 small">
                {materials.map((item, index) => (
                    <li key={index}>{item.material} (Butuh: {item.needed})</li>
                ))}
            </ul>
        </div>
    );
});

const ProcessCard = memo(({ processData }) => (
  <div className="process-card h-100">
    <h6 className="mb-3 text-primary">
      <i className="fas fa-cog"></i> {processData.name}
    </h6>
    <div className="row text-center mb-3">
      <div className="col-6">
        <div className="metric-value text-info">{processData.queue_in}</div>
        <div className="metric-label">Antri Masuk</div>
      </div>
      <div className="col-6">
        <div className="metric-value text-warning">{processData.queue_out}</div>
        <div className="metric-label">Antri Keluar</div>
      </div>
    </div>
    <div className="border-top pt-3">
      <div className="mb-2">
        <span className="h6 text-secondary">Dalam Proses</span>
        <small className="d-block text-muted">
          {processData.units_in_process.length} / {processData.num_operators} Operator
        </small>
      </div>
      <div className="mb-2" style={{minHeight: '30px'}}>
        {processData.units_in_process.map((unit, unitIndex) => (
          <UnitProgressBar key={unitIndex} progress={unit.progress} />
        ))}
      </div>
      {processData.is_waiting_for_material && 
        <MaterialsWaiting materials={processData.materials_waiting_for} />
      }
    </div>
  </div>
));

const ProductionLine = memo(({ lineName, lineData }) => (
    <div className="line-card card mb-4">
        <div className="card-header d-flex justify-content-between align-items-center">
            <h4 className="mb-0"><i className="fas fa-industry"></i> Lini Produksi: {lineName}</h4>
            <span className={`badge bg-${lineData.status === 'running' ? 'success' : 'warning'}`}>
                {lineData.status}
            </span>
        </div>
        <div className="card-body">
            <div className="row">
                {Object.values(lineData.processes).map(processData => (
                    <div key={processData.name} className="col-md-6 mb-4">
                        <ProcessCard processData={processData} />
                    </div>
                ))}
            </div>
        </div>
    </div>
));

const ProductionSimulationDisplay = ({ config, onBack }) => {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const [historyData, setHistoryData] = useState([]);

  useEffect(() => {
    let intervalId;

    const startSimulation = async () => {
      try {
        setError('');
        // Menggunakan file yang dipilih dalam config
        const runConfig = {
            ...config,
            schedule_file: config.scheduleFile, // pastikan nama field sesuai dengan yang diharapkan backend
            bom_file: config.bomFile
        };
        await axios.post(`${API_URL}/production/run`, runConfig);
        fetchStatus();
        intervalId = setInterval(fetchStatus, 1000);
      } catch (err) {
        console.error("Gagal memulai simulasi:", err);
        const errorMsg = err.response?.data?.detail ? JSON.stringify(err.response.data.detail) : 'Pastikan server backend berjalan dan file yang dipilih valid.';
        setError(`Gagal memulai simulasi: ${errorMsg}`);
      }
    };

    const fetchStatus = async () => {
      try {
        const response = await axios.get(`${API_URL}/production/status`);
        const newStatus = response.data;
        setStatus(newStatus);

        // Kumpulkan data untuk grafik
        setHistoryData(prev => {
            const newHistory = [...prev, {
                time: newStatus.current_time,
                completed_units: newStatus.completed_units,
                scrapped_units: newStatus.scrapped_units,
            }];
            // Batasi history untuk performa
            return newHistory.slice(-300);
        });

        if (newStatus.status === 'finished') {
          clearInterval(intervalId);
        }
      } catch (err) {
        console.error("Gagal mengambil status:", err);
        setError('Gagal mengambil status simulasi dari server.');
        clearInterval(intervalId);
      }
    };

    startSimulation();

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
        // Minta server untuk menghentikan simulasi saat komponen di-unmount
        axios.post(`${API_URL}/production/stop`).catch(err => console.error("Gagal menghentikan simulasi:", err));
      }
    };
  }, [config]);

  if (error) {
    return (
      <div className="alert alert-danger">
        <p>{error}</p>
        <button onClick={onBack} className="btn btn-secondary">Kembali</button>
      </div>
    );
  }

  if (!status) {
    return <div className="alert alert-info">Menyiapkan simulasi, mohon tunggu...</div>;
  }

  const totalTarget = status.total_production_target;
  const completedUnits = status.completed_units;
  const scrappedUnits = status.scrapped_units;
  const totalProcessed = completedUnits + scrappedUnits;
  const progress = totalTarget > 0 ? (totalProcessed / totalTarget) * 100 : 0;

  const chartData = {
    labels: historyData.map(data => data.time),
    datasets: [
      {
        label: 'Unit Selesai (OK)',
        data: historyData.map(data => data.completed_units),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        tension: 0.1,
      },
      {
        label: 'Unit Gagal (NG)',
        data: historyData.map(data => data.scrapped_units),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
        tension: 0.1,
      },
    ],
  };

  return (
    <div className="simulation-card p-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="mb-0">
          <i className="fas fa-cogs text-primary"></i> Simulasi Produksi Berjalan
          <span className="badge bg-primary ms-2">{status.status}</span>
        </h2>
        <button onClick={onBack} className="btn btn-modern btn-secondary-modern">
          <i className="fas fa-stop"></i> Hentikan & Kembali
        </button>
      </div>
      
      <div className="row text-center mb-4">
          <div className="col-md-4">
            <div className="metric-card h-100">
              <div className="metric-label">PROGRES TOTAL</div>
              <div className="metric-value text-primary">{totalProcessed} / {totalTarget}</div>
              <div className="progress-modern mt-3">
                <div className="progress-bar-modern" role="progressbar" style={{width: `${progress}%`}}></div>
              </div>
            </div>
          </div>
          <div className="col-md-4">
            <div className="metric-card h-100">
              <div className="metric-label">UNIT SELESAI (OK)</div>
              <div className="metric-value text-success">{completedUnits}</div>
            </div>
          </div>
          <div className="col-md-4">
            <div className="metric-card h-100">
              <div className="metric-label">UNIT GAGAL (NG)</div>
              <div className="metric-value text-danger">{scrappedUnits}</div>
            </div>
          </div>
        </div>

      <hr />

      {status.lines && Object.entries(status.lines).map(([lineName, lineData]) => (
          <ProductionLine key={lineName} lineName={lineName} lineData={lineData} />
      ))}

      <hr />

      <h4 className="text-center mb-4">
        <i className="fas fa-chart-line text-primary"></i> Grafik Hasil Simulasi
      </h4>
      <div className="chart-container">
        <h5><i className="fas fa-check-circle text-success"></i> Output Produksi & Gagal (Kumulatif)</h5>
        <Line data={chartData} />
      </div>
    </div>
  );
};

export default ProductionSimulationDisplay;
