import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AuditorLayout from './auditor/AuditorLayout';
import AuditorOverview from './auditor/AuditorOverview';
import ReviewQueue from './auditor/ReviewQueue';
import ProjectInspection from './auditor/ProjectInspection';
import FarmProjects from './auditor/FarmProjects';
import ReviewHistory from './auditor/ReviewHistory';
import AuditorSettings from './auditor/AuditorSettings';
import Login from './auth/Login';
import Signup from './auth/Signup';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Auth routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* Auditor Workspace with nested routes */}
        <Route path="/auditor" element={<AuditorLayout />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<AuditorOverview />} />
          <Route path="review-queue" element={<ReviewQueue />} />
          <Route path="project-inspection" element={<ProjectInspection />} />
          <Route path="project-inspection/:id" element={<ProjectInspection />} />
          <Route path="farm-projects" element={<FarmProjects />} />
          <Route path="review-history" element={<ReviewHistory />} />
          <Route path="settings" element={<AuditorSettings />} />
        </Route>

        {/* Default route redirects to auditor overview */}
        <Route path="/" element={<Navigate to="/auditor/overview" replace />} />
        <Route path="/overview" element={<Navigate to="/auditor/overview" replace />} />
        <Route path="*" element={<Navigate to="/auditor/overview" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
