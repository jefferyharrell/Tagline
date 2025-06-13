import { redirect } from "next/navigation";

export default function DebugAuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Server-side production guard
  if (process.env.NODE_ENV !== "development") {
    redirect("/");
  }

  return <>{children}</>;
}