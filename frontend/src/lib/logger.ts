/**
 * Frontend logging utility that sends logs to backend
 * 
 * This module provides a centralized logging system that:
 * - Supports different log levels (debug, info, warn, error)
 * - Batches log messages for efficiency
 * - Sends logs to backend for centralized debugging
 * - Falls back to console logging if backend is unavailable
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  component: string;
  url: string;
  user_agent: string;
  extra: Record<string, unknown>;
}

interface LogBatch {
  logs: LogEntry[];
  session_id: string;
}

class FrontendLogger {
  private logQueue: LogEntry[] = [];
  private batchTimeout: NodeJS.Timeout | null = null;
  private sessionId: string;
  private enabled: boolean = true;
  private readonly batchSize = 10;
  private readonly batchDelay = 2000; // 2 seconds
  
  constructor() {
    this.sessionId = this.generateSessionId();
    
    // Disable in production for now - can be enabled via env var
    if (typeof window !== 'undefined') {
      this.enabled = process.env.NODE_ENV === 'development' || 
                     window.localStorage.getItem('enableFrontendLogging') === 'true';
    }
  }
  
  private generateSessionId(): string {
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
  
  private getCurrentUrl(): string {
    if (typeof window === 'undefined') return '';
    return window.location.href;
  }
  
  private getUserAgent(): string {
    if (typeof window === 'undefined') return '';
    return window.navigator.userAgent;
  }
  
  private createLogEntry(
    level: LogLevel, 
    message: string, 
    component: string = 'frontend',
    extra: Record<string, unknown> = {}
  ): LogEntry {
    return {
      level,
      message,
      timestamp: new Date().toISOString(),
      component,
      url: this.getCurrentUrl(),
      user_agent: this.getUserAgent(),
      extra
    };
  }
  
  private async sendBatch(logs: LogEntry[]): Promise<void> {
    if (!this.enabled || logs.length === 0) return;
    
    try {
      const batch: LogBatch = {
        logs,
        session_id: this.sessionId
      };
      
      const response = await fetch('/api/logs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(batch),
        credentials: 'include' // Include auth cookies
      });
      
      if (!response.ok) {
        throw new Error(`Logging request failed: ${response.status}`);
      }
      
    } catch (error) {
      // Fallback to console logging if backend fails
      console.warn('Failed to send logs to backend, falling back to console:', error);
      logs.forEach(log => {
        const consoleMessage = `[${log.level.toUpperCase()}] ${log.component}: ${log.message}`;
        switch (log.level) {
          case 'debug':
            console.debug(consoleMessage, log.extra);
            break;
          case 'info':
            console.info(consoleMessage, log.extra);
            break;
          case 'warn':
            console.warn(consoleMessage, log.extra);
            break;
          case 'error':
            console.error(consoleMessage, log.extra);
            break;
        }
      });
    }
  }
  
  private scheduleBatch(): void {
    if (this.batchTimeout) return;
    
    this.batchTimeout = setTimeout(() => {
      this.flushLogs();
    }, this.batchDelay);
  }
  
  private flushLogs(): void {
    if (this.logQueue.length === 0) return;
    
    const logsToSend = [...this.logQueue];
    this.logQueue = [];
    
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
      this.batchTimeout = null;
    }
    
    this.sendBatch(logsToSend);
  }
  
  private addLog(level: LogLevel, message: string, component?: string, extra?: Record<string, unknown>): void {
    if (!this.enabled) return;
    
    const logEntry = this.createLogEntry(level, message, component, extra);
    this.logQueue.push(logEntry);
    
    // Send immediately for errors, or when batch is full
    if (level === 'error' || this.logQueue.length >= this.batchSize) {
      this.flushLogs();
    } else {
      this.scheduleBatch();
    }
  }
  
  // Public logging methods
  debug(message: string, component?: string, extra?: Record<string, unknown>): void {
    this.addLog('debug', message, component, extra);
  }
  
  info(message: string, component?: string, extra?: Record<string, unknown>): void {
    this.addLog('info', message, component, extra);
  }
  
  warn(message: string, component?: string, extra?: Record<string, unknown>): void {
    this.addLog('warn', message, component, extra);
  }
  
  error(message: string, component?: string, extra?: Record<string, unknown>): void {
    this.addLog('error', message, component, extra);
  }
  
  // Manually flush any pending logs
  flush(): void {
    this.flushLogs();
  }
  
  // Enable/disable logging
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    if (typeof window !== 'undefined') {
      if (enabled) {
        window.localStorage.setItem('enableFrontendLogging', 'true');
      } else {
        window.localStorage.removeItem('enableFrontendLogging');
      }
    }
  }
  
  isEnabled(): boolean {
    return this.enabled;
  }
}

// Create singleton instance
const logger = new FrontendLogger();

// Flush logs when page is unloading
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    logger.flush();
  });
}

export default logger;