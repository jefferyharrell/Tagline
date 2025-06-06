"use client";

import React, { createContext, useContext, useEffect, useRef, useCallback, ReactNode } from 'react';

export interface IngestEvent {
  object_key: string;
  has_thumbnail: boolean;
  ingestion_status: 'pending' | 'processing' | 'completed' | 'failed';
  event_type: 'media_ingested';
  timestamp?: string;
}

interface SSEContextType {
  subscribe: (callback: (event: IngestEvent) => void) => () => void;
  isConnected: boolean;
}

const SSEContext = createContext<SSEContextType | null>(null);

export function SSEProvider({ children }: { children: ReactNode }) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const listenersRef = useRef<Set<(event: IngestEvent) => void>>(new Set());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 1000;
  const lastEventTimeRef = useRef<string | null>(null);
  const isConnectedRef = useRef(false);

  const notifyListeners = useCallback((event: IngestEvent) => {
    listenersRef.current.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error('Error in SSE event listener:', error);
      }
    });
  }, []);

  const connect = useCallback(() => {
    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      // Build URL with optional since parameter
      let url = '/api/events/ingest';
      if (lastEventTimeRef.current) {
        url += `?since=${encodeURIComponent(lastEventTimeRef.current)}`;
        console.log('🔄 SSE: Reconnecting with since parameter:', lastEventTimeRef.current);
      } else {
        console.log('🆕 SSE: First connection, no since parameter');
      }
      
      const eventSource = new EventSource(url, {
        withCredentials: true
      });

      eventSource.onopen = () => {
        console.log('✅ SSE: Connection established');
        reconnectAttempts.current = 0;
        isConnectedRef.current = true;
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'media_ingested') {
            const ingestEvent: IngestEvent = {
              object_key: data.object_key,
              has_thumbnail: data.has_thumbnail,
              ingestion_status: data.ingestion_status,
              event_type: 'media_ingested',
              timestamp: data.timestamp
            };
            
            // Track timestamp for reconnection
            if (ingestEvent.timestamp) {
              lastEventTimeRef.current = ingestEvent.timestamp;
            }
            
            // Notify all listeners
            notifyListeners(ingestEvent);
          }
        } catch (error) {
          console.error('❌ SSE: Failed to parse event:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('❌ SSE: Connection error:', error);
        eventSource.close();
        isConnectedRef.current = false;
        
        // Attempt to reconnect with exponential backoff
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = baseReconnectDelay * Math.pow(2, reconnectAttempts.current);
          reconnectAttempts.current++;
          
          console.log(`🔄 SSE: Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current})`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          console.error('❌ SSE: Max reconnection attempts reached');
        }
      };

      eventSourceRef.current = eventSource;
    } catch (error) {
      console.error('❌ SSE: Failed to create connection:', error);
      isConnectedRef.current = false;
    }
  }, [notifyListeners]);

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
    isConnectedRef.current = false;
  }, []);

  // Subscribe function for components to register callbacks
  const subscribe = useCallback((callback: (event: IngestEvent) => void) => {
    listenersRef.current.add(callback);
    
    // Return unsubscribe function
    return () => {
      listenersRef.current.delete(callback);
    };
  }, []);

  // Establish connection on mount
  useEffect(() => {
    console.log('🚀 SSE: Provider mounting, establishing connection');
    connect();

    return () => {
      console.log('🛑 SSE: Provider unmounting, closing connection');
      disconnect();
    };
  }, [connect, disconnect]);

  const value: SSEContextType = {
    subscribe,
    isConnected: isConnectedRef.current
  };

  return (
    <SSEContext.Provider value={value}>
      {children}
    </SSEContext.Provider>
  );
}

export function useSSE() {
  const context = useContext(SSEContext);
  if (!context) {
    throw new Error('useSSE must be used within SSEProvider');
  }
  return context;
}