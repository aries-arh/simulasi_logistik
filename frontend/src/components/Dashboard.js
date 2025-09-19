import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

function Dashboard({ onBack }) {
  const [systemStatus, setSystemStatus] = useState({
    production: null,
    logistics: null,
    loading: true,
    error: null
  });

  const [stats, setStats] = useState({
    totalSimulations: 0,
    activeSimulations: 0,
    completedToday: 0,
    avgEfficiency: 0
  });

  useEffect(() => {
    fetchSystemStatus();
    fetchStats();
    
    // Poll for updates every 5 seconds
    const interval = setInterval(() => {
      fetchSystemStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const fetchSystemStatus = async () => {
    try {
      const [prodRes, logRes] = await Promise.all([
        axios.get(`${API_URL}/production/status`),
        axios.get(`${API_URL}/logistics/status`)
      ]);
      
      setSystemStatus({
        production: prodRes.data,
        logistics: logRes.data,
        loading: false,
        error: null
      });
    } catch (err) {
      setSystemStatus(prev => ({
        ...prev,
        loading: false,
        error: 'Gagal mengambil status sistem'
      }));
    }
  };

  const fetchStats = async () => {
    try {
      // Mock data for now - in real implementation, these would come from API
      setStats({
        totalSimulations: 15,
        activeSimulations: systemStatus.production?.status === 'running' || systemStatus.logistics?.status === 'running' ? 1 : 0,
        completedToday: 8,
        avgEfficiency: 87.5
      });
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'success';
      case 'finished': return 'info';
      case 'error': return 'danger';
      default: return 'secondary';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running': return 'fa-play-circle';
      case 'finished': return 'fa-check-circle';
      case 'error': return 'fa-exclamation-triangle';
      default: return 'fa-pause-circle';
    }
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2><i className="fas fa-tachometer-alt"></i> Dashboard Sistem</h2>
        <button onClick={onBack} className="btn btn-modern btn-secondary-modern">
          <i className="fas fa-arrow-left"></i> Kembali
        </button>
      </div>

      {/* Statistics Cards */}
      <div className="row mb-4">
        <div className="col-md-3 mb-3">
          <div className="metric-card">
            <div className="metric-value text-primary">{stats.totalSimulations}</div>
            <div className="metric-label">Total Simulasi</div>
          </div>
        </div>
        <div className="col-md-3 mb-3">
          <div className="metric-card">
            <div className="metric-value text-success">{stats.activeSimulations}</div>
            <div className="metric-label">Simulasi Aktif</div>
          </div>
        </div>
        <div className="col-md-3 mb-3">
          <div className="metric-card">
            <div className="metric-value text-info">{stats.completedToday}</div>
            <div className="metric-label">Selesai Hari Ini</div>
          </div>
        </div>
        <div className="col-md-3 mb-3">
          <div className="metric-card">
            <div className="metric-value text-warning">{stats.avgEfficiency}%</div>
            <div className="metric-label">Efisiensi Rata-rata</div>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="row">
        <div className="col-md-6 mb-4">
          <div className="simulation-card p-4">
            <h5 className="mb-3">
              <i className="fas fa-cogs text-primary"></i> Status Produksi
            </h5>
            {systemStatus.loading ? (
              <div className="text-center">
                <div className="loading-spinner"></div>
                <p className="mt-2">Memuat status...</p>
              </div>
            ) : systemStatus.error ? (
              <div className="alert alert-modern alert-danger-modern">
                <i className="fas fa-exclamation-triangle"></i> {systemStatus.error}
              </div>
            ) : systemStatus.production ? (
              <div>
                <div className="status-card mb-3">
                  <div className="d-flex justify-content-between align-items-center">
                    <span><i className={`fas ${getStatusIcon(systemStatus.production.status)}`}></i> Status</span>
                    <span className={`badge bg-${getStatusColor(systemStatus.production.status)}`}>
                      {systemStatus.production.status}
                    </span>
                  </div>
                </div>
                <div className="row text-center">
                  <div className="col-6">
                    <div className="metric-value text-success">{systemStatus.production.completed_units || 0}</div>
                    <div className="metric-label">Unit Selesai</div>
                  </div>
                  <div className="col-6">
                    <div className="metric-value text-danger">{systemStatus.production.scrapped_units || 0}</div>
                    <div className="metric-label">Unit Gagal</div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-muted">Tidak ada data produksi</p>
            )}
          </div>
        </div>

        <div className="col-md-6 mb-4">
          <div className="simulation-card p-4">
            <h5 className="mb-3">
              <i className="fas fa-truck text-success"></i> Status Logistik
            </h5>
            {systemStatus.loading ? (
              <div className="text-center">
                <div className="loading-spinner"></div>
                <p className="mt-2">Memuat status...</p>
              </div>
            ) : systemStatus.error ? (
              <div className="alert alert-modern alert-danger-modern">
                <i className="fas fa-exclamation-triangle"></i> {systemStatus.error}
              </div>
            ) : systemStatus.logistics ? (
              <div>
                <div className="status-card mb-3">
                  <div className="d-flex justify-content-between align-items-center">
                    <span><i className={`fas ${getStatusIcon(systemStatus.logistics.status)}`}></i> Status</span>
                    <span className={`badge bg-${getStatusColor(systemStatus.logistics.status)}`}>
                      {systemStatus.logistics.status}
                    </span>
                  </div>
                </div>
                <div className="row text-center">
                  <div className="col-6">
                    <div className="metric-value text-success">{systemStatus.logistics.completed_tasks_count || 0}</div>
                    <div className="metric-label">Task Selesai</div>
                  </div>
                  <div className="col-6">
                    <div className="metric-value text-warning">{systemStatus.logistics.remaining_tasks_count || 0}</div>
                    <div className="metric-label">Task Tersisa</div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-muted">Tidak ada data logistik</p>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="simulation-card p-4">
        <h5 className="mb-3"><i className="fas fa-bolt text-warning"></i> Aksi Cepat</h5>
        <div className="row">
          <div className="col-md-3 mb-2">
            <button className="btn btn-modern btn-primary-modern w-100">
              <i className="fas fa-play"></i> Mulai Simulasi Baru
            </button>
          </div>
          <div className="col-md-3 mb-2">
            <button className="btn btn-modern btn-info-modern w-100">
              <i className="fas fa-chart-bar"></i> Lihat Laporan
            </button>
          </div>
          <div className="col-md-3 mb-2">
            <button className="btn btn-modern btn-success-modern w-100">
              <i className="fas fa-download"></i> Export Data
            </button>
          </div>
          <div className="col-md-3 mb-2">
            <button className="btn btn-modern btn-secondary-modern w-100">
              <i className="fas fa-cog"></i> Pengaturan
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
