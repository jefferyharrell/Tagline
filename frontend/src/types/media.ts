export interface MediaObject {
  id: string;
  object_key: string;
  metadata: {
    description?: string;
    keywords?: string[];
    file_size?: string;
    dimensions?: string;
    created?: string;
    intrinsic?: {
      width: number;
      height: number;
    };
    [key: string]: string | string[] | object | undefined;
  };
  created_at?: string;
  updated_at?: string;
}
