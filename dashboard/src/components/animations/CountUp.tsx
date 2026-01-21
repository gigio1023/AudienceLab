import { useEffect, useMemo, useState } from "react";

type CountUpProps = {
  end: number;
  decimals?: number;
  duration?: number;
  suffix?: string;
};

export function CountUp({ end, decimals = 0, duration = 900, suffix = "" }: CountUpProps) {
  const [value, setValue] = useState(0);
  const endValue = useMemo(() => Math.max(0, end), [end]);

  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      const next = endValue * progress;
      setValue(next);
      if (progress < 1) {
        raf = requestAnimationFrame(tick);
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [endValue, duration]);

  const formatted = value.toFixed(decimals);

  return (
    <span>
      {formatted}
      {suffix}
    </span>
  );
}
