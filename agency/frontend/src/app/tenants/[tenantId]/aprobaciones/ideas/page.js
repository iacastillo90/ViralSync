"use client";

import { use } from "react";
import { IdeaApprovalView } from "@/features/Ideation/views/IdeaApprovalView";

export default function IdeasPage({ params }) {
  const resolvedParams = use(params);
  return <IdeaApprovalView tenantId={resolvedParams.tenantId} />;
}
