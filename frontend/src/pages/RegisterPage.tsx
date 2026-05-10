import { useState } from "react";
import { useAuth } from "../hooks/useAuth";

interface Props {
  onSwitch: () => void;
}

export function RegisterPage({ onSwitch }: Props) {
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 6) {
      setError("Пароль минимум 6 символов");
      return;
    }
    setLoading(true);
    try {
      await register(email, password, displayName);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка регистрации");
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
        <h1>Регистрация</h1>
        <p>Создайте аккаунт для работы с DataSearcher</p>

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
            <label>Имя</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Как вас называть?"
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
            {loading ? "Регистрация..." : "Зарегистрироваться"}
          </button>
        </form>

        <button className="auth-switch" onClick={onSwitch}>
          Уже есть аккаунт? Войти
        </button>
      </div>
    </div>
  );
}
