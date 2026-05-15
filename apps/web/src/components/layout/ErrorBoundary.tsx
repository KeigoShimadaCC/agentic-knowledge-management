"use client";
import * as React from "react";
import { ErrorState } from "@/components/ui/ErrorState";

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode; fallback?: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  override render() {
    if (this.state.error) {
      return (
        this.props.fallback ?? (
          <ErrorState
            error={this.state.error}
            onRetry={() => this.setState({ error: null })}
            className="min-h-[40vh]"
          />
        )
      );
    }
    return this.props.children;
  }
}
