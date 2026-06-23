type BrandLogoProps = {
  compact?: boolean;
};

export default function BrandLogo({ compact = false }: BrandLogoProps) {
  return (
    <span className={compact ? "brand-logo compact" : "brand-logo"} aria-label="SmartVote">
      <span className="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 48 48" role="img">
          <path className="brand-shield" d="M24 4 40 10v12c0 10.8-6.5 17.8-16 22C14.5 39.8 8 32.8 8 22V10L24 4Z" />
          <path className="brand-check" d="m16.5 24.2 5 5.1 10.8-12.4" />
          <path className="brand-orbit" d="M10 30c9 6.3 19.6 6.4 29.2-.6" />
        </svg>
      </span>
      {!compact && (
        <span className="brand-word">
          <strong>SmartVote</strong>
          <small>AI Election OS</small>
        </span>
      )}
    </span>
  );
}
