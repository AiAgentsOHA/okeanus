# Okeanus Dashboard Build Progress

## Created So Far
1. `/Users/mikaeel/okeanus/dashboard/package.json` - dependencies
2. `/Users/mikaeel/okeanus/dashboard/next.config.js` - API proxy rewrites
3. `/Users/mikaeel/okeanus/dashboard/tsconfig.json` - TypeScript config
4. `/Users/mikaeel/okeanus/dashboard/tailwind.config.ts` - Theme colors, fonts, animations

## Remaining Files to Create
### Config
- `postcss.config.js`
- `src/app/globals.css`

### Core
- `src/lib/utils.ts` - cn() utility
- `src/lib/api.ts` - API client with all endpoints
- `src/lib/store.ts` - Zustand global store

### Layout
- `src/app/layout.tsx` - Root layout with nav rail
- `src/components/layout/Navbar.tsx` - Top bar
- `src/components/layout/Sidebar.tsx` - Left nav rail

### Pages (6 total)
1. `src/app/page.tsx` - Globe/Map view (deck.gl + maplibre)
2. `src/app/graph/page.tsx` - Knowledge graph (sigma.js)
3. `src/app/analytics/page.tsx` - Analytics dashboard (echarts)
4. `src/app/alerts/page.tsx` - Alerts table
5. `src/app/investigate/page.tsx` - Investigation chat
6. `src/app/lineage/page.tsx` - Data lineage

### Components
- `src/components/map/GlobeMap.tsx`
- `src/components/map/EntityDetail.tsx`
- `src/components/map/LayerControls.tsx`
- `src/components/map/AlertTicker.tsx`
- `src/components/graph/KnowledgeGraph.tsx`
- `src/components/charts/` - ECharts wrappers
- `src/components/alerts/AlertTable.tsx`
- `src/components/investigate/ChatInterface.tsx`
- `src/components/ui/` - Shared UI components

## Color Palette
- bg-deep: #0A0E17, bg-surface: #111827, bg-elevated: #1A2332
- accent-blue: #3B82F6, accent-cyan: #06B6D4, accent-emerald: #10B981
- accent-amber: #F59E0B, accent-red: #EF4444, accent-violet: #8B5CF6

## API Base
All calls go to /api/* which proxies to http://127.0.0.1:8000/*
