import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import OverviewPage from './pages/OverviewPage';
import InvestigationsListPage from './pages/InvestigationsListPage';
import NewInvestigationPage from './pages/NewInvestigationPage';
import InvestigationPage from './pages/InvestigationPage';
import ServicesPage from './pages/ServicesPage';
import EvidencePage from './pages/EvidencePage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-bg-main text-text-primary">
        {/* Fixed Sidebar */}
        <Sidebar />

        {/* Main Application Area */}
        <div className="flex-1 flex flex-col min-w-0 min-h-screen overflow-x-hidden">
          <TopBar />
          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/investigations" element={<InvestigationsListPage />} />
              <Route path="/investigations/new" element={<NewInvestigationPage />} />
              <Route path="/investigations/:id" element={<InvestigationPage />} />
              <Route path="/services" element={<ServicesPage />} />
              <Route path="/evidence" element={<EvidencePage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}
