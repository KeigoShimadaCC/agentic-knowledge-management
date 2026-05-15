import { Spinner } from "@/components/ui/Spinner";

export default function AppLoading() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Spinner size="lg" />
    </div>
  );
}
