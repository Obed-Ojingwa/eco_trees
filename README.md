# EcoTrees

> Turning Smallholder Tree Planting into Verified Carbon Revenue

EcoTrees is a multilingual Digital Measurement, Reporting, and Verification (dMRV) and payout platform for Nigerian smallholder farmers. It replaces slow, expensive manual field audits with satellite data, pools smallholder tree growth into verifiable batches, and routes payouts back to local planters when corporate buyers purchase verified carbon impact.

---

## The Problem

Millions of smallholder farmers and community groups across Africa plant trees and drive climate action, yet almost none of them earn from the global carbon market.

- **Costly manual audits:** Traditional verification can take 12–24 months and cost $50,000–$100,000, which excludes the vast majority of smallholders.
- **Data integrity deficit:** Unverified ground data pushes African carbon offsets to steep discounts compared with global prices.
- **Capital disconnection:** Project developers cannot easily turn verified environmental impact into working capital or bank collateral.

Climate action is local, but carbon finance infrastructure is still difficult to access at smallholder scale.

---

## Our Solution

EcoTrees acts as the digital MRV software layer and data bridge between the people who create climate value and the buyers who pay for it. It does not issue its own certificates. Verified data is packaged into audit-ready formats for submission to established carbon registries, while EcoTrees provides the satellite pipeline, auditor tooling, marketplace, and payout rails.

| Role | Who | What they do | Output |
| --- | --- | --- | --- |
| **Value Creator** | Local farmers and community planting groups | Plant trees on degraded land and map their plots | Measurable CO₂e reduction data |
| **Digital Verifier** | EcoTrees engine and independent auditors | Aggregate Sentinel-2 and NASA satellite data and review it against carbon methodologies | Certified digital audit trail |
| **Ultimate Payer** | Corporates and green banks | Buy verified carbon credits or provide climate-linked loans | Capital liquidity for farmers and ESG outcomes for buyers |

---

## Key Features

- **Satellite-Verified dMRV:** Uses Sentinel-2 earth observation data to verify farm boundaries, track canopy growth, and run NDVI health comparisons.
- **Fraud and Overlap Checks:** Automated spatial checks flag overlapping land claims and double-counting before a batch reaches an auditor.
- **Multilingual Support:** Built on `react-i18next`, with instant full-screen translation across English, Nigerian Pidgin, Hausa, Igbo, and Yoruba.
- **Mobile-First Design:** Optimized for low-end Android browsers with lightweight JavaScript, offline draft queues, and touch-friendly targets.
- **Secure Escrow and Settlement:** Automated pro-rata split payouts with disbursement tracking.
- **Controlled Auditor Portal:** Invite-only verification console with multi-factor batch reviews and cryptographically signed data receipts.
- **Verified Marketplace:** Buyers see satellite proof and serial numbers for every credit before purchase.

---

## Demo Flow

The hackathon demo walks through the full agroforestry pipeline, from a farmer's plot to a payout:

1. **Site Selection:** The user draws a plot boundary on an interactive map.
2. **Satellite Call:** The platform fetches Sentinel imagery and measures biomass using NDVI.
3. **CO₂ Quantification:** The carbon accounting model converts biomass into metric tonnes of CO₂e.
4. **Bank Disbursal:** A simulated payout is triggered through a banking API sandbox.

> **Demo scope:** Payouts in this prototype are simulated. Live registry issuance and real money movement are part of the roadmap below.

---

## Core User Portals

### Farmer Portal (`/farmer/dashboard`)
Register land, submit growth proof, and track earnings.
- Day-Zero Seedling checklist
- Step-by-step polygon mapping wizard
- Live GPS-stamped photo capture
- Transparent earnings tracker

### Auditor Console (`/auditor/dashboard`)
Inspect digital evidence, verify carbon calculations, and approve impact batches.
- Dashboard of pending batches
- Split-screen NDVI satellite heatmap timeline with field photos
- Photo EXIF metadata checks
- Fraud check for land overlaps and double-counting
- One-click batch approval with a digital signature applied to the data package

