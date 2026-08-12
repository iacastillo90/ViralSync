import { redirect } from "next/navigation";

export default async function TenantRootPage({ params }) {
  const { tenantId } = await params;
  redirect(`/tenants/${tenantId}/pipeline`);
}
