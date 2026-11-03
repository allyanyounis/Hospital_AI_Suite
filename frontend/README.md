# Hospital AI Suite — frontend

Next.js 16 (App Router) + React 19 + Tailwind 4. Talks to the FastAPI backend through `/api/*`, which the Next
server proxies to `BACKEND_URL`; WebSockets (`/api/events`, live transcription) connect to the backend directly.

## Run

```bash
cp .env.example .env.local   # then fill in the VAPI keys (optional)
npm install
npm run dev                  # http://localhost:3004 (backend expected on :8000)
```

| Script | What it does |
|---|---|
| `npm run dev` | Dev server on port 3004 |
| `npm run build` / `npm start` | Production build / serve it on 3004 |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | ESLint (Next + TypeScript rules) |
| `npm run format` | Prettier over `src` (`npx prettier --check src` in CI) |

## Environment

All in `.env.local` (see `.env.example`). Browser-visible values are read in exactly one place,
[src/config/env.ts](src/config/env.ts); never read `process.env.NEXT_PUBLIC_*` anywhere else.

| Variable | Side | Purpose |
|---|---|---|
| `NEXT_PUBLIC_VAPI_PUBLIC_KEY`, `NEXT_PUBLIC_VAPI_ASSISTANT_ID` | browser | VAPI voice agent; empty disables it |
| `NEXT_PUBLIC_BACKEND_WS_URL` | browser | Full WebSocket base (other host / HTTPS) |
| `NEXT_PUBLIC_BACKEND_PORT` | browser | Backend port for WebSockets when no full URL is set (default 8000) |
| `BACKEND_URL` | server | Proxy target for `/api/*` (default `http://localhost:8000`) |

## Layout

```
src/
├── app/                    Routes only: each page.tsx renders one view from a feature
├── config/env.ts           The only reader of NEXT_PUBLIC_* variables
├── shared/                 Used by every feature; imports nothing from features/
│   ├── api/                http.ts (fetch wrapper, UnauthorizedError, wsUrl()), React Query client, Page<T> cursors
│   ├── live/               LiveEventsProvider: /api/events messages invalidate React Query keys by prefix
│   ├── ui/                 ui.tsx (cards, notices, tabs…), overlays.tsx (Modal, Drawer), virtual.tsx
│   │                       (VirtualList, VirtualTable for long paged lists), Sparkline.tsx, icons.tsx
│   ├── hooks/              useMounted, useNow
│   └── lib/                format.ts (dates, durations), theme.ts (chart colours)
└── features/
    ├── registry.ts         The feature registry: every feature's routes (see below)
    ├── auth/               Session, roles + permissions, access map (derived), RouteGuard, LoginView
    ├── shell/              AppShell (sidebar + top bar); navigation derived from the registry
    ├── dashboard/          OverviewView (/)
    ├── patients/           Patient registry (/patients): search, register, edit; PatientPicker
    ├── clinical/           Patient chart (/patients/[id]): labs, vitals, reports, history; ClinicalRecord
    ├── theatre/            Operating theatres: board, case, book, surgeons, insights (/theatre/*)
    ├── appointments/       OPD appointments (/appointments) from every channel; desk booking; live events
    ├── scribe/             AI scribe: SessionView, BoardView, EncountersView, MetricsView (/scribe/*)
    ├── reception/          AI voice receptionist (a booking channel): AgentView, MonitoringView (call costs)
    ├── schedule/           Each doctor's OPD week + hospital closed dates (/schedule)
    ├── staff/              Staff directory and profiles (/staff); StaffProfileForm
    ├── organization/       Departments (/admin/departments)
    ├── users/              Account management (/admin/users)
    ├── portal/             A patient's own details and appointments (/portal)
    └── account/            AccountView, change-password form (/account)
```

Each feature folder holds `routes.ts` (its pages), `api.ts` (its backend endpoints), `types.ts` (its data
contracts), `components/`, `views/` (one per route) and an `index.ts` barrel.

## Feature registry

Every page is declared once, by the feature that owns it, in `features/<name>/routes.ts`:

```ts
export const routes: RouteDef[] = [
  { path: "/staff", permission: "staff.view", nav: { group: "Hospital", label: "Staff", icon: Icons.UserCog, order: 20 } },
];
```

[features/registry.ts](src/features/registry.ts) collects them. Two things are derived from it, so nothing else
keeps a list of pages:

- **Access:** `routeFor(path)` in `features/auth/access.ts` finds the longest matching `path`; its `permission`
  decides who may open the page (`null` = any signed-in user). `RouteGuard` enforces it.