### Buyer Marketplace (`/marketplace`)
Purchase verified carbon reduction impact.
- Credit discovery with satellite proof
- Transparent fee breakdowns
- Secure checkout flow
- Instant serial number verification


## System Architecture

```
┌─────────────────────────────────────────────────────┐
│  Frontend: React + TypeScript + Tailwind + Leaflet  │
└──────────────────────────┬──────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────┐
│               Core Backend Gateway (API)            │
└──────┬───────────────────┬───────────────────┬──────┘
       │                   │                   │
┌──────▼──────┐   ┌────────▼────────┐   ┌──────▼──────┐
│ Data Feeds  │   │ Calculation     │   │ Banking and │
│             │   │ Engine          │   │ Payments    │
└─────────────┘   └─────────────────┘   └─────────────┘
```

| Layer | Description |
| --- | --- |
| **Frontend** | Mobile-first React application with Leaflet GIS mapping for plot boundaries and satellite overlays. |
| **Core Backend Gateway** | API layer connecting the portals to data, calculation, and payment services. |
| **Data Feeds** | Sentinel Hub, NASA Earthdata, and NiMet weather data. |
| **Calculation Engine** | Carbon accounting model aligned with Verra and Gold Standard approaches. |
| **Banking and Payments** | Bank sandbox APIs and mobile money or payment gateway integrations for payouts and checkout. |
| **Registry Integration (planned)** | API submission of verified batches to external registries such as the NCCC Registry, Verra, and Gold Standard, which issue the official serialized credits. |

---

## Tech Stack

| Area | Technology |
| --- | --- |
| Framework | React (Vite SPA) |
| Language | TypeScript |
| Routing | React Router (`react-router-dom`) |
| Styling | Tailwind CSS |
| Forms and Validation | React Hook Form |
| Mapping | Leaflet and `react-leaflet` |

---

## Project Structure

```
ecotrees/
├── backend/                 # Backend API
└── frontend/                # React + Vite client
    ├── public/              # Static assets
    ├── src/
    │   ├── auditor/         # Auditor console
    │   ├── auth/            # Authentication
    │   ├── buyer/           # Buyer marketplace
    │   ├── farmer/          # Farmer portal
    │   ├── App.tsx
    │   ├── index.css
    │   ├── main.tsx
    │   └── vite-env.d.ts
    ├── eslint.config.js
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── tsconfig.app.json
    ├── tsconfig.node.json
    └── vite.config.ts
```

---

## Getting Started

### Prerequisites

- Node.js v18 or higher
- npm or yarn

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/buildwithfavvy/ecotrees.git
   cd ecotrees
   ```

2. **Install frontend dependencies:**

   ```bash
   cd frontend
   npm install
   ```

3. **Start the development server:**

   ```bash
   npm run dev
   ```

4. **Open the app:**
   Navigate to [http://localhost:5173](http://localhost:5173) in your browser.

---

## Business Model

| Revenue Stream | Description |
| --- | --- |
| **Transaction Fee (3%–5%)** | Commission on every carbon credit or off-take settlement executed on the marketplace. |
| **SaaS MRV Subscriptions** | Enterprise tier for NGOs, cooperatives, and project developers using real-time satellite biomass dashboards. |
| **Loan Origination Fee (1%)** | Collected on working capital loans disbursed through integrated banking APIs. |
| **EU CBAM Audit Modules** | Subscription compliance reporting for African exporters shipping goods to the European Union. |

---

## Roadmap

| Phase | Milestone | Description |
| --- | --- | --- |
| **Phase 1 (Now)** | Hackathon MVP | Functional geospatial dMRV interface connected to banking sandbox APIs. |
| **Months 1–3** | Pilot Projects in Nigeria | Onboard 3 regional agroforestry and cookstove developers to test real payouts. |
| **Months 6–12** | Pan-African Expansion | Roll out EU CBAM export compliance modules across Ghana and East Africa. |
