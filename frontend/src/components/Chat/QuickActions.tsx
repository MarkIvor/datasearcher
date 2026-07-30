interface Props {
  actions: string[];
  onAction: (action: string) => void;
}

export function QuickActions({ actions, onAction }: Props) {
  if (!actions.length) return null;

  return (
    <div className="quick-actions">
      {actions.map((action, i) => (
        <button
          key={i}
          className="quick-action-btn"
          onClick={() => onAction(action)}
          style={{ animationDelay: `${i * 40}ms` }}
        >
          {action}
        </button>
      ))}
    </div>
  );
}
