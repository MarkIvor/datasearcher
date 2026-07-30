import type { StepInfo } from "../../types";
import { CheckCircle, Loader2 } from "lucide-react";

interface Props {
  steps: StepInfo[];
}

export function StepIndicator({ steps }: Props) {
  if (!steps.length) return null;

  return (
    <div className="step-indicator">
      {steps.map((step, i) => (
        <div key={i} className={`step-pill step-${step.status}`}>
          {step.status === "completed" ? (
            <CheckCircle size={11} />
          ) : (
            <Loader2 size={11} className="spin" />
          )}
          <span>{step.text}</span>
          {i < steps.length - 1 && <span className="step-arrow">→</span>}
        </div>
      ))}
    </div>
  );
}
