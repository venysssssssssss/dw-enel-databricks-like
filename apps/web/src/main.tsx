import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, createRoute, createRootRoute, createRouter, Outlet } from "@tanstack/react-router";
import { reportWebVitals } from "./lib/web-vitals";
import { Shell } from "./components/shared/Shell";
import { features } from "./lib/features";
import "./styles.css";

const ChatRoute = lazy(() => import("./app/routes/chat").then((module) => ({ default: module.ChatRoute })));
const MisRoute = lazy(() => import("./app/routes/bi.mis").then((module) => ({ default: module.MisRoute })));
const ExecutiveRoute = lazy(() =>
  import("./app/routes/bi.executive").then((module) => ({ default: module.ExecutiveRoute }))
);
const PatternsRoute = lazy(() =>
  import("./app/routes/bi.patterns").then((module) => ({ default: module.PatternsRoute }))
);
const ImpactRoute = lazy(() =>
  import("./app/routes/bi.impact").then((module) => ({ default: module.ImpactRoute }))
);
const TaxonomyRoute = lazy(() =>
  import("./app/routes/bi.taxonomy").then((module) => ({ default: module.TaxonomyRoute }))
);
const CeTotaisRoute = lazy(() =>
  import("./app/routes/bi.ce-totais").then((module) => ({ default: module.CeTotaisRoute }))
);
const GovernanceRoute = lazy(() =>
  import("./app/routes/bi.governance").then((module) => ({ default: module.GovernanceRoute }))
);
const EducationalRoute = lazy(() =>
  import("./app/routes/bi.educational").then((module) => ({ default: module.EducationalRoute }))
);
const SeveridadeAltaRoute = lazy(() =>
  import("./app/routes/bi.severidade").then((module) => ({ default: module.SeveridadeAltaRoute }))
);
const SeveridadeCriticaRoute = lazy(() =>
  import("./app/routes/bi.severidade").then((module) => ({ default: module.SeveridadeCriticaRoute }))
);

function RouteBoundary({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<div className="route-loading">Carregando...</div>}>{children}</Suspense>;
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 600_000,
      refetchOnWindowFocus: false
    }
  }
});

const rootRoute = createRootRoute({
  component: () => (
    <Shell>
      <Outlet />
    </Shell>
  )
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: () => (
    <RouteBoundary>
      <ChatRoute />
    </RouteBoundary>
  )
});

const chatRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/chat",
  component: () => (
    <RouteBoundary>
      <ChatRoute />
    </RouteBoundary>
  )
});

const misRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bi/mis",
  component: () => (
    <RouteBoundary>
      <MisRoute />
    </RouteBoundary>
  )
});

const executiveRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bi/executive",
  component: () => (
    <RouteBoundary>
      <ExecutiveRoute />
    </RouteBoundary>
  )
});

const patternsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bi/patterns",
  component: () => (
    <RouteBoundary>
      <PatternsRoute />
    </RouteBoundary>
  )
});

const impactRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bi/impact",
  component: () => (
    <RouteBoundary>
      <ImpactRoute />
    </RouteBoundary>
  )
});

const taxonomyRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bi/taxonomy",
  component: () => (
    <RouteBoundary>
      <TaxonomyRoute />
    </RouteBoundary>
  )
});

const ceTotaisRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bi/ce-totais",
  component: () => (
    <RouteBoundary>
      <CeTotaisRoute />
    </RouteBoundary>
  )
});

const governanceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bi/governance",
  component: () => (
    <RouteBoundary>
      <GovernanceRoute />
    </RouteBoundary>
  )
});

const educationalRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bi/educational",
  component: () => (
    <RouteBoundary>
      <EducationalRoute />
    </RouteBoundary>
  )
});

const severidadeAltaRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bi/severidade-alta",
  component: () => (
    <RouteBoundary>
      <SeveridadeAltaRoute />
    </RouteBoundary>
  )
});

const severidadeCriticaRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bi/severidade-critica",
  component: () => (
    <RouteBoundary>
      <SeveridadeCriticaRoute />
    </RouteBoundary>
  )
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  chatRoute,
  misRoute,
  executiveRoute,
  patternsRoute,
  impactRoute,
  taxonomyRoute,
  ceTotaisRoute,
  governanceRoute,
  educationalRoute,
  ...(features.severidadeV1 ? [severidadeAltaRoute, severidadeCriticaRoute] : [])
]);

const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>
);

reportWebVitals();
