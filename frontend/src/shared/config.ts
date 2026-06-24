/**
 * API base URL.
 * Empty string = relative URLs → Vite dev proxy handles /api → :8000.
 * In production, set VITE_API_BASE_URL env var.
 */
export const API_BASE_URL = import.meta.env['VITE_API_BASE_URL'] ?? ''
