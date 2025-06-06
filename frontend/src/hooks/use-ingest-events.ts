"use client";

import { useEffect, useRef, useCallback } from 'react';

export interface IngestEvent {
  object_key: string;
  has_thumbnail: boolean;
  ingestion_status: 'pending' | 'processing' | 'completed' | 'failed';
  event_type: 'media_ingested';
  timestamp?: string;
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
          if (data.type === 'media_ingested') {
            // Convert backend format to frontend format
            const ingestEvent: IngestEvent = {
              object_key: data.object_key,
              has_thumbnail: data.has_thumbnail,
              ingestion_status: data.ingestion_status,
              event_type: 'media_ingested',
              timestamp: data.timestamp
            };
            handleEvent(ingestEvent);
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