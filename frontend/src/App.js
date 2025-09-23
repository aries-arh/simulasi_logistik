import React, { useState } from 'react';
import ProductionSetupForm from './components/ProductionSetupForm';
import ProductionSimulationDisplay from './components/ProductionSimulationDisplay';
import LogisticsSetupForm from './components/LogisticsSetupForm';
import LogisticsSimulationDisplay from './components/LogisticsSimulationDisplay';
import ScenarioManager from './components/ScenarioManager';
import IntegratedSimulationView from './components/IntegratedSimulationView';
import Dashboard from './components/Dashboard';

function App() {
  const [mainView, setMainView] = useState('selection'); // Controls the main view: 'selection', 'dashboard', 'production_setup', 'logistics_setup', 'scenario_manager', 'integrated_simulation', 'production_display', 'logistics_display'
  const [simulationConfig, setSimulationConfig] = useState(null);
  const [initialScenario, setInitialScenario] = useState(null);
  const [masterDataView, setMasterDataView] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);

  const handleProductionSimulationStart = (config) => {
    // Ensure all properties, including file names, are preserved.
    setSimulationConfig(config);
    setMainView('production_display');
  };

  const handleLogisticsSimulationStart = (config, comparisonData) => {
    setSimulationConfig(config);
    setComparisonData(comparisonData);
    setMainView('logistics_display');
  };

  const handleBackToSelection = () => {
    setSimulationConfig(null);
    setInitialScenario(null);
    setMasterDataView(null);
    setComparisonData(null);
    setMainView('selection');
  };

  const handleLoadScenario = (type, scenario) => {
    setInitialScenario(scenario);
    if (type === 'production') {
      setMainView('production_setup');
    } else if (type === 'logistics') {
      setMainView('logistics_setup');
    }
    setMasterDataView(null);
  };

  const handleManageMasterData = (viewType) => {
    setMasterDataView(viewType);
    setMainView('scenario_manager');
  };

  const renderSelection = () => (
    <div className="text-center">
      <div className="row">
        <div className="col-12">
          <h2 className="mb-4">🏭 Pilih Tipe Simulasi</h2>
          <p className="lead mb-4">Pilih jenis simulasi yang ingin Anda jalankan atau kelola skenario yang sudah ada.</p>
        </div>
      </div>
      
      <div className="row g-3">
        <div className="col-md-6 col-lg-3">
          <div className="simulation-card h-100 p-3 text-center">
            <div className="mb-3">
              <i className="fas fa-cogs fa-3x text-primary"></i>
            </div>
            <h5 className="mb-3">Simulasi Produksi</h5>
            <p className="text-muted mb-3">Konfigurasi dan jalankan simulasi lini produksi untuk mengidentifikasi bottleneck.</p>
            <button 
              className="btn btn-modern btn-primary-modern w-100" 
              onClick={() => setMainView('production_setup')}
            >
              Mulai Simulasi
            </button>
          </div>
        </div>
        
        <div className="col-md-6 col-lg-3">
          <div className="simulation-card h-100 p-3 text-center">
            <div className="mb-3">
              <i className="fas fa-truck fa-3x text-success"></i>
            </div>
            <h5 className="mb-3">Simulasi Logistik</h5>
            <p className="text-muted mb-3">Simulasi transportasi material dan manajemen inventory untuk optimasi supply chain.</p>
            <button 
              className="btn btn-modern btn-success-modern w-100" 
              onClick={() => setMainView('logistics_setup')}
            >
              Mulai Simulasi
            </button>
          </div>
        </div>
        
        <div className="col-md-6 col-lg-3">
          <div className="simulation-card h-100 p-3 text-center">
            <div className="mb-3">
              <i className="fas fa-sync-alt fa-3x text-info"></i>
            </div>
            <h5 className="mb-3">Simulasi Terintegrasi</h5>
            <p className="text-muted mb-3">Jalankan simulasi produksi dan logistik secara bersamaan untuk analisis holistik.</p>
            <button 
              className="btn btn-modern btn-info-modern w-100" 
              onClick={() => setMainView('integrated_simulation')}
            >
              Mulai Simulasi
            </button>
          </div>
        </div>
        
        <div className="col-md-6 col-lg-3">
          <div className="simulation-card h-100 p-3 text-center">
            <div className="mb-3">
              <i className="fas fa-tachometer-alt fa-3x text-warning"></i>
            </div>
            <h5 className="mb-3">Dashboard</h5>
            <p className="text-muted mb-3">Lihat status sistem, statistik, dan akses cepat ke fitur-fitur utama.</p>
            <button 
              className="btn btn-modern btn-warning-modern w-100" 
              onClick={() => setMainView('dashboard')}
            >
              Buka Dashboard
            </button>
          </div>
        </div>
        
        <div className="col-md-6 col-lg-3">
          <div className="simulation-card h-100 p-3 text-center">
            <div className="mb-3">
              <i className="fas fa-database fa-3x text-secondary"></i>
            </div>
            <h5 className="mb-3">Manajemen Data</h5>
            <p className="text-muted mb-3">Kelola skenario simulasi, data master lokasi, transport unit, dan template proses.</p>
            <button 
              className="btn btn-modern btn-secondary-modern w-100" 
              onClick={() => setMainView('scenario_manager')}
            >
              Kelola Data
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderContent = () => {
    switch (mainView) {
      case 'dashboard':
        return <Dashboard onBack={handleBackToSelection} />;
      case 'production_display':
        return <ProductionSimulationDisplay config={simulationConfig} onBack={handleBackToSelection} />;
      case 'logistics_display':
        return <LogisticsSimulationDisplay config={simulationConfig} comparisonData={comparisonData} onBack={handleBackToSelection} />;
      case 'production_setup':
        return <ProductionSetupForm onStart={handleProductionSimulationStart} initialData={initialScenario} onBack={handleBackToSelection} onManageMasterData={handleManageMasterData} />;
      case 'logistics_setup':
        return <LogisticsSetupForm onStart={handleLogisticsSimulationStart} initialData={initialScenario} onBack={handleBackToSelection} onManageMasterData={handleManageMasterData} />;
      case 'scenario_manager':
        return <ScenarioManager onLoad={handleLoadScenario} onBack={handleBackToSelection} initialMasterDataView={masterDataView} />;
      case 'integrated_simulation':
        return <IntegratedSimulationView onBack={handleBackToSelection} />;
      case 'selection':
      default:
        return renderSelection();
    }
  };

  return (
    <div className="App">
      <div className="main-container">
        <header className="header-section">
          <h1>🏭 Production & Logistics Simulator</h1>
          <p>Konfigurasi dan jalankan simulasi untuk mengidentifikasi bottleneck dalam sistem produksi dan logistik</p>
        </header>

        <main className="compact-container">
          {renderContent()}
        </main>

        <footer className="text-center mt-4 text-muted">
          <p><i className="fas fa-code"></i> Dibuat dengan React & FastAPI | <i className="fas fa-heart text-danger"></i> Production Simulation System</p>
        </footer>
      </div>
    </div>
  );
}

export default App;