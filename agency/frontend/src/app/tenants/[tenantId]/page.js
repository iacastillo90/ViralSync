import { DashboardView } from "@/features/Dashboard/views/DashboardView";

export default async function TenantRootPage({ params }) {
  const { tenantId } = await params;
  return <DashboardView tenantId={tenantId} />;
}
