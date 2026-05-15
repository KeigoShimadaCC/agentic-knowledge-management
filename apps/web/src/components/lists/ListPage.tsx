/**
 * @example
 * <ListPage title="Pages" actions={<Button>New</Button>} loading={isLoading} empty={items.length === 0} emptyTitle="No pages yet">
 *   {items.map(item => <Row key={item.id} item={item} />)}
 * </ListPage>
 */
"use client";

import * as React from "react";
import { Skeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { cn } from "@/lib/cn";

interface ListPageProps {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  toolbar?: React.ReactNode;
  loading?: boolean;
  error?: Error | string | null;
  onRetry?: () => void;
  empty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
  skeletonRows?: number;
  children?: React.ReactNode;
  className?: string;
}

export function ListPage({
  title,
  description,
  actions,
  toolbar,
  loading,
  error,
  onRetry,
  empty,
  emptyTitle,
  emptyDescription,
  emptyAction,
  skeletonRows = 5,
  children,
  className,
}: ListPageProps) {
  const resolvedError = error instanceof Error ? error : error ? new Error(error) : null;

  return (
    <div className={cn("p-8", className)}>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{title}</h1>
          {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>

      {toolbar && <div className="mb-2">{toolbar}</div>}

      {resolvedError ? (
        <ErrorState error={resolvedError} onRetry={onRetry} />
      ) : loading ? (
        <div className="space-y-2">
          {Array.from({ length: skeletonRows }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      ) : empty ? (
        <EmptyState
          title={emptyTitle ?? "Nothing here yet"}
          description={emptyDescription}
          action={emptyAction}
        />
      ) : (
        children
      )}
    </div>
  );
}
