"use client";

import { use } from "react";
import { LeadsKanbanView } from "@/features/LeadsInbound/views/LeadsKanbanView";

export default function LeadsPage({ params }) {
  const resolvedParams = use(params);
  return <LeadsKanbanView tenantId={resolvedParams.tenantId} />;
}
