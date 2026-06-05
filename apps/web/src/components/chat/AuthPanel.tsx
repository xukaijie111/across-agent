"use client";

import { useCallback, useEffect, useState } from "react";
import { LogIn, LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  fetchMe,
  login,
  logout,
  type AuthUser,
} from "@/lib/auth";

type AuthPanelProps = {
  onAuthChange?: () => void;
};

export function AuthPanel({ onAuthChange }: AuthPanelProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchMe().then((me) => {
      setUser(me);
    });
  }, []);

  const handleLogin = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const me = await login(username.trim(), password);
      setUser(me);
      setPassword("");
      setShowForm(false);
      onAuthChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }, [username, password, onAuthChange]);

  const handleLogout = useCallback(async () => {
    await logout();
    setUser(null);
    onAuthChange?.();
  }, [onAuthChange]);

  if (user) {
    return (
      <div className="flex items-center gap-2">
        <span className="hidden text-xs text-muted-foreground sm:inline">
          {user.username} · {user.policy}
        </span>
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => void handleLogout()}>
          <LogOut className="size-3.5" />
          退出
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-end gap-2">
      {showForm ? (
        <div className="flex flex-col gap-2 rounded-lg border border-border/60 bg-card p-3 shadow-sm sm:flex-row sm:items-center">
          <input
            className="h-8 rounded-md border border-input bg-background px-2 text-sm"
            placeholder="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
          <input
            className="h-8 rounded-md border border-input bg-background px-2 text-sm"
            placeholder="密码"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleLogin();
            }}
          />
          <Button size="sm" disabled={loading || !username || !password} onClick={() => void handleLogin()}>
            确认
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>
            取消
          </Button>
        </div>
      ) : null}
      {error ? <p className="text-xs text-destructive">{error}</p> : null}
      <Button
        variant="outline"
        size="sm"
        className="gap-1.5"
        onClick={() => setShowForm((v) => !v)}
      >
        <LogIn className="size-3.5" />
        登录
      </Button>
    </div>
  );
}
