"use client";

import { use } from "react";
import { InboundLeadsView } from "@/features/LeadsInbound/views/InboundLeadsView";

export default function LeadsPage({ params }) {
  const resolvedParams = use(params);
  return <InboundLeadsView tenantId={resolvedParams.tenantId} />;
}
