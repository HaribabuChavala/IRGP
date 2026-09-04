import Link from "next/link";
import { FileBarChart2, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 px-4">
      <div className="mx-auto max-w-2xl text-center">
        <div className="mb-6 inline-flex items-center justify-center rounded-2xl bg-indigo-600 p-4 shadow-lg shadow-indigo-500/30">
          <FileBarChart2 className="h-10 w-10 text-white" />
        </div>
        <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
          Instant Report Generation Platform
        </h1>
        <p className="mt-4 text-lg text-slate-300">
          Connect data sources, ask questions in plain language, and export reports
          to Excel, PDF, or CSV — instantly.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link href="/login">
            <Button size="lg" className="min-w-[180px]">
              Sign in
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/login">
            <Button variant="outline" size="lg" className="min-w-[180px] border-slate-600 bg-transparent text-white hover:bg-slate-800">
              Platform Admin
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
