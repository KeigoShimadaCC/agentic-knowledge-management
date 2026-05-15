import Link from "next/link";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { LoginForm } from "@/components/auth/LoginForm";

export const metadata = { title: "Sign in — KnowledgeOS" };

export default function LoginPage() {
  return (
    <AuthLayout title="Sign in to KnowledgeOS" subtitle="Your local-first AI knowledge base.">
      <LoginForm />
      <p className="mt-4 text-center text-sm text-gray-500">
        No account?{" "}
        <Link href="/register" className="text-indigo-400 hover:underline">Register</Link>
        {" · "}
        <Link href="/forgot-password" className="text-indigo-400 hover:underline">Forgot password?</Link>
      </p>
    </AuthLayout>
  );
}
