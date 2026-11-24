/**
 * Mask a patient phone number for display while keeping leading country/area
 * digits and the trailing 4 digits readable.
 */
export function maskPhoneNumber(phone: string): string {
  const trimmed = phone.trim();
  if (trimmed.length <= 6) {
    return trimmed.replace(/.(?=.{2})/g, "•");
  }

  const prefixMatch = trimmed.match(/^(\+\d{1,3}|0\d{2,3})/);
  const prefix = prefixMatch ? prefixMatch[0] : trimmed.slice(0, 2);
  const suffix = trimmed.slice(-4);
  const hiddenCount = Math.max(3, trimmed.length - prefix.length - suffix.length);

  return `${prefix} ${"•".repeat(Math.min(hiddenCount, 6))} ${suffix}`;
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export function formatDateLabel(isoDate: string): string {
  const parsed = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return isoDate;
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(parsed);
}
