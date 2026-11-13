export interface DemoFarmProject {
  id: string;
  farm: string;
  farmer: string;
  state: string;
  location: string;
  trees: number;
  areaHa: number;
  status: string;
  submittedAt: string;
  priority: 'High' | 'Normal';
}

export const DEMO_FARM_PROJECTS: DemoFarmProject[] = [
  {
    id: 'DEMO-ET-1001',
    farm: 'Green Valley Demo Farm',
    farmer: 'Ama Demo Farmer',
    state: 'Ogun',
    location: 'Abeokuta, Ogun State',
    trees: 620,
    areaHa: 2.4,
    status: 'Awaiting review',
    submittedAt: '12 Nov 2026',
    priority: 'Normal',
  },
  {
    id: 'DEMO-ET-1002',
    farm: 'Idera Community Demo Grove',
    farmer: 'Tunde Demo Farmer',
    state: 'Ogun',
    location: 'Ifo, Ogun State',
    trees: 400,
    areaHa: 1.5,
    status: 'Internally approved',
    submittedAt: '11 Nov 2026',
    priority: 'Normal',
  },
  {
    id: 'DEMO-ET-1003',
    farm: 'Waterside Demo Agroforest',
    farmer: 'Chika Demo Farmer',
    state: 'Lagos',
    location: 'Epe, Lagos State',
    trees: 220,
    areaHa: 0.9,
    status: 'Changes requested',
    submittedAt: '10 Nov 2026',
    priority: 'High',
  },
];

export interface DemoReviewHistoryItem {
  id: string;
  date: string;
  time: string;
  reviewer: string;
  project_id: string;
  action: string;
  isApproved: boolean;
}

export const DEMO_REVIEW_HISTORY: DemoReviewHistoryItem[] = [
  {
    id: 'DEMO-REVIEW-001',
    date: '12 Nov 2026',
    time: '10:20',
    reviewer: 'Demo Reviewer A',
    project_id: 'DEMO-ET-1001',
    action: 'Submission received · sample',
    isApproved: false,
  },
  {
    id: 'DEMO-REVIEW-002',
    date: '11 Nov 2026',
    time: '15:10',
    reviewer: 'Demo Reviewer B',
    project_id: 'DEMO-ET-1002',
    action: 'Internal review completed · sample',
    isApproved: true,
  },
  {
    id: 'DEMO-REVIEW-003',
    date: '10 Nov 2026',
    time: '09:45',
    reviewer: 'Demo Reviewer A',
    project_id: 'DEMO-ET-1003',
    action: 'Changes requested · sample',
    isApproved: false,
  },
];
