export function CountPill({ icon, tone, n, label }: { icon: React.ReactNode; tone: string; n: number; label: string }) {
  return (
    <span className={`flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 font-medium ${tone}`}>
      {icon}
      {n} {label}
    </span>
  );
}

export function Chip({
  active,
  subtle,
  onClick,
  children,
}: {
  active: boolean;
  subtle?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-medium transition-colors ${
        active
          ? subtle
            ? "bg-brand-50 text-brand-800 ring-1 ring-brand-200"
            : "bg-brand-700 text-white shadow-sm"
          : "text-slate-600 hover:bg-white"
      }`}
    >
      {children}
    </button>
  );
}
