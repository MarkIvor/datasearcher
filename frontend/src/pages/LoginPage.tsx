import { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { useI18n } from "../i18n";
import { ArrowUpRight, Check, Languages } from "lucide-react";

interface Props {
  onSwitch: () => void;
}

export function LoginPage({ onSwitch }: Props) {
  const { login } = useAuth();
  const { lang, setLang, t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const features = [t("login.feature1"), t("login.feature2"), t("login.feature3")];
  const [heroLine1, heroLine2] = t("login.heroTitle").split("\n");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("login.failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-grid">
        <div className="auth-hero notch-cut">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div className="auth-hero-logo">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <rect x="2" y="2" width="7" height="7" rx="1.5" fill="currentColor" />
                <rect x="11" y="2" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.6" />
                <rect x="2" y="11" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.6" />
                <rect x="11" y="11" width="7" height="7" rx="1.5" fill="currentColor" opacity="0.3" />
              </svg>
            </div>
            <button className="icon-round" onClick={() => setLang(lang === "ru" ? "en" : "ru")} title={t("common.langTitle")}>
              <Languages size={15} />
            </button>
          </div>
          <div>
            <h1 className="auth-hero-title">{heroLine1}<br />{heroLine2}</h1>
            <p className="auth-hero-sub">{t("login.heroSub")}</p>
            <div className="auth-hero-features">
              {features.map((f) => (
                <span key={f} className="auth-hero-feature">
                  <span className="feature-dot"><Check size={12} strokeWidth={3} /></span>
                  {f}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="auth-form-card">
          <h2 className="auth-form-title">{t("login.title")}</h2>
          <p className="auth-form-sub">{t("login.sub")}</p>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="auth-field">
              <label>{t("login.email")}</label>
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
              <label>{t("login.password")}</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t("login.passwordHint")}
                required
              />
            </div>
            <button className="auth-submit" type="submit" disabled={loading}>
              {loading ? t("login.submitting") : t("login.submit")}
              <ArrowUpRight size={16} />
            </button>
          </form>

          <button className="auth-switch" onClick={onSwitch}>
            {t("login.noAccount")}
          </button>
        </div>
      </div>
    </div>
  );
}
