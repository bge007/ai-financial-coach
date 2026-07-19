/** Format a number with Indian digit grouping and a ₹ prefix.
 *  Pass { fixed: true } to always show two decimals (₹1,00,000.00).
 */
export function formatINR(value, { fixed = false } = {}) {
  if (value === null || value === undefined || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  const formatted = new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: fixed ? 2 : 0,
  }).format(num);
  return `₹${formatted}`;
}

/** Turn YYYY-MM into a readable label, e.g. "April 2025" or "Apr 2025". */
export function formatMonthLabel(monthKey, { style = "long" } = {}) {
  if (!monthKey || monthKey === "all") return "All months";
  const match = /^(\d{4})-(\d{2})$/.exec(String(monthKey).trim());
  if (!match) return monthKey;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, 1);
  return new Intl.DateTimeFormat("en-IN", {
    month: style === "short" ? "short" : "long",
    year: "numeric",
  }).format(date);
}
