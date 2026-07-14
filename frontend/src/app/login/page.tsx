"use client";

import { Activity, Loader2, ArrowRight } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

import { Button } from "@/components/ui/button";
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

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useAuthStore((state) => state.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
    <div className="relative flex min-h-[100dvh] w-full items-center justify-center overflow-hidden bg-background selection:bg-primary/30">
      {/* Premium Background Effects */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-[20%] -left-[10%] h-[50%] w-[50%] rounded-full bg-primary/10 blur-[120px]" />
        <div className="absolute top-[20%] -right-[10%] h-[40%] w-[40%] rounded-full bg-cyan-500/10 blur-[120px]" />
        <div className="absolute -bottom-[20%] left-[20%] h-[50%] w-[60%] rounded-full bg-blue-500/5 blur-[120px]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(255,255,255,0.03),_transparent_50%),linear-gradient(180deg,rgba(255,255,255,0.02),transparent_20%)] dark:bg-[radial-gradient(circle_at_center,_rgba(255,255,255,0.04),_transparent_50%),linear-gradient(180deg,rgba(255,255,255,0.01),transparent_20%)]" />
      </div>

      <div className="relative z-10 w-full max-w-[420px] px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
          className="mb-8 flex flex-col items-center gap-3 text-center"
        >
          <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 ring-1 ring-primary/20 backdrop-blur-xl">
            <div className="absolute inset-0 rounded-2xl bg-primary/10 blur-xl transition-all duration-500 group-hover:bg-primary/20" />
            <Activity className="relative h-7 w-7 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              StadiumPulse
            </h1>
            <p className="text-xs font-bold tracking-[0.2em] text-muted-foreground uppercase mt-1">
              Mission Control
            </p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: [0.23, 1, 0.32, 1] }}
        >
          <div className="overflow-hidden rounded-3xl border border-white/10 bg-white/50 shadow-2xl backdrop-blur-xl dark:bg-black/40">
            <div className="px-8 pt-8 pb-6">
              <h2 className="text-xl font-semibold tracking-tight">Welcome back</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Enter your credentials to access operations.
              </p>

              <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
                <div className="space-y-1.5">
                  <label htmlFor="email" className="text-xs font-medium text-foreground/80">
                    Email address
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    autoComplete="username"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="you@stadiumpulse.demo"
                    className="w-full h-11 rounded-xl border border-white/10 bg-white/50 px-4 text-sm outline-none transition-all placeholder:text-muted-foreground/50 focus:border-primary/50 focus:bg-white/80 focus:ring-4 focus:ring-primary/10 dark:bg-black/50 dark:focus:bg-black/80"
                  />
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <label htmlFor="password" className="text-xs font-medium text-foreground/80">
                      Password
                    </label>
                  </div>
                  <input
                    id="password"
                    type="password"
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="••••••••"
                    className="w-full h-11 rounded-xl border border-white/10 bg-white/50 px-4 text-sm outline-none transition-all placeholder:text-muted-foreground/50 focus:border-primary/50 focus:bg-white/80 focus:ring-4 focus:ring-primary/10 dark:bg-black/50 dark:focus:bg-black/80"
                  />
                </div>

                <AnimatePresence mode="wait">
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="text-xs font-medium text-destructive overflow-hidden"
                    >
                      <div className="rounded-lg bg-destructive/10 px-3 py-2 mt-1">
                        {error}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                <Button 
                  type="submit" 
                  disabled={isSubmitting} 
                  className="mt-2 h-11 w-full rounded-xl bg-primary text-primary-foreground transition-all hover:brightness-110 active:scale-[0.98]"
                >
                  {isSubmitting ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <>
                      Sign in to Dashboard
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </>
                  )}
                </Button>
              </form>
            </div>

            <div className="border-t border-white/10 bg-black/5 px-8 py-6 dark:bg-white/5">
              <p className="mb-3 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">
                Quick Demo Access
              </p>
              <div className="grid grid-cols-2 gap-2">
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => {
                      setEmail(account.email);
                      setPassword("demo-password-change-me");
                    }}
                    className="flex items-center justify-center rounded-lg border border-white/10 bg-white/40 px-3 py-2 text-xs font-medium text-foreground transition-all hover:bg-white/60 hover:shadow-sm active:scale-[0.98] dark:bg-white/5 dark:hover:bg-white/10"
                  >
                    {account.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}
