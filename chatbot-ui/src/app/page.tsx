"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Chat from "@/components/Chat";

export default function Page() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (!token) {
      router.push("/login");
    } else {
      setIsAuthenticated(true);
    }
  }, [router]);

  if (isAuthenticated === null) {
    return null; // Prevent flash of content
  }

  if (!isAuthenticated) {
    return null; // Will redirect
  }

  return (
    <main className="chat-page">
      <Chat />
    </main>
  );
}

