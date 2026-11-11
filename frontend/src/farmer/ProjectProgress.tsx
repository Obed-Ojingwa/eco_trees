import { useState } from 'react';
import { CheckCircle2, Clock, Circle, Info } from 'lucide-react';

interface FarmProgressData {
  farm_name: string;
  submitted_date: string;
  status: string;
}

export default function ProjectProgress() {
  const [data] = useState<FarmProgressData>({
    farm_name: 'Green Valley Farm',
    submitted_date: '7 November 2026',
    status: 'Under review',
  });

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Page Title */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Project progress
        </h1>
        <p className="text-sm text-gray-600 mt-1.5">
          See where your farm project stands.
        </p>
      </div>

      {/* Farm Banner Card */}
      <div className="bg-white rounded-2xl border border-gray-100 p-6 shadow-[0_1px_2px_rgba(0,0,0,0.02)] flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-gray-900">
            {data.farm_name}
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Submitted · {data.submitted_date}
          </p>
        </div>

        <span className="bg-[#fef3c7] text-[#92400e] text-xs font-semibold px-3.5 py-1 rounded-full">
          {data.status}
        </span>
      </div>

      {/* Project Timeline Section */}
      <div className="space-y-4">
        <h3 className="font-semibold text-sm text-gray-900">
          Project timeline
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Step 1: Submission received */}
          <div className="bg-[#f2f7f4] rounded-2xl p-6 space-y-2">
            <CheckCircle2 size={20} className="text-[#1b4332]" />
            <h4 className="font-bold text-sm text-gray-900 pt-1">
              Submission received
            </h4>
            <p className="text-xs text-gray-600 leading-relaxed">
              Your farm details and photos are with our team.
            </p>
          </div>

          {/* Step 2: Under review (Current active step) */}
          <div className="bg-[#f2f7f4] rounded-2xl p-6 space-y-2 border border-[#1b4332]/20">
            <Clock size={20} className="text-[#1b4332]" />
            <h4 className="font-bold text-sm text-[#1b4332] pt-1">
              Under review
            </h4>
            <p className="text-xs text-[#1b4332]/90 leading-relaxed font-medium">
              Our team is taking a closer look.
            </p>
          </div>

          {/* Step 3: Review decision */}
          <div className="bg-[#f2f7f4] rounded-2xl p-6 space-y-2 opacity-80">
            <Circle size={20} className="text-gray-400" />
            <h4 className="font-bold text-sm text-gray-900 pt-1">
              Review decision
            </h4>
            <p className="text-xs text-gray-600 leading-relaxed">
              We’ll let you know here when there’s news.
            </p>
          </div>
        </div>
      </div>

      {/* Important Disclaimer Banner */}
      <div className="bg-[#fbf4e2] border border-[#f5e6c4] rounded-2xl p-6">
        <div className="flex items-center gap-2 text-sm font-bold text-[#543d11] mb-1">
          <Info size={16} className="text-[#875d15] shrink-0" />
          <span>Important</span>
        </div>
        <p className="text-xs text-[#71541b] leading-relaxed pl-6">
          Internal approval is not formal carbon-credit certification.
        </p>
      </div>
    </div>
  );
}
