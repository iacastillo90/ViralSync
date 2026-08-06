"use client";

import { use } from "react";
import { PublishApprovalView } from "@/features/VideoPreview/views/PublishApprovalView";

export default function PublicacionPage({ params }) {
  const resolvedParams = use(params);
  return <PublishApprovalView tenantId={resolvedParams.tenantId} />;
}
