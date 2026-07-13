import type { Metadata } from "next";
import { Providers } from "./providers";
import "./globals.css";
import { Geist } from "next/font/google";
import { cn } from "@/lib/utils";
import { ThemeProvider } from "@/components/theme-provider";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

export const metadata: Metadata = {
  title: "StadiumPulse — Mission Control",
  description: "Real-time multi-agent stadium operations platform. Monitor crowd density, manage incidents, dispatch resources, and leverage AI-powered predictive insights.",
  keywords: ["stadium", "operations", "crowd management", "incident response", "AI", "real-time"],
  authors: [{ name: "StadiumPulse Team" }],
  openGraph: {
    title: "StadiumPulse — Mission Control",
    description: "Real-time multi-agent stadium operations platform.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning className={cn("font-sans", geist.variable)}>
      <body suppressHydrationWarning className="antialiased min-h-screen bg-background text-foreground">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <Providers>
            {children}
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  );
}
