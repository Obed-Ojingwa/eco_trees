export interface DemoMetric {
  label: string;
  value: string;
}

interface DemoMetricSnapshotProps {
  title: string;
  metrics: DemoMetric[];
}

export default function DemoMetricSnapshot({
  title,
  metrics,
}: DemoMetricSnapshotProps) {
  const gridColumns =
    metrics.length === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-4';

  return (
    <section
      aria-label={`${title}, illustrative demo values`}
      className="rounded-2xl border border-[#dbe8df] bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.02)]"
    >
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
        <span className="rounded-full bg-[#eaf3ec] px-2.5 py-1 text-[10px] font-bold tracking-wide text-[#1b4332]">
          DEMO
        </span>
      </div>
      <p className="mt-1 text-xs text-gray-500">
        Static illustrative values only — not live account data or verified outcomes.
      </p>

      <div className={`mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 ${gridColumns}`}>
        {metrics.map((metric) => (
          <div
            key={metric.label}
            className="rounded-xl border border-gray-100 bg-[#f8faf8] p-4"
          >
            <p className="text-xs font-medium text-gray-500">{metric.label}</p>
            <p className="mt-2 text-2xl font-bold tracking-tight text-[#1b4332]">
              {metric.value}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
