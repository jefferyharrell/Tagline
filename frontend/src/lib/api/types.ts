/**
 * API response interfaces for the Tagline application
 */

// Base API response interface
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ApiError;
}

// API error interface
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

// Pagination metadata
export interface PaginationMeta {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPrevPage: boolean;
}

// Paginated response interface
export interface PaginatedResponse<T> extends ApiResponse {
  data: T[];
  meta: PaginationMeta;
}

// Media item interface
export interface MediaItem {
  id: string;
  filename: string;
  fileType: string;
  fileSize: number;
  width?: number;
  height?: number;
  url: string;
  thumbnailUrl: string;
  createdAt: string;
  updatedAt: string;
  metadata: MediaMetadata;
  tags: string[];
}

// Media metadata interface
export interface MediaMetadata {
  title?: string;
  description?: string;
  dateTaken?: string;
  location?: string;
  photographer?: string;
  event?: string;
  [key: string]: any; // Allow for custom metadata fields
}

// User profile interface
export interface UserProfile {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  roles: string[];
  createdAt: string;
  lastLoginAt?: string;
  isActive: boolean;
}

// Tag interface
export interface Tag {
  id: string;
  name: string;
  count: number;
}

// Search filters interface
export interface SearchFilters {
  query?: string;
  tags?: string[];
  dateFrom?: string;
  dateTo?: string;
  fileTypes?: string[];
  metadata?: Record<string, any>;
  sortBy?: 'createdAt' | 'updatedAt' | 'fileSize' | 'filename';
  sortDirection?: 'asc' | 'desc';
}

// Upload status interface
export interface UploadStatus {
  id: string;
  filename: string;
  progress: number;
  status: 'pending' | 'uploading' | 'processing' | 'complete' | 'error';
  error?: string;
  createdAt: string;
}

// Eligibility check request/response
export interface EligibilityCheckRequest {
  email: string;
}

export interface EligibilityCheckResponse extends ApiResponse {
  data: {
    eligible: boolean;
    message?: string;
  };
}
