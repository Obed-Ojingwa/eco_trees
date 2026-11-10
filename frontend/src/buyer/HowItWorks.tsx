import { ShieldCheck, Trees, ShoppingBag, Info } from 'lucide-react';

export default function HowItWorks() {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          How it works
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          Learn how EcoTrees connects verified tree planting with transparent nature-based restoration listings.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-[#eaf3ec] flex items-center justify-center text-[#1b4332]">
            <Trees size={20} />
          </div>
          <h3 className="font-bold text-sm text-gray-900">1. Farm registration</h3>
          <p className="text-xs text-gray-600 leading-relaxed">
            Local farmers map their restoration plots using GPS coordinates and capture tagged photo evidence of newly planted trees.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-[#eaf3ec] flex items-center justify-center text-[#1b4332]">
            <ShieldCheck size={20} />
          </div>
          <h3 className="font-bold text-sm text-gray-900">2. Independent audit</h3>
          <p className="text-xs text-gray-600 leading-relaxed">
            Specialist auditors analyze plot geometry, evidence photos, and Sentinel-2 satellite NDVI observations to verify growth.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] space-y-3">
          <div className="w-10 h-10 rounded-xl bg-[#eaf3ec] flex items-center justify-center text-[#1b4332]">
            <ShoppingBag size={20} />
          </div>
          <h3 className="font-bold text-sm text-gray-900">3. Demo marketplace</h3>
          <p className="text-xs text-gray-600 leading-relaxed">
            Approved restoration projects are listed as illustrative units allowing supporters to simulate nature-based project purchases.
          </p>
        </div>
      </div>

      {/* Notice */}
      <div className="bg-[#fbf4e2] border border-[#f5e6c4] rounded-2xl p-6">
        <div className="flex items-center gap-2 text-sm font-bold text-[#543d11] mb-1.5">
          <Info size={16} className="text-[#875d15] shrink-0" />
          <span>Marketplace clarification</span>
        </div>
        <p className="text-xs text-[#71541b] leading-relaxed pl-6">
          EcoTrees listings are currently prototype demo units based on internal verification records. They are not formally certified carbon offset credits.
        </p>
      </div>
    </div>
  );
}
