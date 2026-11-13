export default function DemoDataNotice() {
  return (
    <aside
      role="note"
      aria-label="Demo data notice"
      className="rounded-xl border border-[#f5e6c4] bg-[#fbf4e2] px-4 py-3"
    >
      <p className="text-xs font-semibold text-[#543d11]">
        Demo data · read-only
      </p>
      <p className="mt-1 text-xs leading-relaxed text-[#71541b]">
        These fictional sample records are stored in the frontend for demonstration only. They are not real farms, evidence, audit decisions, purchases, credits, or payments.
      </p>
    </aside>
  );
}
