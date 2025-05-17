/**
 * API client for the Tagline application
 * Handles all requests to the backend API with proper error handling and authentication
 */

import { ApiError, ApiResponse } from './types';

// Default API configuration
const API_CONFIG = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
};

// API request options interface
export interface ApiRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  params?: Record<string, string | number | boolean | undefined>;
  data?: any;
  timeout?: number;
  withAuth?: boolean;
}

// API client class
export class ApiClient {
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;
  private timeout: number;

  constructor(config = API_CONFIG) {
    this.baseUrl = config.baseUrl;
    this.defaultHeaders = config.headers;
    this.timeout = config.timeout;
  }

  /**
   * Get the authentication token from local storage or cookies
   */
  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('auth_token');
  }

  /**
   * Build the full URL with query parameters
   */
  private buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined>): string {
    const url = new URL(`${this.baseUrl}${endpoint}`);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          url.searchParams.append(key, String(value));
        }
      });
    }
    
    return url.toString();
  }

  /**
   * Handle API errors and format them consistently
   */
  private handleError(error: any): ApiError {
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      const { status, data } = error.response;
      
      return {
        code: `API_ERROR_${status}`,
        message: data?.message || `Request failed with status code ${status}`,
        details: data?.details || data,
      };
    } else if (error.request) {
      // The request was made but no response was received
      return {
        code: 'NETWORK_ERROR',
        message: 'Network error, no response received from server',
      };
    } else if (error.name === 'AbortError') {
      // The request was aborted (timeout)
      return {
        code: 'TIMEOUT_ERROR',
        message: 'Request timed out',
      };
    } else {
      // Something happened in setting up the request that triggered an Error
      return {
        code: 'REQUEST_ERROR',
        message: error.message || 'An unexpected error occurred',
      };
    }
  }

  /**
   * Make an API request with proper error handling
   */
  public async request<T = any>(
    endpoint: string,
    options: ApiRequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const {
      method = 'GET',
      headers = {},
      params,
      data,
      timeout = this.timeout,
      withAuth = true,
    } = options;

    // Build request URL with query parameters
    const url = this.buildUrl(endpoint, params);

    // Prepare headers
    const requestHeaders: Record<string, string> = {
      ...this.defaultHeaders,
      ...headers,
    };

    // Add authentication token if required
    if (withAuth) {
      const token = this.getAuthToken();
      if (token) {
        requestHeaders['Authorization'] = `Bearer ${token}`;
      }
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        method,
        headers: requestHeaders,
        body: data ? JSON.stringify(data) : undefined,
        signal: controller.signal,
      });

      // Clear timeout
      clearTimeout(timeoutId);

      // Parse response
      const responseData = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: {
            code: `API_ERROR_${response.status}`,
            message: responseData?.message || `Request failed with status code ${response.status}`,
            details: responseData?.details || responseData,
          },
        };
      }

      return {
        success: true,
        data: responseData,
      };
    } catch (error: any) {
      // Clear timeout
      clearTimeout(timeoutId);

      return {
        success: false,
        error: this.handleError(error),
      };
    }
  }

  /**
   * Convenience methods for common HTTP methods
   */
  public async get<T = any>(
    endpoint: string,
    params?: Record<string, string | number | boolean | undefined>,
    options: Omit<ApiRequestOptions, 'method' | 'params'> = {}
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'GET',
      params,
    });
  }

  public async post<T = any>(
    endpoint: string,
    data?: any,
    options: Omit<ApiRequestOptions, 'method' | 'data'> = {}
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      data,
    });
  }

  public async put<T = any>(
    endpoint: string,
    data?: any,
    options: Omit<ApiRequestOptions, 'method' | 'data'> = {}
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      data,
    });
  }

  public async patch<T = any>(
    endpoint: string,
    data?: any,
    options: Omit<ApiRequestOptions, 'method' | 'data'> = {}
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      data,
    });
  }

  public async delete<T = any>(
    endpoint: string,
    options: Omit<ApiRequestOptions, 'method'> = {}
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'DELETE',
    });
  }
}

// Create and export a singleton instance of the API client
export const apiClient = new ApiClient();

// Export default for convenience
export default apiClient;
