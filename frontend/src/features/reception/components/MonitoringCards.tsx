import { TrendingDown, TrendingUp } from "lucide-react";

export function KpiCard({
  title,
  icon: Icon,
  value,
  note,
  change,
}: {
  title: string;
  icon: React.ElementType;
  value: string;
  note: string;
  change?: number;
}) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white shadow-sm p-5 card-hover">
      <div className="flex items-center justify-between text-slate-600 mb-3">
        <span className="text-sm font-medium">{title}</span>
        <Icon className="w-4 h-4 text-slate-400" />
      </div>
      <p className="text-3xl font-bold text-slate-800">{value}</p>
      <div className="flex items-center gap-2 mt-1">
        {change !== undefined && (
          <span className={`flex items-center gap-0.5 text-xs font-semibold ${change >= 0 ? "text-green-600" : "text-red-500"}`}>
            {change >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
            {Math.abs(change).toFixed(0)}%
          </span>
        )}
        <span className="text-xs text-slate-400">{note}</span>
      </div>
    </div>
  );
}

export function ShareBar({
  name,
  value,
  share,
  className = "bg-brand-700",
}: {
  name: string;
  value: string;
  share: number;
  className?: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-700">{name}</span>
        <span className="font-semibold text-slate-800">{value}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full rounded-full ${className}`} style={{ width: `${share * 100}%` }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
