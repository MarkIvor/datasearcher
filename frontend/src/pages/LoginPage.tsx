import { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { ArrowUpRight, Check } from "lucide-react";

interface Props {
  onSwitch: () => void;
}

const FEATURES = [
  "46 аналитических инструментов",
  "SQL по вопросу на русском",
  "Графики, дашборды, ML-прогнозы",
];

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
    <div className="auth-shell">
      <div className="auth-grid">
        <div className="auth-hero notch-cut">
          <div className="auth-hero-logo">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <rect x="2" y="2" width="7" height="7" rx="1.5" fill="currentColor" />
              <rect x="11" y="2" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.6" />
              <rect x="2" y="11" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.6" />
              <rect x="11" y="11" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.3" />
            </svg>
          </div>
          <div>
            <h1 className="auth-hero-title">Анализ данных<br />через диалог</h1>
            <p className="auth-hero-sub">
              Загрузите таблицу или подключитесь к БД. DataSearcher сам напишет SQL,
              построит графики и найдёт инсайты.
            </p>
            <div className="auth-hero-features">
              {FEATURES.map((f) => (
                <span key={f} className="auth-hero-feature">
                  <span className="feature-dot"><Check size={12} strokeWidth={3} /></span>
                  {f}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="auth-form-card">
          <h2 className="auth-form-title">Вход</h2>
          <p className="auth-form-sub">Введите email и пароль вашего аккаунта</p>

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
              <ArrowUpRight size={16} />
            </button>
          </form>

          <button className="auth-switch" onClick={onSwitch}>
            Нет аккаунта? Зарегистрироваться
          </button>
        </div>
      </div>
    </div>
  );
}
