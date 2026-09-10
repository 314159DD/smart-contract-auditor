"use client";

function arcPath(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const x1 = cx + r * Math.cos(toRad(startAngle));
  const y1 = cy + r * Math.sin(toRad(startAngle));
  const x2 = cx + r * Math.cos(toRad(endAngle));
  const y2 = cy + r * Math.sin(toRad(endAngle));
  const large = endAngle - startAngle > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

export function RiskGauge({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(100, score));
  // Arc: 180° from left (-180°) to right (0°), bottom half
  const START = 180;
  const END = 360;
  const angle = START + (clamped / 100) * 180;

  const color =
    clamped >= 80
      ? "#ef4444"
      : clamped >= 50
      ? "#f97316"
      : clamped >= 20
      ? "#eab308"
      : "#22c55e";

  const CX = 80;
  const CY = 80;
  const R = 60;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={160} height={100} viewBox="0 0 160 100">
        {/* Background arc */}
        <path
          d={arcPath(CX, CY, R, 180, 360)}
          fill="none"
          stroke="#1f2937"
          strokeWidth={14}
          strokeLinecap="round"
        />
        {/* Score arc */}
        <path
          d={arcPath(CX, CY, R, 180, angle)}
          fill="none"
          stroke={color}
          strokeWidth={14}
          strokeLinecap="round"
        />
        {/* Needle */}
        {(() => {
          const rad = ((angle) * Math.PI) / 180;
          const nx = CX + R * Math.cos(rad);
          const ny = CY + R * Math.sin(rad);
          return (
            <circle cx={nx} cy={ny} r={6} fill={color} />
          );
        })()}
        {/* Score label */}
        <text
          x={CX}
          y={CY - 8}
          textAnchor="middle"
          className="font-mono"
          fill={color}
          fontSize={22}
          fontWeight="bold"
          fontFamily="monospace"
        >
          {Math.round(clamped)}
        </text>
        <text
          x={CX}
          y={CY + 10}
          textAnchor="middle"
          fill="#9ca3af"
          fontSize={10}
          fontFamily="sans-serif"
        >
          RISK SCORE
        </text>
        <text x={12} y={CY + 18} fill="#6b7280" fontSize={9} fontFamily="monospace">
          0
        </text>
        <text x={140} y={CY + 18} fill="#6b7280" fontSize={9} fontFamily="monospace">
          100
        </text>
      </svg>
    </div>
  );
}
