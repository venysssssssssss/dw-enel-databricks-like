type Props = {
  size?: number;
  variant?: "mark" | "wordmark";
  tone?: "brand" | "mono";
  className?: string;
};

const RED = "#C8102E";

export function EnelLogo({ size = 28, variant = "mark", tone = "brand", className }: Props) {
  const fill = tone === "mono" ? "currentColor" : RED;

  if (variant === "mark") {
    return (
      <svg
        viewBox="0 0 64 64"
        width={size}
        height={size}
        role="img"
        aria-label="ENEL"
        className={className}
      >
        <defs>
          <linearGradient id="enel-mark-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={tone === "mono" ? "currentColor" : "#E0263E"} />
            <stop offset="100%" stopColor={tone === "mono" ? "currentColor" : "#7A0A1F"} />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="64" height="64" rx="14" fill="url(#enel-mark-grad)" />
        <path
          d="M14 42 L14 22 L34 22 L34 28 L20 28 L20 30 L32 30 L32 36 L20 36 L20 42 Z"
          fill="#fff"
        />
        <path
          d="M40 22 L46 22 L46 36 L52 36 L52 42 L40 42 Z"
          fill="#fff"
          opacity="0.92"
        />
        <circle cx="55" cy="14" r="3.5" fill="#fff" />
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 200 56"
      width={size * 3.2}
      height={size}
      role="img"
      aria-label="ENEL Brasil"
      className={className}
    >
      <g fill={fill}>
        <path d="M8 38 V14 H44 V20 H16 V22 H40 V28 H16 V32 H44 V38 Z" />
        <path d="M52 38 V14 H58 L74 30 V14 H80 V38 H74 L58 22 V38 Z" />
        <path d="M88 38 V14 H124 V20 H96 V22 H120 V28 H96 V32 H124 V38 Z" />
        <path d="M132 38 V14 H140 V32 H164 V38 Z" />
      </g>
      <circle cx="172" cy="16" r="4" fill={fill} />
    </svg>
  );
}
