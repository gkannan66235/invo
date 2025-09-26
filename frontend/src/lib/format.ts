// Currency & number formatting helpers for Indian locale (FR-003, FR-004, FR-021).
// Utility module consumed by dashboard, invoice form, printable invoice.
// Uses en-IN locale for lakh/crore grouping. Ensures two decimal places where monetary.

export function formatINR(amount: number | string | null | undefined, opts: { minimumFractionDigits?: number; maximumFractionDigits?: number } = {}) {
  if (amount === null || amount === undefined || amount === '') return '₹0.00';
  let num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) num = 0;
  const { minimumFractionDigits = 2, maximumFractionDigits = 2 } = opts;
  return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits, maximumFractionDigits });
}

export function formatNumberIN(amount: number | string | null | undefined) {
  if (amount === null || amount === undefined || amount === '') return '0';
  let num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) num = 0;
  return num.toLocaleString('en-IN');
}
