import type { EdgeWithObjectsOut, ObjectOut, RelatedObjectOut } from "@/types";

export const sampleObject: ObjectOut = {
  id: "object-1",
  user_id: "user-1",
  kind: "page",
  title: "Untitled Page",
  description: null,
  tags: [],
  metadata: {},
  is_pinned: false,
  is_archived: false,
  ai_generated: false,
  created_at: "2026-05-15T00:00:00Z",
  updated_at: "2026-05-15T00:00:00Z",
  deleted_at: null,
};

export const sampleBacklinks: EdgeWithObjectsOut[] = [
  {
    id: "edge-1",
    kind: "links_to",
    weight: 1,
    source_id: "page-2",
    target_id: "page-1",
    source_object: { id: "page-2", kind: "page", title: "Source Page" },
    target_object: { id: "page-1", kind: "page", title: "Target Page" },
    created_at: "2026-05-15T00:00:00Z",
  },
];

export const sampleRelated: RelatedObjectOut[] = [
  {
    id: "source-1",
    kind: "source",
    title: "Related Source",
    distance: 1,
    edge_kind: "cites",
    direction: "outgoing",
  },
];
