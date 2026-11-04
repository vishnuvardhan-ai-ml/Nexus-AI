import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import {
  BrainCircuit,
  MapPin,
  SlidersHorizontal,
  BarChart3,
  CheckSquare,
  Settings,
} from 'lucide-react';

import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { DashboardOverview } from './pages/DashboardOverview';
import { IncidentListPage } from './pages/IncidentListPage';
import { IncidentReportPage } from './pages/IncidentReportPage';
import { IncidentDetailPage } from './pages/IncidentDetailPage';
import { SimulatorPage } from './pages/SimulatorPage';
import { MitigationPlannerPage } from './pages/MitigationPlannerPage';
import { RiskMapPage } from './pages/RiskMapPage';
import { PlaceholderPage } from './pages/PlaceholderPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <Routes>
          {/* Public Landing View */}
          <Route path="/" element={<LandingPage />} />

          {/* Authentication Pages */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Dashboard Shell with Unified Sidebar & Navbar */}
          <Route element={<DashboardLayout />}>
            <Route path="/dashboard" element={<DashboardOverview />} />

            {/* Incident Management */}
            <Route path="/incidents" element={<IncidentListPage />} />
            <Route
              path="/incidents/new"
              element={
                <ProtectedRoute>
                  <IncidentReportPage />
                </ProtectedRoute>
              }
            />
            <Route path="/incidents/:id" element={<IncidentDetailPage />} />

            {/* Upcoming Civic Decision Modules */}
            <Route
              path="/intelligence"
              element={
                <PlaceholderPage
                  title="AI Intelligence Analysis"
                  subtitle="Lightweight Scikit-learn TF-IDF + Logistic Regression classification and entity extraction"
                  milestone="MILESTONE 3: AI/ML ENGINE"
                  icon={BrainCircuit}
                  plannedFeatures={[
                    'Automated category prediction with confidence scoring',
                    'Transparent factor explanation (H, E, V, D contribution percentages)',
                    'Model limitation notices and uncertainty bounds',
                    'Batch intelligence processing and classification diagnostics',
                  ]}
                />
              }
            />

            <Route path="/map" element={<RiskMapPage />} />

            <Route path="/simulator" element={<SimulatorPage />} />

            <Route path="/mitigation-planner" element={<MitigationPlannerPage />} />

            <Route
              path="/analytics"
              element={
                <PlaceholderPage
                  title="Risk Analytics & Trends"
                  subtitle="Recharts visualizations of category distribution, temporal incident spikes, and resolution times"
                  milestone="MILESTONE 6: ANALYTICS & REPORTING"
                  icon={BarChart3}
                  plannedFeatures={[
                    'Category breakdown pie and bar charts',
                    'Weekly and monthly risk velocity timeline charts',
                    'Factor contribution comparative analysis',
                    'Exportable PDF/CSV civic risk audit reports',
                  ]}
                />
              }
            />

            <Route
              path="/actions"
              element={
                <PlaceholderPage
                  title="Action Center & Playbooks"
                  subtitle="Actionable municipal mitigation recommendations and emergency response dispatches"
                  milestone="MILESTONE 7: RECOMMENDATIONS & DISPATCH"
                  icon={CheckSquare}
                  plannedFeatures={[
                    'Automated recommendation playbooks based on risk score thresholds',
                    'Priority work-order generation for civic maintenance crews',
                    'Community advisory notification drafting',
                    'Intervention status tracking and audit logging',
                  ]}
                />
              }
            />

            <Route
              path="/settings"
              element={
                <PlaceholderPage
                  title="Settings & Administration"
                  subtitle="System configuration, Firestore sync rules, and role-based access control (RBAC)"
                  milestone="MILESTONE 8: ADMIN & SECURITY"
                  icon={Settings}
                  plannedFeatures={[
                    'Role authorization viewer (COMMUNITY_USER, ANALYST, ADMIN)',
                    'Firebase Admin SDK token verification toggle',
                    'Risk equation weight adjustments (H, E, V, D multipliers)',
                    'Telemetry heartbeat intervals and system activity logs',
                  ]}
                />
              }
            />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