- **Navigation:** `navigationFor(user)` in `features/shell/navigation.ts` builds the sidebar from routes that have a
  `nav` entry and that the user may open, grouped by `NAV_GROUPS` (Overview, Patients, Clinical, Theatres, Front
  desk, Hospital, Me) and sorted by `order`. Routes without `nav` (e.g. a redirect) take an optional `title`.

`routes.ts` holds plain data (path, permission, label, icon) and imports only `shared/` and types, which is why the
registry may import it directly: it is the one exception to the barrel rule and never creates an import cycle.

## Adding a hospital module (e.g. laboratory)

1. Backend first: the module's endpoints and permissions (see `backend/README.md`).
2. Add the new permission strings to `Permission` in `features/auth/types.ts`.
3. Create `src/features/laboratory/` with `api.ts`, `types.ts`, `components/`, `views/`, `index.ts` and
   `routes.ts` (path, permission, nav group/label/icon/order).
4. Add one line to `features/registry.ts`.
5. Add `app/(app)/laboratory/page.tsx` that renders the view from `@/features/laboratory`.

The sidebar link and the access check follow from step 4; no other file changes.

## Module rules

1. **Routes are thin.** `app/**/page.tsx` imports a view from a feature barrel and renders it. No logic in routes.
2. **A feature owns its slice.** Endpoints, types, components and views for one domain live in its folder.
3. **Cross-feature imports go through the barrel**: `import { useSession } from "@/features/auth"`, never
   `@/features/auth/components/...`. Inside a feature, use relative imports (`../api`), never your own barrel.
   Only `features/registry.ts` imports other features' `routes.ts` directly.
4. **No cycles.** Current direction: `dashboard → appointments, schedule, scribe`; `appointments → patients, staff,
   schedule`; `reception → appointments, staff`; `schedule → staff`; `staff → organization`; `users → staff,
   patients`; `theatre → clinical, patients`; `clinical → patients`; everything → `auth`; `auth`, `organization`, `patients`, `portal` import no other feature (types
   only). If two features need each other, move the shared part to `shared/`.
5. **`shared/` is feature-free.** It must not import from `features/`.
6. **Env only via `config/env.ts`.**

## Access control

Five roles sign in: **admin**, **doctor**, **nurse**, **receptionist** and **patient**. The backend owns the role →
permission matrix and sends the signed-in user's `permissions` with `/api/login`, `/api/me` and `/api/session`; the
frontend never decides access from the role name (roles are only displayed).

| Permission | Unlocks |
|---|---|
| `dashboard.view` | Overview (`/`) |
| `patients.view` / `patients.manage` | `/patients`, patient search in the top bar / registering and editing patients |
| `appointments.view` / `appointments.manage` / `appointments.book` | `/appointments` / Cancel buttons / "New appointment" |
| `scribe.use` | `/scribe/*`, "New Session" |
| `voice_agent.use` | `/reception/agent` |
| `schedule.view` / `schedule.edit` | `/schedule` / editing doctors' hours and closed dates (read-only otherwise) |
| `staff.view` / `staff.manage` | `/staff` / editing staff profiles |
| `organization.manage` | `/admin/departments` |
| `users.manage` | `/admin/users` |
| `metrics.view_all` | "All clinicians" on Pilot Metrics |
| `call_costs.view` | `/reception/monitoring` |
| `portal.use` | `/portal` (patients; their home page) |
| `clinical.view` | The clinical tabs of `/patients/[id]` and a theatre case's "Patient record" tab |
| `theatre.view` / `theatre.manage` | `/theatre`, `/theatre/cases/*`, `/theatre/surgeons` / `/theatre/book`, case actions, "Add emergency" |
| `theatre.roster` / `theatre.insights` | Editing rosters and leave on `/theatre/surgeons` / `/theatre/insights` |

- **Pages:** declared in each feature's `routes.ts` (see Feature registry). No access shows a "You don't have
  access" page, and `/` sends patients to `/portal`.
- **Buttons and widgets:** `const { can } = useSession(); can("schedule.edit")`. Don't call APIs the user can't
  use (see `useAppointments(enabled)` on the overview).
- **After sign-in:** the user goes back to `?next=` only if they may open it, otherwise to their home
  (`homePath`: `/portal` for patients, `/` for staff).
- The UI only mirrors access; the backend checks the same permission on every request (403 otherwise).

Changing the colours: edit the `--color-brand-*` scale in `src/app/globals.css` and the matching hex values in
`src/shared/lib/theme.ts` (used by charts).
