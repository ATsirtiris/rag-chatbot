"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLogin, setIsLogin] = useState(true);
  const [mounted, setMounted] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setMounted(true);
    // If already logged in, redirect to home
    const token = localStorage.getItem("token");
    if (token) {
      router.push("/");
    }
  }, [router]);

  async function handleSubmit(e: any) {
    e.preventDefault();
    try {
      const url = `${process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"}/auth/${isLogin ? "login" : "signup"}`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        alert(errorData.detail || "Error");
        return;
      }
      
      const data = await res.json();
      if (data.access_token) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("username", username);
        router.push("/");
      } else {
        alert("No token received");
      }
    } catch (error: any) {
      alert(`Network error: ${error?.message || "Could not connect to server"}`);
    }
  }

  if (!mounted) {
    return (
      <main className="flex flex-col items-center justify-center min-h-screen bg-slate-900 text-white">
        <div className="text-white">Loading...</div>
      </main>
    );
  }

  return (
    <main className="flex flex-col items-center justify-center min-h-screen bg-slate-900 text-white">
      <div className="bg-slate-800 p-6 rounded-xl w-80">
        <h1 className="text-xl mb-4 text-center">
          {isLogin ? "Login" : "Sign Up"}
        </h1>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-3 py-2 rounded bg-slate-700 text-white"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 rounded bg-slate-700 text-white"
          />
          <button
            type="submit"
            className="w-full bg-sky-500 py-2 rounded hover:bg-sky-400 transition"
          >
            {isLogin ? "Login" : "Create Account"}
          </button>
        </form>
        <button
          onClick={() => setIsLogin(!isLogin)}
          className="mt-3 text-sm text-sky-400 underline w-full"
        >
          {isLogin ? "Need an account? Sign up" : "Already have an account? Login"}
        </button>
      </div>
    </main>
  );
}


