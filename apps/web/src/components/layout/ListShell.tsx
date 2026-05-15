/**
 * Wraps list loading / error / empty states.
 * @example
 * <ListShell loading={isLoading} error={error} empty={!data?.length} emptyTitle="No items">
 *   {data?.map(item => <Row key={item.id} />)}
 * </ListShell>
 */
import * as React from "react";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { cn } from "@/lib/cn";

export interface ListShellProps extends React.HTMLAttributes<HTMLDivElement> {
  loading?: boolean;
  error?: Error | string | null;
  onRetry?: () => void;
  empty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;
  skeletonRows?: number;
}

export function ListShell({
  loading,
  error,
  onRetry,
  empty,
  emptyTitle = "Nothing here yet",
  emptyDescription,
  emptyAction,
  skeletonRows = 5,
  children,
  className,
  ...props
}: ListShellProps) {
  if (loading) {
    return (
      <div className={cn("flex flex-col gap-2", className)} {...props}>
        {Array.from({ length: skeletonRows }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }
  if (error) {
    return <ErrorState error={error} onRetry={onRetry} className={className} />;
  }
  if (empty) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        action={emptyAction}
        className={className}
      />
    );
  }
  return (
    <div className={cn(className)} {...props}>
      {children}
    </div>
  );
}
