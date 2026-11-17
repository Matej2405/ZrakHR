import { createBrowserRouter, type RouteObject } from 'react-router'

import { AppShell } from './components/AppShell'
import { AnalysisPage } from './pages/AnalysisPage'
import { DashboardPage } from './pages/DashboardPage'
import { ErrorPage } from './pages/ErrorPage'
import { MapPage } from './pages/MapPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { StatusPage } from './pages/StatusPage'

/** Rute aplikacije; odvojene od routera kako bi ih testovi mogli koristiti s memorijskim routerom. */
export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      {
        // Greška unutar stranice prikazuje se u okviru aplikacije, pa navigacija ostaje dostupna
        errorElement: <ErrorPage />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: 'karta', element: <MapPage /> },
          { path: 'analiza', element: <AnalysisPage /> },
          { path: 'status', element: <StatusPage /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
