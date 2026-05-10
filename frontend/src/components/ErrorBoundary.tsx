import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div style={{ padding: "10px 14px", background: "var(--error-light)", borderRadius: 8, fontSize: 12, color: "#991b1b" }}>
          Ошибка рендеринга
        </div>
      );
    }
    return this.props.children;
  }
}
