import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { ServicesPage } from './pages/ServicesPage';
import { InvestigationsPage } from './pages/InvestigationsPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { LogsPage } from './pages/LogsPage';
import { DeploymentsPage } from './pages/DeploymentsPage';
import { TracesPage } from './pages/TracesPage';
import { NotFoundPage } from './pages/NotFoundPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="services" element={<ServicesPage />} />
          <Route path="investigations" element={<InvestigationsPage />} />
          <Route path="incidents" element={<IncidentsPage />} />
          <Route path="approvals" element={<ApprovalsPage />} />
          <Route path="logs" element={<LogsPage />} />
          <Route path="deployments" element={<DeploymentsPage />} />
          <Route path="traces" element={<TracesPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
