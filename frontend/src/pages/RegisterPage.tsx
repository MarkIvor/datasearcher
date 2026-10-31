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
            <h1 className="auth-hero-title">Присоединяйтесь<br />к DataSearcher</h1>
            <p className="auth-hero-sub">
              Создайте аккаунт — и задайте первый вопрос своим данным уже через минуту.
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
          <h2 className="auth-form-title">Регистрация</h2>
          <p className="auth-form-sub">Создайте аккаунт для работы с DataSearcher</p>

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
              <ArrowUpRight size={16} />
            </button>
          </form>

          <button className="auth-switch" onClick={onSwitch}>
            Уже есть аккаунт? Войти
          </button>
        </div>
      </div>
    </div>
  );
}
