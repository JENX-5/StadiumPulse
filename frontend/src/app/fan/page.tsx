"use client";

import { Activity, LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/store/useAuthStore";

export default function FanPage() {
  const { user, logout } = useAuthStore();

  return (
    <div className="flex h-screen w-screen flex-col items-center justify-center gap-4 bg-background p-4 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
        <Activity className="h-5 w-5 text-primary" />
      </div>

      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Welcome{user?.full_name ? `, ${user.full_name}` : ""}</CardTitle>
          <CardDescription>
            The live operations dashboard is reserved for venue staff. Check back here for
            event updates and venue information.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" size="sm" onClick={logout} className="w-full">
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
