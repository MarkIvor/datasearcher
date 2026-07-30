import { useEffect, useCallback, useRef } from "react";

export function useNotification() {
  const granted = useRef(false);

  useEffect(() => {
    if ("Notification" in window && Notification.permission === "granted") {
      granted.current = true;
    }
  }, []);

  const requestPermission = useCallback(async () => {
    if ("Notification" in window && Notification.permission === "default") {
      const p = await Notification.requestPermission();
      granted.current = p === "granted";
    }
  }, []);

  const notify = useCallback((title: string, body?: string) => {
    if (!granted.current) return;
    if (document.visibilityState === "visible") return;
    new Notification(title, { body, icon: "/favicon.ico" });
  }, []);

  const playSound = useCallback(() => {
    try {
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      osc.type = "sine";
      gain.gain.value = 0.08;
      osc.start();
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
      osc.stop(ctx.currentTime + 0.15);
    } catch {
      // ignore
    }
  }, []);

  return { requestPermission, notify, playSound };
}
