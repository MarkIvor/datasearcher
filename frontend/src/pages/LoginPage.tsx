import { useState } from "react";
import { useAuth } from "../hooks/useAuth";

interface Props {
  onSwitch: () => void;
}

export function LoginPage({ onSwitch }: Props) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <svg width="28" height="28" viewBox="0 0 20 20" fill="none">
            <rect x="2" y="2" width="7" height="7" rx="1.5" fill="white" />
            <rect x="11" y="2" width="7" height="7" rx="1.5" fill="white" opacity="0.6" />
            <rect x="2" y="11" width="7" height="7" rx="1.5" fill="white" opacity="0.6" />
            <rect x="11" y="11" width="7" height="7" rx="1.5" fill="white" opacity="0.3" />
          </svg>
        </div>
        <h1>Вход в DataSearcher</h1>
        <p>Введите email и пароль для входа</p>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="auth-field">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
              required
              autoFocus
            />
          </div>
          <div className="auth-field">
            <label>Пароль</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Минимум 6 символов"
              required
            />
          </div>
          <button className="auth-submit" type="submit" disabled={loading}>
            {loading ? "Вход..." : "Войти"}
          </button>
        </form>

        <button className="auth-switch" onClick={onSwitch}>
          Нет аккаунта? Зарегистрироваться
        </button>
      </div>
    </div>
  );
}
