export class ApiError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly detail?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function getFriendlyMessage(error: Error, statusCode?: number): string {
  if (typeof navigator !== 'undefined' && !navigator.onLine) return 'No internet connection.';

  if (error instanceof ApiError && error.detail) {
    // Pass backend detail through for 400 and 422 — all backend messages are sanitized
    // and written to be user-readable (graph errors, contract violations, warm-up notices)
    if (error.statusCode === 400 || error.statusCode === 422) return error.detail;
  }

  switch (statusCode) {
    case 400: return 'Invalid request. Check your inputs.';
    case 401: return 'Unauthorized. Please check your credentials.';
    case 403: return 'Access denied.';
    case 404: return 'Resource not found.';
    case 422: return 'Validation failed. Check required fields.';
    case 500: return 'Server error. Please try again.';
    case 503: return 'Service unavailable. Is the backend running?';
  }

  if (error.message.includes('Failed to fetch') || error.message.includes('fetch')) {
    return 'Cannot reach server. Is the backend running?';
  }

  return error.message || 'An unexpected error occurred.';
}
