import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Info } from 'lucide-react';

interface CheckoutData {
  farm_name: string;
  project_id: string;
  demo_units: number;
  price_per_unit: number;
}

export default function PurchaseCheckout() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const checkoutData: CheckoutData = {
    farm_name: 'Green Valley Farm',
    project_id: id ? (id.startsWith('ET-') ? `ET-2026-${id.slice(3)}` : id) : 'ET-2026-00124',
    demo_units: 100,
    price_per_unit: 5000,
  };

  const totalAmount = checkoutData.demo_units * checkoutData.price_per_unit;

  const handleConfirmPurchase = async () => {
    setLoading(true);
    try {
      // Optional simulated call to backend transaction endpoint
      await fetch('/api/buyer/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-EcoTrees': '1' },
        body: JSON.stringify({
          project_id: checkoutData.project_id,
          units: checkoutData.demo_units,
          amount: totalAmount,
        }),
      }).catch(() => null);
    } finally {
      setLoading(false);
      navigate('/buyer/portfolio');
    }
  };

  return (
    <div className="space-y-8">
      {/* Title & Subtitle */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Demo purchase checkout
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Check the details before confirming this demo transaction.
        </p>
      </div>

      {/* Two Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column (8 cols): Checkout Details */}
        <div className="lg:col-span-8 bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-4">
          <h2 className="text-sm font-bold text-gray-900 mb-4">
            {checkoutData.farm_name} · {checkoutData.project_id}
          </h2>

          {/* Field 1: Demo units */}
          <div className="border border-gray-200/80 rounded-xl p-3.5">
            <label className="text-[11px] font-medium text-gray-400 block mb-1">
              Demo units
            </label>
            <div className="text-sm font-semibold text-gray-900">
              {checkoutData.demo_units}
            </div>
          </div>

          {/* Field 2: Illustrative price per unit */}
          <div className="border border-gray-200/80 rounded-xl p-3.5">
            <label className="text-[11px] font-medium text-gray-400 block mb-1">
              Illustrative price per unit
            </label>
            <div className="text-sm font-semibold text-gray-900">
              ₦{checkoutData.price_per_unit.toLocaleString()}
            </div>
          </div>

          {/* Field 3: Total demo amount */}
          <div className="border border-gray-200/80 rounded-xl p-3.5">
            <label className="text-[11px] font-medium text-gray-400 block mb-1">
              Total demo amount
            </label>
            <div className="text-sm font-semibold text-gray-900">
              ₦{totalAmount.toLocaleString()}
            </div>
          </div>

          {/* Payment simulation yellow card */}
          <div className="bg-[#fbf4e2] border border-[#f5e6c4] rounded-xl p-4 mt-5">
            <div className="flex items-center gap-2 text-xs font-bold text-[#543d11] mb-1">
              <Info size={14} className="text-[#875d15] shrink-0" />
              <span>Payment simulation</span>
            </div>
            <p className="text-xs text-[#71541b] leading-relaxed pl-5">
              This checkout is a prototype simulation. No payment will be collected and no credits will be transferred.
            </p>
          </div>
        </div>

        {/* Right Column (4 cols): Order summary */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
          <h3 className="text-sm font-bold text-gray-900">Order summary</h3>

          <p className="text-xs text-gray-600 mt-4 font-normal">
            {checkoutData.demo_units} demo units × ₦{checkoutData.price_per_unit.toLocaleString()}
          </p>

          <div className="text-xl font-bold text-gray-900 mt-2">
            Total ₦{totalAmount.toLocaleString()}
          </div>

          <button
            onClick={handleConfirmPurchase}
            disabled={loading}
            className="w-full bg-[#1e4d3a] hover:bg-[#163c2c] text-white text-xs font-semibold py-3.5 rounded-xl transition-colors cursor-pointer mt-6 disabled:opacity-60"
          >
            {loading ? 'Processing simulation...' : 'Confirm simulated purchase'}
          </button>

          <button
            onClick={() => navigate(-1)}
            className="w-full border border-gray-200 hover:bg-gray-50 text-gray-700 text-xs font-medium py-3 rounded-xl transition-colors cursor-pointer mt-2.5"
          >
            Back to project
          </button>
        </div>
      </div>

      {/* Transaction scope card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
        <div className="flex items-center gap-2 text-sm font-bold text-gray-900 mb-2">
          <Info size={16} className="text-emerald-700 shrink-0" />
          <span>Transaction scope</span>
        </div>
        <p className="text-xs text-gray-600 leading-relaxed pl-6">
          The demo creates a transaction record and an illustrative farmer allocation record for the hackathon walkthrough only.
        </p>
      </div>
    </div>
  );
}
