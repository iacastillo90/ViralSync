"use client";

import { use } from "react";
import { BrainManagementView } from "@/features/RAGBrain/views/BrainManagementView";

export default function CerebroPage({ params }) {
  const resolvedParams = use(params);
  return <BrainManagementView tenantId={resolvedParams.tenantId} />;
}
