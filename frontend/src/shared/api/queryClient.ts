/**
 * The app's TanStack Query client. Defaults: data is fresh for 30s, refetched when the window regains focus,
 * failed requests retried once - except "not signed in" (UnauthorizedError), which is never retried and sends the
 * user to /login, exactly like SessionProvider does on first load.
 *
 * Query keys start with the feature name (["appointments", ...], ["theatre", ...], ["clinical", ...]) so a live
 * event can invalidate a whole feature by prefix (see shared/live/LiveEventsProvider.tsx).
 */

import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";
import { UnauthorizedError } from "./http";

/** `onUnauthorized` runs when any query or mutation fails with UnauthorizedError (session expired). */
export function makeQueryClient(onUnauthorized: () => void): QueryClient {
  const onError = (error: unknown) => {
    if (error instanceof UnauthorizedError) onUnauthorized();
  };
  return new QueryClient({
    queryCache: new QueryCache({ onError }),
    mutationCache: new MutationCache({ onError }),
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: true,
        retry: (failureCount, error) => !(error instanceof UnauthorizedError) && failureCount < 1,
      },
      mutations: { retry: false },
    },
  });
}
