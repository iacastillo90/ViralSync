import { use } from "react";
import { MediaGalleryView } from "@/features/Media/views/MediaGalleryView";

export default function MediaPage({ params }) {
  const resolvedParams = use(params);
  return <MediaGalleryView tenantId={resolvedParams.tenantId} />;
}
