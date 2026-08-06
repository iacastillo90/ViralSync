"use client";

import { use } from "react";
import { PipelineMonitorView } from "@/features/Pipeline/views/PipelineMonitorView";

export default function PipelinePage({ params }) {
  const resolvedParams = use(params);
  return <PipelineMonitorView tenantId={resolvedParams.tenantId} />;
}
