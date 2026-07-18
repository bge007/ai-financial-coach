/** Format a number with Indian digit grouping and a ₹ prefix. */
export function formatINR(value) {
  if (value === null || value === undefined || value === "") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return "—";
  const formatted = new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(num);
  return `₹${formatted}`;
}
