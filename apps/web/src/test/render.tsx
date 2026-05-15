import type { ReactElement, ReactNode } from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { SWRConfig } from "swr";
import { WorkspaceLiteProvider } from "@/components/workspace/WorkspaceLiteProvider";

interface RenderWithProvidersOptions extends Omit<RenderOptions, "wrapper"> {
  withWorkspace?: boolean;
}

function Providers({
  children,
  withWorkspace = true,
}: {
  children: ReactNode;
  withWorkspace?: boolean;
}) {
  const content = withWorkspace ? (
    <WorkspaceLiteProvider>{children}</WorkspaceLiteProvider>
  ) : (
    children
  );

  return (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {content}
    </SWRConfig>
  );
}

export function renderWithProviders(
  ui: ReactElement,
  { withWorkspace = true, ...options }: RenderWithProvidersOptions = {}
) {
  return render(ui, {
    wrapper: ({ children }) => <Providers withWorkspace={withWorkspace}>{children}</Providers>,
    ...options,
  });
}
