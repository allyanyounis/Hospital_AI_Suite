"use client";

/**
 * Virtualised list and table for long, paged data: only the rows in view are rendered. Rows have a fixed height
 * (`estimateSize`, px). `onEndReached` fires when the user scrolls within `endThreshold` rows of the end - wire it to
 * useInfiniteQuery's fetchNextPage (guarded by hasNextPage) and pass `loading={isFetchingNextPage}`.
 */

import { useVirtualizer } from "@tanstack/react-virtual";
import { useEffect, useRef } from "react";
import { EmptyState, Spinner } from "./ui";

type VirtualBaseProps<T> = {
  items: T[];
  /** Row height in px */
  estimateSize: number;
  /** Scroll area height (px or any CSS length); omitted = fill the parent flex column (`min-h-0 flex-1`) */
  height?: number | string;
  /** Stable row key; defaults to the index */
  getKey?: (item: T, index: number) => string | number;
  onEndReached?: () => void;
  /** How many rows before the end onEndReached fires (default 5) */
  endThreshold?: number;
  /** Shows a spinner after the last row (or in place of the empty state while nothing has loaded) */
  loading?: boolean;
  /** Shown when there are no items and nothing is loading */
  empty?: React.ReactNode;
  overscan?: number;
  className?: string;
};

/** Shared virtualiser setup: the scroll element, the virtualiser and the end-reached trigger. */
function useVirtualRows<T>(
  { items, estimateSize, getKey, onEndReached, endThreshold = 5, loading, overscan = 8 }: VirtualBaseProps<T>,
  scrollMargin = 0,
) {
  const scrollRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Virtual returns fresh functions each render
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => estimateSize,
    getItemKey: getKey ? (i) => getKey(items[i], i) : undefined,
    overscan,
    scrollMargin,
  });
  const rows = virtualizer.getVirtualItems();
  const lastIndex = rows.length ? rows[rows.length - 1].index : -1;

  const endReached = useRef(onEndReached);
  useEffect(() => {
    endReached.current = onEndReached;
  }, [onEndReached]);
  useEffect(() => {
    if (!loading && items.length > 0 && lastIndex >= items.length - 1 - endThreshold) endReached.current?.();
  }, [lastIndex, items.length, endThreshold, loading]);

  return { scrollRef, virtualizer, rows };
}

function scrollStyle(height: number | string | undefined): { className: string; style?: React.CSSProperties } {
  return height == null ? { className: "min-h-0 flex-1" } : { className: "", style: { height } };
}

function Footer({ loading, isEmpty, empty }: { loading?: boolean; isEmpty: boolean; empty?: React.ReactNode }) {
  if (loading)
    return (
      <div className={`flex justify-center ${isEmpty ? "py-12" : "py-3"}`}>
        <Spinner className={isEmpty ? "h-6 w-6" : "h-4 w-4"} />
      </div>
    );
  if (isEmpty) return <>{empty ?? <EmptyState title="Nothing here yet" />}</>;
  return null;
}

/** A virtualised vertical list; `renderRow` draws one row inside a box of exactly `estimateSize` px. */
export function VirtualList<T>(
  props: VirtualBaseProps<T> & { renderRow: (item: T, index: number) => React.ReactNode },
) {
  const { items, estimateSize, height, loading, empty, className = "", renderRow } = props;
  const { scrollRef, virtualizer, rows } = useVirtualRows(props);
  const scroll = scrollStyle(height);

  return (
    <div ref={scrollRef} className={`overflow-y-auto ${scroll.className} ${className}`} style={scroll.style}>
      <div className="relative w-full" style={{ height: virtualizer.getTotalSize() }}>
        {rows.map((row) => (
          <div
            key={row.key}
            className="absolute left-0 top-0 w-full"
            style={{ height: estimateSize, transform: `translateY(${row.start}px)` }}
          >
            {renderRow(items[row.index], row.index)}
          </div>
        ))}
      </div>
      <Footer loading={loading} isEmpty={items.length === 0} empty={empty} />
    </div>
  );
}

export type VirtualColumn<T> = {
  key: string;
  header: React.ReactNode;
  /** CSS grid track, e.g. "8rem", "2fr", "minmax(10rem,1fr)" (default "minmax(0,1fr)") */
  width?: string;
  /** Extra classes for this column's header and cells (alignment, tabular-nums …) */
  className?: string;
  render: (item: T, index: number) => React.ReactNode;
};

const HEADER_HEIGHT = 36; // h-9

/**
 * A virtualised table built on CSS grid (table rows can't be absolutely positioned): sticky header, fixed-height
 * rows, optional row click and a highlighted selected row.
 */
export function VirtualTable<T>(
  props: VirtualBaseProps<T> & {
    columns: VirtualColumn<T>[];
    onRowClick?: (item: T, index: number) => void;
    isSelected?: (item: T, index: number) => boolean;
  },
) {
  const { items, estimateSize, height, loading, empty, className = "", columns, onRowClick, isSelected } = props;
  // The header sits inside the scroll area, so offset the rows by its height.
  const { scrollRef, virtualizer, rows } = useVirtualRows(props, HEADER_HEIGHT);
  const scroll = scrollStyle(height);
  const gridTemplateColumns = columns.map((c) => c.width ?? "minmax(0,1fr)").join(" ");

  return (
    <div
      ref={scrollRef}
      role="table"
      className={`overflow-auto ${scroll.className} ${className}`}
      style={scroll.style}
    >
      <div
        role="row"
        className="sticky top-0 z-10 grid h-9 items-center gap-3 border-b border-slate-100 bg-slate-50/95 px-4 text-[11px] font-semibold uppercase tracking-wide text-slate-500 backdrop-blur"
        style={{ gridTemplateColumns }}
      >
        {columns.map((c) => (
          <div key={c.key} role="columnheader" className={`truncate ${c.className ?? ""}`}>
            {c.header}
          </div>
        ))}
      </div>
      <div role="rowgroup" className="relative w-full" style={{ height: virtualizer.getTotalSize() }}>
        {rows.map((row) => {
          const item = items[row.index];
          const selected = isSelected?.(item, row.index) ?? false;
          return (
            <div
              key={row.key}
              role="row"
              aria-selected={isSelected ? selected : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              onClick={onRowClick && (() => onRowClick(item, row.index))}
              onKeyDown={
                onRowClick &&
                ((e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onRowClick(item, row.index);
                  }
                })
              }
              className={`absolute left-0 top-0 grid w-full items-center gap-3 border-b border-slate-100 px-4 text-sm text-slate-700 ${
                selected ? "bg-brand-50" : onRowClick ? "hover:bg-slate-50" : ""
              } ${onRowClick ? "cursor-pointer" : ""}`}
              style={{
                gridTemplateColumns,
                height: estimateSize,
                transform: `translateY(${row.start - virtualizer.options.scrollMargin}px)`,
              }}
            >
              {columns.map((c) => (
                <div key={c.key} role="cell" className={`min-w-0 truncate ${c.className ?? ""}`}>
                  {c.render(item, row.index)}
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <Footer loading={loading} isEmpty={items.length === 0} empty={empty} />
    </div>
  );
}
