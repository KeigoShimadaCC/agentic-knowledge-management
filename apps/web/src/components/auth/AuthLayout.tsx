import { Logo } from "@/components/brand/Logo";

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen bg-gray-950">
      {/* Left panel — visible at lg+ */}
      <div className="hidden flex-col justify-between bg-surface-1 p-12 lg:flex lg:w-1/2 xl:w-2/5">
        <div className="flex items-center gap-3">
          <Logo size={36} />
          <span className="text-xl font-bold text-fg">KnowledgeOS</span>
        </div>
        <div>
          <blockquote className="text-lg leading-relaxed text-fg-muted">
            &ldquo;Your second brain — local, private, and AI-ready.&rdquo;
          </blockquote>
          <p className="mt-4 text-sm text-fg-subtle">All data stays on your machine. Always.</p>
        </div>
        <p className="text-xs text-fg-subtle">© {new Date().getFullYear()} KnowledgeOS</p>
      </div>

      {/* Right panel — full width on mobile, half width on lg+ */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12">
        {/* Mobile branding */}
        <div className="mb-8 flex items-center gap-2 lg:hidden">
          <Logo size={28} />
          <span className="text-lg font-bold text-white">KnowledgeOS</span>
        </div>

        <div className="w-full max-w-sm">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-white">{title}</h1>
            {subtitle && <p className="mt-1 text-sm text-gray-400">{subtitle}</p>}
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
