import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

export interface TableLayout {
  numeric: boolean[];
  stickyFirstColumn: boolean;
}

export const TableLayoutContext = createContext<TableLayout>({ numeric: [], stickyFirstColumn: false });

export function useTableLayout(): TableLayout {
  return useContext(TableLayoutContext);
}

interface ScrollableTableProps {
  layout: TableLayout;
  children: React.ReactNode;
}

/** Horizontally scrollable table shell with edge fades that appear only while more content is off-screen. */
export const ScrollableTable: React.FC<ScrollableTableProps> = ({ layout, children }) => {
  const scroller = useRef<HTMLDivElement>(null);
  const [edges, setEdges] = useState({ left: false, right: false });

  const measure = useCallback(() => {
    const el = scroller.current;
    if (!el) return;
    const left = el.scrollLeft > 2;
    const right = el.scrollLeft + el.clientWidth < el.scrollWidth - 2;
    setEdges((prev) => (prev.left === left && prev.right === right ? prev : { left, right }));
  }, []);

  useEffect(() => {
    measure();
    const el = scroller.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    if (el.firstElementChild) observer.observe(el.firstElementChild);
    return () => observer.disconnect();
  }, [measure, children]);

  return (
    <div className="relative my-4 overflow-hidden rounded-xl border border-white/10 bg-slate-950/70 shadow-[0_12px_32px_-18px_rgba(0,0,0,0.8)]">
      <div
        ref={scroller}
        onScroll={measure}
        role="region"
        aria-label="Data table, scrolls horizontally"
        tabIndex={0}
        className="overflow-x-auto overscroll-x-contain [scrollbar-color:rgba(56,189,248,0.4)_transparent] [scrollbar-width:thin]"
      >
        <TableLayoutContext.Provider value={layout}>
          <table className="w-max min-w-full border-separate border-spacing-0 text-[13px] leading-snug">{children}</table>
        </TableLayoutContext.Provider>
      </div>
      <div
        aria-hidden="true"
        className={`pointer-events-none absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-slate-950 to-transparent transition-opacity duration-200 ${
          edges.left ? 'opacity-100' : 'opacity-0'
        }`}
      />
      <div
        aria-hidden="true"
        className={`pointer-events-none absolute inset-y-0 right-0 w-10 bg-gradient-to-l from-slate-950 to-transparent transition-opacity duration-200 ${
          edges.right ? 'opacity-100' : 'opacity-0'
        }`}
      />
    </div>
  );
};
