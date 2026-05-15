import Link from "next/link";
import { AuthLayout } from "@/components/auth/AuthLayout";

export const metadata = { title: "Reset password — KnowledgeOS" };

export default function ForgotPasswordPage() {
  return (
    <AuthLayout title="Reset password" subtitle="KnowledgeOS is local-first — passwords are reset via the CLI.">
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-5 text-sm text-gray-300 space-y-3">
        <p>Since KnowledgeOS runs entirely on your machine, password resets work through the command line:</p>
        <pre className="rounded bg-gray-950 px-3 py-2 font-mono text-xs text-green-400 overflow-x-auto">
          kos-cli user reset-password --email you@example.com
        </pre>
        <p className="text-gray-400 text-xs">The CLI ships with your Docker Compose stack under <code className="text-gray-300">scripts/kos-cli</code>.</p>
      </div>
      <p className="mt-4 text-center text-sm text-gray-500">
        Remember your password?{" "}
        <Link href="/login" className="text-indigo-400 hover:underline">Sign in</Link>
      </p>
    </AuthLayout>
  );
}
