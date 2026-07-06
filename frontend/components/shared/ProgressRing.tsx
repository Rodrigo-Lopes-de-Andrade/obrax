interface ProgressRingProps {
  pct: number;
  label: string;
  size?: number;
  radius?: number;
  strokeWidth?: number;
  colorClassName?: string;
}

export function ProgressRing({
  pct,
  label,
  size = 132,
  radius = 52,
  strokeWidth = 11,
  colorClassName = "text-primary",
}: ProgressRingProps) {
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
      <circle cx={center} cy={center} r={radius} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth={strokeWidth} />
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={`${(circumference * pct) / 100} ${circumference}`}
        transform={`rotate(-90 ${center} ${center})`}
        className={colorClassName}
        stroke="currentColor"
      />
      <text x={center} y={center - 2} textAnchor="middle" className="fill-foreground font-mono text-[30px] font-extrabold">
        {pct}%
      </text>
      <text x={center} y={center + 18} textAnchor="middle" className="fill-muted-foreground text-[12px]">
        {label}
      </text>
    </svg>
  );
}
