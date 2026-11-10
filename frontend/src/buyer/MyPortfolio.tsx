import { useEffect, useState } from 'react';
import { LayoutGrid, Wallet, Info } from 'lucide-react';

interface PortfolioStats {
  demo_purchases: string;
  demo_units: string;
  illustrative_spend: string;
}

interface PortfolioTransaction {
  id: string;
  date: string;
  project: string;
  demo_units: number;
  amount: string;
  status: string;
}

interface PortfolioData {
  stats: PortfolioStats;
  transactions: PortfolioTransaction[];
}

async function fetchPortfolioData(): Promise<PortfolioData> {
  try {
    const res = await fetch('/api/buyer/portfolio');
    if (!res.ok) throw new Error();
    return await res.json();
  } catch {
    // Exact fallback matching the UI specification
    return {
      stats: {
        demo_purchases: '01',
        demo_units: '100',
        illustrative_spend: '₦500,000',
      },
      transactions: [
        {
          id: 'tx-001',
          date: '09 Nov 2026',
          project: 'Green Valley Farm',
          demo_units: 100,
          amount: '₦500,000',
          status: 'Simulated',
        },
      ],
    };
  }
}

export default function MyPortfolio() {
  const [data, setData] = useState<PortfolioData | null>(null);

  useEffect(() => {
    fetchPortfolioData().then(setData);
  }, []);

  if (!data) {
    return <div className="p-8 text-gray-500 text-sm">Loading portfolio...</div>;
  }

  return (
    <div className="space-y-8">
      {/* Title & Subtitle */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          My portfolio
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Keep track of your demo transactions and the farmer allocations they illustrate.
        </p>
      </div>

      {/* 3 Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Purchases */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <span className="text-3xl font-bold text-gray-900 tracking-tight">
              {data.stats.demo_purchases}
            </span>
            <LayoutGrid size={20} className="text-[#1b4332]" />
          </div>
          <span className="text-xs text-gray-500 mt-4 font-normal">
            Demo purchases
          </span>
        </div>

        {/* Card 2: Units */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <span className="text-3xl font-bold text-gray-900 tracking-tight">
              {data.stats.demo_units}
            </span>
            <svg
              className="w-5 h-5 text-[#1b4332]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22v-7" />
              <path d="M12 15a5 5 0 0 1-5-5c0-3 2.5-6 5-8 2.5 2 5 5 5 8a5 5 0 0 1-5 5z" />
              <path d="M7 10a4 4 0 0 0-4 4c0 2 1.5 3.5 3.5 3.5" />
              <path d="M17 10a4 4 0 0 1 4 4c0 2-1.5 3.5-3.5 3.5" />
            </svg>
          </div>
          <span className="text-xs text-gray-500 mt-4 font-normal">
            Demo units
          </span>
        </div>

        {/* Card 3: Spend */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <span className="text-3xl font-bold text-gray-900 tracking-tight">
              {data.stats.illustrative_spend}
            </span>
            <Wallet size={20} className="text-gray-400" />
          </div>
          <span className="text-xs text-gray-500 mt-4 font-normal">
            Illustrative spend
          </span>
        </div>
      </div>

      {/* Transactions Table Container */}
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-[#f8faf8] border-b border-gray-100 text-[11px] font-semibold tracking-wider text-gray-500 uppercase">
              <th className="py-3 px-6">DATE</th>
              <th className="py-3 px-6">PROJECT</th>
              <th className="py-3 px-6">DEMO UNITS</th>
              <th className="py-3 px-6">AMOUNT</th>
              <th className="py-3 px-6">STATUS</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-xs">
            {data.transactions.map((tx) => (
              <tr key={tx.id} className="hover:bg-[#fafbfa] transition-colors">
                <td className="py-4 px-6 text-gray-600">{tx.date}</td>
                <td className="py-4 px-6 font-medium text-gray-900">{tx.project}</td>
                <td className="py-4 px-6 text-gray-600">{tx.demo_units}</td>
                <td className="py-4 px-6 font-semibold text-gray-900">{tx.amount}</td>
                <td className="py-4 px-6 text-gray-700">{tx.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Farmer proceeds allocation card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
        <h3 className="text-sm font-bold text-gray-900">
          Farmer proceeds allocation
        </h3>
        <p className="text-xs text-gray-600 mt-2 leading-relaxed">
          A demo allocation record may show the share assigned to the farmer based on the prototype's configured distribution rule.
        </p>
        <p className="text-xs text-gray-800 font-medium mt-3">
          Allocation status: Simulated · Payout status: Not paid
        </p>
      </div>

      {/* Demo-only portfolio disclaimer */}
      <div className="bg-[#fbf4e2] border border-[#f5e6c4] rounded-2xl p-6">
        <div className="flex items-center gap-2 text-sm font-bold text-[#543d11] mb-1.5">
          <Info size={16} className="text-[#875d15] shrink-0" />
          <span>Demo-only portfolio</span>
        </div>
        <p className="text-xs text-[#71541b] leading-relaxed pl-6">
          These records are illustrative. No real carbon credits, certified offsets, payment settlement or farmer payout has occurred.
        </p>
      </div>
    </div>
  );
}
