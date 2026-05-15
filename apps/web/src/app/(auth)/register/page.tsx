import Link from "next/link";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata = { title: "Create account — KnowledgeOS" };

export default function RegisterPage() {
  return (
    <AuthLayout title="Create your account" subtitle="Set up your local KnowledgeOS instance.">
      <RegisterForm />
      <p className="mt-4 text-center text-sm text-gray-500">
        Already have an account?{" "}
        <Link href="/login" className="text-indigo-400 hover:underline">Sign in</Link>
      </p>
    </AuthLayout>
  );
}
