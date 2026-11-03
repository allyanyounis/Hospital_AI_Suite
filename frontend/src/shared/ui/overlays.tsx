"use client";

/** Modal dialog and right-side drawer: dimmed backdrop, click outside or press Esc to close. */

import { useEffect } from "react";
import { Icons } from "./icons";

/** Calls `onClose` when Escape is pressed while mounted. */
function useEscape(onClose: () => void) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
}

function OverlayHeader({
  title,
  subtitle,
  onClose,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-100 px-6 py-4">
      <div className="min-w-0">
        <h3 className="text-lg font-bold text-slate-800">{title}</h3>
        {subtitle && <div className="text-sm text-slate-500">{subtitle}</div>}
      </div>
      <button onClick={onClose} title="Close" aria-label="Close" className="p-1 text-slate-400 hover:text-slate-700">
        <Icons.Close className="h-5 w-5" />
      </button>
    </div>
  );
}

const MODAL_WIDTH = { sm: "max-w-md", md: "max-w-2xl", lg: "max-w-4xl" };

/**
 * Centred dialog. The body (children) is neither padded nor scrolled, so callers lay it out themselves
 * (e.g. `flex-1 overflow-y-auto px-6 py-4`); `footer` renders below a divider.
 */
export function Modal({
  title,
  subtitle,
  onClose,
  size = "md",
  footer,
  children,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  onClose: () => void;
  size?: "sm" | "md" | "lg";
  footer?: React.ReactNode;
  children: React.ReactNode;
}) {
  useEscape(onClose);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : undefined}
        className={`flex max-h-[85vh] w-full ${MODAL_WIDTH[size]} flex-col rounded-2xl bg-white shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        <OverlayHeader title={title} subtitle={subtitle} onClose={onClose} />
        {children}
        {footer && <div className="shrink-0 border-t border-slate-100 px-6 py-3">{footer}</div>}
      </div>
    </div>
  );
}

/** Full-height panel on the right edge with a padded, scrollable body; `footer` stays pinned at the bottom. */
export function Drawer({
  title,
  subtitle,
  onClose,
  footer,
  className = "",
  children,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  onClose: () => void;
  footer?: React.ReactNode;
  /** Extra classes for the panel, e.g. another width (default: full width on phones, 32rem from sm up) */
  className?: string;
  children: React.ReactNode;
}) {
  useEscape(onClose);
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40" onClick={onClose}>
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={typeof title === "string" ? title : undefined}
        className={`flex h-full w-full flex-col bg-white shadow-2xl sm:w-[32rem] ${className}`}
        onClick={(e) => e.stopPropagation()}
      >
        <OverlayHeader title={title} subtitle={subtitle} onClose={onClose} />
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer && <div className="shrink-0 border-t border-slate-100 px-6 py-3">{footer}</div>}
      </aside>
    </div>
  );
}
