/**
 * Error handling utilities for the Tagline application
 * Provides consistent error handling and logging
 */

import { ApiError } from '../api/types';

// Error severity levels
export enum ErrorSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

// Error context interface
export interface ErrorContext {
  component?: string;
  action?: string;
  userId?: string;
  additionalData?: Record<string, any>;
}

/**
 * Format an error message for display to the user
 */
export function formatErrorMessage(error: ApiError | Error | string): string {
  if (typeof error === 'string') {
    return error;
  }
  
  if ('code' in error && error.code && error.message) {
    // API error with code
    return error.message;
  }
  
  // Standard Error object
  return error.message || 'An unexpected error occurred';
}

/**
 * Log an error with additional context
 */
export function logError(
  error: ApiError | Error | string,
  context: ErrorContext = {},
  severity: ErrorSeverity = ErrorSeverity.ERROR
): void {
  // In production, this would send errors to a logging service
  // For now, we'll just log to console with severity and context
  
  const errorMessage = formatErrorMessage(error);
  const errorObject = typeof error === 'string' ? { message: error } : error;
  
  const logData = {
    timestamp: new Date().toISOString(),
    severity,
    message: errorMessage,
    error: errorObject,
    ...context,
  };
  
  // Log based on severity
  switch (severity) {
    case ErrorSeverity.INFO:
      console.info('[Tagline]', logData);
      break;
    case ErrorSeverity.WARNING:
      console.warn('[Tagline]', logData);
      break;
    case ErrorSeverity.CRITICAL:
      console.error('[Tagline][CRITICAL]', logData);
      break;
    case ErrorSeverity.ERROR:
    default:
      console.error('[Tagline]', logData);
      break;
  }
  
  // In production, you would send this to a service like Sentry, LogRocket, etc.
}

/**
 * Handle API errors consistently
 */
export function handleApiError(
  error: ApiError,
  context: ErrorContext = {}
): string {
  // Log the error
  logError(error, context);
  
  // Return user-friendly message based on error code
  switch (error.code) {
    case 'NETWORK_ERROR':
      return 'Unable to connect to the server. Please check your internet connection and try again.';
    
    case 'TIMEOUT_ERROR':
      return 'The request timed out. Please try again later.';
    
    case 'API_ERROR_401':
      return 'You are not authorized to perform this action. Please log in and try again.';
    
    case 'API_ERROR_403':
      return 'You do not have permission to access this resource.';
    
    case 'API_ERROR_404':
      return 'The requested resource was not found.';
    
    case 'API_ERROR_429':
      return 'Too many requests. Please try again later.';
    
    case 'API_ERROR_500':
    case 'API_ERROR_502':
    case 'API_ERROR_503':
    case 'API_ERROR_504':
      return 'A server error occurred. Please try again later.';
    
    default:
      // Use the error message from the API if available
      return error.message || 'An unexpected error occurred. Please try again.';
  }
}

/**
 * Create a context object for error logging
 */
export function createErrorContext(
  component: string,
  action: string,
  additionalData?: Record<string, any>
): ErrorContext {
  return {
    component,
    action,
    additionalData,
    // In a real app, you might include the user ID here
    // userId: getCurrentUserId(),
  };
}
