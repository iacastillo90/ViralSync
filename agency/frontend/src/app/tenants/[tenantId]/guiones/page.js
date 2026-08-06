"use client";

import { use } from "react";
import { ScriptInspectorView } from "@/features/Scriptwriting/views/ScriptInspectorView";

export default function GuionesPage({ params }) {
  const resolvedParams = use(params);
  return <ScriptInspectorView tenantId={resolvedParams.tenantId} />;
}
