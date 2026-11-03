/** Cursor pagination, as the backend's list endpoints return it: a page of items and the cursor for the next one. */

export type Page<T> = { items: T[]; next_cursor: string | null };

/**
 * The cursor options for `useInfiniteQuery` over a Page<T> endpoint:
 *   useInfiniteQuery({ queryKey, queryFn: ({ pageParam }) => api.list(pageParam), ...cursorPagination<Row>() })
 * `pageParam` is null for the first page, then each page's next_cursor; a null cursor means no more pages.
 */
export function cursorPagination<T>() {
  return {
    initialPageParam: null as string | null,
    getNextPageParam: (page: Page<T>) => page.next_cursor ?? undefined,
  };
}

/** All items of the pages loaded so far, in order (`data` from useInfiniteQuery). */
export function flattenPages<T>(data: { pages: Page<T>[] } | undefined): T[] {
  return data ? data.pages.flatMap((p) => p.items) : [];
}
