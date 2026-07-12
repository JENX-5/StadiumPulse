"use client";

import { Activity, Loader2, LockKeyhole } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError } from "@/lib/api-client";
import { ROLE_HOME_ROUTE } from "@/lib/auth-constants";
import { authApi } from "@/services/api";
import { useAuthStore } from "@/store/useAuthStore";

const DEMO_ACCOUNTS = [
  { label: "Admin", email: "admin@stadiumpulse.demo" },
  { label: "Dispatcher", email: "dispatcher@stadiumpulse.demo" },
  { label: "Volunteer", email: "volunteer@stadiumpulse.demo" },
  { label: "Fan", email: "fan@stadiumpulse.demo" },
];

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useAuthStore((state) => state.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("demo-password-change-me");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const { access_token } = await authApi.login(email, password);
      // Stash the token before the /auth/me call so apiRequest attaches it.
      login(access_token, { id: "", email, full_name: "", role: "fan", venue_id: null });
      const profile = await authApi.me();
      login(access_token, profile);

      const from = searchParams.get("from");
      router.push(from && from !== "/login" ? from : ROLE_HOME_ROUTE[profile.role]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <Activity className="h-5 w-5 text-primary" />
          </div>
          <span className="font-semibold text-lg tracking-tight text-foreground">
            StadiumPulse
          </span>
          <span className="text-xs uppercase font-bold tracking-wider text-muted-foreground">
            Mission Control
          </span>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Sign in</CardTitle>
            <CardDescription>Enter your credentials to access the operations dashboard.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="email" className="text-xs font-medium text-muted-foreground">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="username"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@stadiumpulse.demo"
                  className="h-9 rounded-lg border border-border bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label htmlFor="password" className="text-xs font-medium text-muted-foreground">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="h-9 rounded-lg border border-border bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
                />
              </div>

              {error && (
                <p className="text-xs text-destructive" role="alert">
                  {error}
                </p>
              )}

              <Button type="submit" disabled={isSubmitting} className="mt-1 w-full">
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <LockKeyhole className="h-4 w-4" />
                )}
                Sign in
              </Button>
            </form>

            <div className="mt-4 border-t border-border/60 pt-3">
              <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Demo accounts
              </p>
              <div className="flex flex-wrap gap-1.5">
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => setEmail(account.email)}
                    className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                  >
                    {account.label}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-[11px] text-muted-foreground">
                Password for all demo accounts: <code>demo-password-change-me</code>
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
