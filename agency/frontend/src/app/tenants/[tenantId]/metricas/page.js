"use client";

import { use } from "react";
import { MetricsDashboardView } from "@/features/Metrics72h/views/MetricsDashboardView";

export default function MetricasPage({ params }) {
  const resolvedParams = use(params);
  return <MetricsDashboardView tenantId={resolvedParams.tenantId} />;
}
