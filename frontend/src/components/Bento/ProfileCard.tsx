import { Bell, Plus } from "lucide-react";
import { useI18n } from "../../i18n";
import type { SetupState } from "../../api/client";
import { LangSwitch } from "./LangSwitch";

interface Props {
  userName: string;
  role?: string;
  setup: SetupState | null;
  onBell?: () => void;
  onPlus?: () => void;
}

export function ProfileCard({ userName, role, setup, onBell, onPlus }: Props) {
  const { t } = useI18n();
  const initial = (userName || "U").trim().charAt(0).toUpperCase();
  const completed = setup?.completed ?? false;
  const step = setup?.step ?? 1;
  const total = setup?.steps_total ?? 4;
  const pct = completed ? 100 : Math.min(100, Math.round((step / total) * 100));
  const captionLeft = completed ? t("profile.setupDone") : t("profile.step", { n: step, total });
  const roleLabel =
    role === "admin" ? t("profile.roleAdmin") :
    role === "viewer" ? t("profile.roleViewer") :
    role ? t("profile.roleAnalyst") : "";

  return (
    <section className="profile-card notch-cut">
      <div className="notch-actions">
        <button className="icon-round" onClick={onPlus} title={t("profile.newSession")}>
          <Plus size={16} />
        </button>
        <button className="icon-round" onClick={onBell} title={t("profile.notifications")}>
          <Bell size={16} />
        </button>
        <LangSwitch />
      </div>

      <div className="profile-top">
        <div className="profile-avatar">{initial}</div>
        <div className="profile-brand">
          <span className="profile-agent">DataSearcher</span>
          <span className="profile-name" title={userName}>{userName || t("profile.user")}</span>
        </div>
      </div>

      <div className="profile-progress">
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <div className="progress-caption">
          <span>{captionLeft}</span>
          <span>{pct}%</span>
        </div>
      </div>
      {roleLabel && (
        <div className="profile-caption" style={{ marginTop: 6, fontSize: 10, fontWeight: 600, opacity: 0.6 }}>
          {roleLabel}
        </div>
      )}
    </section>
  );
}
