"use client";

import { useEffect, useRef, useCallback } from 'react';
import type { MediaObject } from '@/types/media';

export interface IngestEvent {
  // New structure with full MediaObject
  event_type: 'queued' | 'started' | 'complete';
  timestamp: string;
  media_object: MediaObject;
  error?: string;
  
  // Backward compatibility fields (will be populated from media_object)
  object_key: string;
  has_thumbnail: boolean;
  ingestion_status: 'pending' | 'processing' | 'completed' | 'failed';
  type?: 'media_ingested';  // For backward compatibility
}

interface UseIngestEventsOptions {
  onMediaIngested: (event: IngestEvent) => void;
  currentPath: string[];
  enabled?: boolean;
}

export function useIngestEvents({ 
  onMediaIngested, 
  currentPath, 
  enabled = true 
}: UseIngestEventsOptions) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 1000; // 1 second
  const lastEventTimeRef = useRef<string | null>(null);

  const handleEvent = useCallback((event: IngestEvent) => {
    // Filter out queued and started events for now - we only want complete events
    if (event.event_type === 'queued' || event.event_type === 'started') {
      console.log(`🚫 Filtering out ${event.event_type} event for ${event.object_key}`);
      return;
    }
    
    // Filter events to only process those relevant to current path
    // Decode URL-encoded path components to match backend object_key format
    const decodedPath = currentPath.map(segment => decodeURIComponent(segment));
    const pathPrefix = decodedPath.length > 0 ? decodedPath.join('/') + '/' : '';
    
    console.log('🔍 SSE Event received:', event);
    console.log('📂 Current path (raw):', currentPath);
    console.log('📂 Current path (decoded):', decodedPath);
    console.log('🎯 Path prefix:', pathPrefix);
    
    // Include event if:
    // 1. We're at root (currentPath is empty) and object_key doesn't contain '/'
    // 2. Object key starts with current path prefix (file is in this folder or subfolder)
    // 3. Object key exactly matches current path (for files in current directory)
    const isRelevant = decodedPath.length === 0 || 
                      event.object_key.startsWith(pathPrefix) ||
                      event.object_key === decodedPath.join('/');
    
    console.log('✅ Event is relevant:', isRelevant);
    
    if (isRelevant) {
      console.log('🚀 Forwarding event to LibraryView');
      
      // Track the timestamp of this event for reconnection
      if (event.timestamp) {
        lastEventTimeRef.current = event.timestamp;
      }
      
      onMediaIngested(event);
    } else {
      console.log('❌ Event filtered out - not relevant to current path');
    }
  }, [currentPath, onMediaIngested]);

  const connect = useCallback(() => {
    if (!enabled) return;

    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      // Build URL with optional since parameter
      let url = '/api/events/ingest';
      if (lastEventTimeRef.current) {
        url += `?since=${encodeURIComponent(lastEventTimeRef.current)}`;
        console.log('🔄 Reconnecting with since parameter:', lastEventTimeRef.current);
      } else {
        console.log('🆕 First connection, no since parameter');
      }
      
      const eventSource = new EventSource(url, {
        withCredentials: true
      });

      eventSource.onopen = () => {
        console.log('SSE connection established');
        reconnectAttempts.current = 0; // Reset on successful connection
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle different event types
          if (data.type === 'media_ingested' || data.event_type) {
            // New format with full MediaObject or backward compatible format
            const ingestEvent: IngestEvent = {
              event_type: data.event_type || 'complete', // Default to complete for backward compatibility
              timestamp: data.timestamp || new Date().toISOString(),
              media_object: data.media_object || {
                // Fallback to backward compatible fields if media_object not present
                object_key: data.object_key,
                has_thumbnail: data.has_thumbnail,
                ingestion_status: data.ingestion_status,
                // Add other required MediaObject fields with defaults
                file_size: null,
                file_mimetype: null,
                file_last_modified: null,
                created_at: null,
                updated_at: null,
                metadata: {}
              },
              error: data.error,
              
              // Backward compatibility fields
              object_key: data.object_key || data.media_object?.object_key || '',
              has_thumbnail: data.has_thumbnail ?? data.media_object?.has_thumbnail ?? false,
              ingestion_status: data.ingestion_status || data.media_object?.ingestion_status || 'pending',
              type: data.type
            };
            
            handleEvent(ingestEvent);
          } else if (data.type === 'heartbeat' || data.type === 'connected') {
            // Handle connection status events
            console.log('SSE status:', data.type);
          } else if (data.type === 'error') {
            console.error('SSE error:', data.message);
          }
        } catch (error) {
          console.error('Failed to parse SSE event:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        eventSource.close();
        
        // Attempt to reconnect with exponential backoff
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = baseReconnectDelay * Math.pow(2, reconnectAttempts.current);
          reconnectAttempts.current++;
          
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current})`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          console.error('Max reconnection attempts reached');
        }
      };

      eventSourceRef.current = eventSource;
    } catch (error) {
      console.error('Failed to create SSE connection:', error);
    }
  }, [enabled, handleEvent]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttempts.current = 0;
    // Note: We intentionally don't clear lastEventTimeRef so reconnections can resume
  }, []);

  // Establish connection when enabled
  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  // Return connection control functions
  return {
    isConnected: eventSourceRef.current?.readyState === EventSource.OPEN,
    reconnect: connect,
    disconnect
  };
}