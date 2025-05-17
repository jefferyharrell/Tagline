/**
 * API hooks for the Tagline application
 * Uses SWR for data fetching with caching and revalidation
 */

import useSWR, { SWRConfiguration, SWRResponse } from 'swr';
import { apiClient } from './client';
import { 
  ApiResponse, 
  MediaItem, 
  PaginatedResponse, 
  SearchFilters, 
  Tag, 
  UserProfile 
} from './types';

// Default SWR configuration
const defaultConfig: SWRConfiguration = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  dedupingInterval: 5000, // 5 seconds
};

/**
 * Custom hook for API data fetching with SWR
 */
export function useApi<T = any>(
  endpoint: string | null,
  params?: Record<string, string | number | boolean | undefined>,
  config?: SWRConfiguration
): SWRResponse<ApiResponse<T>, Error> {
  return useSWR(
    endpoint ? [endpoint, params] : null,
    async ([url, queryParams]) => {
      return apiClient.get<T>(url, queryParams);
    },
    { ...defaultConfig, ...config }
  );
}

/**
 * Hook for fetching media items with pagination and search filters
 */
export function useMediaItems(
  page: number = 1,
  pageSize: number = 20,
  filters?: SearchFilters,
  config?: SWRConfiguration
) {
  // Convert filters to a format compatible with the API client
  const params: Record<string, string | number | boolean | undefined> = {
    page,
    pageSize,
  };
  
  // Add filters if they exist
  if (filters) {
    // Handle special cases for array values
    if (filters.tags) {
      params['tags'] = filters.tags.join(',');
    }
    if (filters.fileTypes) {
      params['fileTypes'] = filters.fileTypes.join(',');
    }
    
    // Add other simple filters
    if (filters.query) params['query'] = filters.query;
    if (filters.dateFrom) params['dateFrom'] = filters.dateFrom;
    if (filters.dateTo) params['dateTo'] = filters.dateTo;
    if (filters.sortBy) params['sortBy'] = filters.sortBy;
    if (filters.sortDirection) params['sortDirection'] = filters.sortDirection;
    
    // Handle metadata object by flattening it
    if (filters.metadata) {
      Object.entries(filters.metadata).forEach(([key, value]) => {
        params[`metadata.${key}`] = value as string | number | boolean;
      });
    }
  }

  return useApi<PaginatedResponse<MediaItem>>('/media', params, config);
}

/**
 * Hook for fetching a single media item by ID
 */
export function useMediaItem(
  id: string | null,
  config?: SWRConfiguration
) {
  return useApi<MediaItem>(id ? `/media/${id}` : null, undefined, config);
}

/**
 * Hook for fetching tags
 */
export function useTags(
  config?: SWRConfiguration
) {
  return useApi<Tag[]>('/tags', undefined, config);
}

/**
 * Hook for fetching the current user's profile
 */
export function useUserProfile(
  config?: SWRConfiguration
) {
  return useApi<UserProfile>('/auth/profile', undefined, config);
}

/**
 * Hook for fetching all users (admin only)
 */
export function useUsers(
  page: number = 1,
  pageSize: number = 20,
  config?: SWRConfiguration
) {
  const params = {
    page,
    pageSize,
  };

  return useApi<PaginatedResponse<UserProfile>>('/admin/users', params, config);
}

/**
 * Hook for searching media items
 */
export function useMediaSearch(
  query: string,
  page: number = 1,
  pageSize: number = 20,
  filters?: Omit<SearchFilters, 'query'>,
  config?: SWRConfiguration
) {
  // Don't fetch if query is empty
  if (!query.trim()) {
    return {
      data: undefined,
      error: undefined,
      isLoading: false,
      isValidating: false,
      mutate: () => Promise.resolve(undefined),
    };
  }

  // Convert parameters to a format compatible with the API client
  const params: Record<string, string | number | boolean | undefined> = {
    query,
    page,
    pageSize,
  };
  
  // Add filters if they exist
  if (filters) {
    // Handle special cases for array values
    if (filters.tags) {
      params['tags'] = filters.tags.join(',');
    }
    if (filters.fileTypes) {
      params['fileTypes'] = filters.fileTypes.join(',');
    }
    
    // Add other simple filters
    if (filters.dateFrom) params['dateFrom'] = filters.dateFrom;
    if (filters.dateTo) params['dateTo'] = filters.dateTo;
    if (filters.sortBy) params['sortBy'] = filters.sortBy;
    if (filters.sortDirection) params['sortDirection'] = filters.sortDirection;
    
    // Handle metadata object by flattening it
    if (filters.metadata) {
      Object.entries(filters.metadata).forEach(([key, value]) => {
        params[`metadata.${key}`] = value as string | number | boolean;
      });
    }
  }

  return useApi<PaginatedResponse<MediaItem>>('/media/search', params, config);
}

/**
 * Hook for fetching recent uploads
 */
export function useRecentUploads(
  limit: number = 5,
  config?: SWRConfiguration
) {
  const params = {
    limit,
  };

  return useApi<MediaItem[]>('/media/recent', params, config);
}

/**
 * Hook for fetching user's favorite media items
 */
export function useFavorites(
  page: number = 1,
  pageSize: number = 20,
  config?: SWRConfiguration
) {
  const params = {
    page,
    pageSize,
  };

  return useApi<PaginatedResponse<MediaItem>>('/media/favorites', params, config);
}
