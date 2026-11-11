import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './LandingPage';
import AuditorLayout from './auditor/AuditorLayout';
import AuditorOverview from './auditor/AuditorOverview';
import ReviewQueue from './auditor/ReviewQueue';
import ProjectInspection from './auditor/ProjectInspection';
import FarmProjects from './auditor/FarmProjects';
import ReviewHistory from './auditor/ReviewHistory';
import AuditorSettings from './auditor/AuditorSettings';
import Login from './auth/Login';
import BuyerLayout from './buyer/BuyerLayout';
import ExploreProjects from './buyer/ExploreProjects';
import ProjectDetail from './buyer/ProjectDetail';
import PurchaseCheckout from './buyer/PurchaseCheckout';
import MyPortfolio from './buyer/MyPortfolio';
import HowItWorks from './buyer/HowItWorks';
import FarmerLayout from './farmer/FarmerLayout';
import FarmerWelcome from './farmer/FarmerWelcome';
import FarmerSignup from './farmer/FarmerSignup';
import FarmerOverview from './farmer/FarmerOverview';
import RegisterFarm from './farmer/RegisterFarm';
import MyFarms from './farmer/MyFarms';
import ProjectProgress from './farmer/ProjectProgress';
import Earnings from './farmer/Earnings';
import FarmerProfile from './farmer/FarmerProfile';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Auth routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Navigate to="/farmer/welcome" replace />} />

        {/* Farmer Workspace & Registration Flow */}
        <Route path="/farmer" element={<FarmerLayout />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="welcome" element={<FarmerWelcome />} />
          <Route path="signup" element={<FarmerSignup />} />
          <Route path="overview" element={<FarmerOverview />} />
          <Route path="register" element={<RegisterFarm />} />
          <Route path="farms" element={<MyFarms />} />
          <Route path="progress" element={<ProjectProgress />} />
          <Route path="earnings" element={<Earnings />} />
          <Route path="profile" element={<FarmerProfile />} />
        </Route>

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
        <Route path="/" element={<LandingPage />} />
        <Route path="/home" element={<LandingPage />} />
        <Route path="/explore" element={<Navigate to="/buyer/explore" replace />} />
        <Route path="/portfolio" element={<Navigate to="/buyer/portfolio" replace />} />
        <Route path="/marketplace" element={<Navigate to="/buyer/explore" replace />} />
        <Route path="/overview" element={<Navigate to="/farmer/overview" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
