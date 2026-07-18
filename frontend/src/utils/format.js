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
