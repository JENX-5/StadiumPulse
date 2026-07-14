import type { Metadata } from "next";
import { Providers } from "./providers";
import "./globals.css";
import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";
import { ThemeProvider } from "@/components/theme-provider";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

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
    <html lang="en" suppressHydrationWarning className={cn("font-sans", inter.variable)}>
      <body suppressHydrationWarning className="antialiased min-h-screen bg-background text-foreground">
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
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
