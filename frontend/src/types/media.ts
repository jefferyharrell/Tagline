export interface MediaObject {
  object_key: string;  // Primary key
  ingestion_status: 'pending' | 'processing' | 'completed' | 'failed';
  file_size?: number;
  file_mimetype?: string;
  file_last_modified?: string;
  created_at?: string;
  updated_at?: string;
  metadata?: {
    description?: string;
    keywords?: string[];
    intrinsic?: {
      width: number;
      height: number;
      mode?: string;
      format?: string;
    };
    [key: string]: string | string[] | object | undefined;
  };
  has_thumbnail: boolean;
  has_proxy: boolean;
}
