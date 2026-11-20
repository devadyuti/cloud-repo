/**
 * Formatter utility functions for the Client Portfolio Risk Dashboard.
 */

/**
 * Format a number as GBP currency with thousand separators.
 * @param {number} value - The numeric value to format (e.g., 2450000)
 * @returns {string} Formatted currency string (e.g., "£2,450,000")
 */
export function formatCurrency(value) {
  if (value == null || isNaN(value)) {
    return '£0';
  }
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format a number as a percentage with appropriate decimal places.
 * @param {number} value - The numeric value to format (e.g., 11.2)
 * @param {number} [decimals=1] - Number of decimal places
 * @returns {string} Formatted percentage string (e.g., "11.2%")
 */
export function formatPercentage(value, decimals = 1) {
  if (value == null || isNaN(value)) {
    return '0%';
  }
  return `${Number(value).toFixed(decimals)}%`;
}

/**
 * Format an ISO date string to a readable format.
 * @param {string} dateString - ISO date string (e.g., "2026-03-15")
 * @returns {string} Formatted date string (e.g., "15 Mar 2026")
 */
export function formatDate(dateString) {
  if (!dateString) {
    return '';
  }
  const date = new Date(dateString);
  if (isNaN(date.getTime())) {
    return '';
  }
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date);
}
