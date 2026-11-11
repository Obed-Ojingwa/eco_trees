import { useState } from 'react';
import { Wallet } from 'lucide-react';

interface EarningsData {
  potential_allocation: string;
  has_transactions: boolean;
}

export default function Earnings() {
  const [data] = useState<EarningsData>({
    potential_allocation: '₦0.00',
    has_transactions: false,
  });

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Title */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Earnings overview
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Track demo purchase allocations linked to your farms.
        </p>
      </div>

      {/* Two Column Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
        {/* Left Card (8 cols) */}
        <div className="md:col-span-8 bg-[#eaf3ec] rounded-2xl p-8 flex flex-col justify-between">
          <div>
            <span className="text-xs text-gray-600 font-medium">
              Potential farmer allocation
            </span>
            <div className="text-4xl font-bold text-gray-900 tracking-tight mt-3">
              {data.potential_allocation}
            </div>
          </div>
          <span className="text-xs text-gray-500 mt-6">
            No simulated purchases yet
          </span>
        </div>

        {/* Right Info Card (4 cols) */}
        <div className="md:col-span-4 bg-[#fbf4e2] border border-[#f5e6c4] rounded-2xl p-6 flex flex-col justify-center">
          <h3 className="font-bold text-sm text-[#543d11]">How it works</h3>
          <p className="text-xs text-[#71541b] mt-2 leading-relaxed">
            The MVP demonstrates a possible proceeds allocation. No real payout is made.
          </p>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="space-y-4">
        <h3 className="font-semibold text-sm text-gray-900">
          Recent activity
        </h3>

        <div className="bg-white rounded-2xl border border-gray-100 p-12 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex flex-col items-center justify-center text-center">
          <div className="w-12 h-12 rounded-2xl bg-[#eaf3ec] flex items-center justify-center text-[#1b4332] mb-3">
            <Wallet size={24} />
          </div>
          <h4 className="font-bold text-sm text-gray-900">
            No transactions yet
          </h4>
          <p className="text-xs text-gray-400 mt-1.5 max-w-sm">
            If an eligible project receives a demo purchase, its allocation will appear here.
          </p>
        </div>
      </div>
    </div>
  );
}
