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
import BuyerLayout from './buyer/BuyerLayout';
import ExploreProjects from './buyer/ExploreProjects';
import ProjectDetail from './buyer/ProjectDetail';
import PurchaseCheckout from './buyer/PurchaseCheckout';
import MyPortfolio from './buyer/MyPortfolio';
import HowItWorks from './buyer/HowItWorks';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Auth routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />

        {/* Buyer / Marketplace routes */}
        <Route path="/buyer" element={<BuyerLayout />}>
          <Route index element={<Navigate to="explore" replace />} />
          <Route path="explore" element={<ExploreProjects />} />
          <Route path="project/:id" element={<ProjectDetail />} />
          <Route path="checkout/:id" element={<PurchaseCheckout />} />
          <Route path="portfolio" element={<MyPortfolio />} />
          <Route path="how-it-works" element={<HowItWorks />} />
        </Route>

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

        {/* Aliases & defaults */}
        <Route path="/explore" element={<Navigate to="/buyer/explore" replace />} />
        <Route path="/portfolio" element={<Navigate to="/buyer/portfolio" replace />} />
        <Route path="/marketplace" element={<Navigate to="/buyer/explore" replace />} />
        <Route path="/" element={<Navigate to="/auditor/overview" replace />} />
        <Route path="/overview" element={<Navigate to="/auditor/overview" replace />} />
        <Route path="*" element={<Navigate to="/auditor/overview" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
