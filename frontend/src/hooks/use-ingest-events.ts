import { useEffect, useRef, useState, useCallback } from 'react';

interface IngestEvent {
  type: 'media_ingested' | 'heartbeat' | 'error';
  object_key?: string;
  job_id?: string;
  timestamp?: string;
  message?: string;
}

interface UseIngestEventsOptions {
  onMediaIngested?: (objectKey: string) => void;
  onError?: (error: string) => void;
  enabled?: boolean;
}

export function useIngestEvents(options: UseIngestEventsOptions = {}) {
  const { onMediaIngested, onError, enabled = true } = options;
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    setIsConnected(false);
  }, []);

  const connect = useCallback(() => {
    if (!enabled || eventSourceRef.current) return;

    const handleReconnect = () => {
      if (reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.pow(2, reconnectAttempts.current) * 1000; // Exponential backoff
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttempts.current++;
          disconnect();
          // Use setTimeout to avoid recursive call stack
          setTimeout(() => connect(), 0);
        }, delay);
      } else {
        setError('Failed to maintain connection after multiple attempts');
        if (onError) {
          onError('Connection lost');
        }
      }
    };

    try {
      const eventSource = new EventSource('/api/events/ingest');
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE connection opened');
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };

      eventSource.onmessage = (event) => {
        try {
          const data: IngestEvent = JSON.parse(event.data);
          
          switch (data.type) {
            case 'media_ingested':
              if (data.object_key && onMediaIngested) {
                onMediaIngested(data.object_key);
              }
              break;
            case 'error':
              if (data.message && onError) {
                onError(data.message);
              }
              break;
            case 'heartbeat':
              // Just keep the connection alive, no action needed
              break;
          }
        } catch (err) {
          console.error('Error parsing SSE event:', err);
        }
      };

      eventSource.onerror = () => {
        console.error('SSE connection error');
        setIsConnected(false);
        handleReconnect();
      };

    } catch (err) {
      console.error('Error creating SSE connection:', err);
      setError('Failed to create connection');
      if (onError) {
        onError('Failed to create connection');
      }
    }
  }, [enabled, onMediaIngested, onError, disconnect]);

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

  return {
    isConnected,
    error,
    connect,
    disconnect,
  };
}