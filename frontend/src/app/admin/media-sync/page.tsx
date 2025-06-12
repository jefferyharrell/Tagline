'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Play, Pause, AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react'

interface IngestStatus {
  job_id: string
  status: string
  metadata: {
    path_filter?: string
    dry_run?: boolean
    current_stage?: string
    total_items?: number
    processed_items?: number
    queued_items?: number
    progress_percent?: number
    error_message?: string
  }
  enqueued_at?: string
  started_at?: string
  ended_at?: string
  duration_seconds?: number
}

interface OrchestratorEvent {
  event_type: 'orchestrator_progress' | 'orchestrator_complete'
  timestamp: string
  job_id: string
  stage: string
  total_items: number
  processed_items: number
  queued_items: number
  progress_percent: number
  path_filter?: string
  dry_run: boolean
  error?: string
}

export default function MediaSyncPage() {
  const [syncStatus, setSyncStatus] = useState<IngestStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isStarting, setIsStarting] = useState(false)
  const [eventSource, setEventSource] = useState<EventSource | null>(null)
  const [liveProgress, setLiveProgress] = useState<OrchestratorEvent | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Fetch current sync status
  const fetchSyncStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/admin/ingest/status', {
        credentials: 'include',
      })
      
      if (!response.ok) {
        throw new Error('Failed to fetch sync status')
      }
      
      const data = await response.json()
      setSyncStatus(data)
      setError(null)
    } catch (err) {
      console.error('Error fetching sync status:', err)
      setError('Failed to load sync status')
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Start media sync
  const startSync = async (dryRun: boolean = false) => {
    setIsStarting(true)
    setError(null)
    
    try {
      const response = await fetch('/api/admin/ingest/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          dry_run: dryRun,
        }),
      })
      
      const data = await response.json()
      
      if (response.status === 409) {
        setError('Sync is already running')
      } else if (!response.ok) {
        throw new Error(data.detail || 'Failed to start sync')
      } else {
        // Refresh status after starting
        await fetchSyncStatus()
        // Start listening to SSE events
        connectToSSE()
      }
    } catch (err) {
      console.error('Error starting sync:', err)
      setError(err instanceof Error ? err.message : 'Failed to start sync')
    } finally {
      setIsStarting(false)
    }
  }

  // Cancel running sync
  const cancelSync = async () => {
    try {
      const response = await fetch('/api/admin/ingest/cancel', {
        method: 'POST',
        credentials: 'include',
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to cancel sync')
      }
      
      // Refresh status after cancelling
      await fetchSyncStatus()
    } catch (err) {
      console.error('Error cancelling sync:', err)
      setError(err instanceof Error ? err.message : 'Failed to cancel sync')
    }
  }

  // Connect to Server-Sent Events for real-time updates
  const connectToSSE = () => {
    if (eventSource) {
      eventSource.close()
    }

    const source = new EventSource('/api/events/orchestrator', {
      withCredentials: true,
    })

    source.onopen = () => {
      console.log('Connected to orchestrator event stream')
    }

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.event_type === 'orchestrator_progress' || data.event_type === 'orchestrator_complete') {
          setLiveProgress(data)
          
          // If complete, refresh the full status
          if (data.event_type === 'orchestrator_complete') {
            fetchSyncStatus()
          }
        }
      } catch (err) {
        console.error('Error parsing SSE data:', err)
      }
    }

    source.onerror = (err) => {
      console.error('SSE error:', err)
      source.close()
      setEventSource(null)
    }

    setEventSource(source)
  }

  // Cleanup SSE on unmount
  useEffect(() => {
    fetchSyncStatus()
    
    // Connect to SSE if sync is running
    if (syncStatus?.status === 'started' || syncStatus?.status === 'queued') {
      connectToSSE()
    }
    
    return () => {
      if (eventSource) {
        eventSource.close()
      }
    }
  }, [])

  // Update connection when status changes
  useEffect(() => {
    if (syncStatus?.status === 'started' || syncStatus?.status === 'queued') {
      if (!eventSource) {
        connectToSSE()
      }
    } else {
      if (eventSource) {
        eventSource.close()
        setEventSource(null)
      }
    }
  }, [syncStatus?.status])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'started':
        return <Loader2 className="h-4 w-4 animate-spin" />
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-600" />
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-600" />
      case 'queued':
        return <Clock className="h-4 w-4 text-yellow-600" />
      default:
        return null
    }
  }

  const getStatusBadgeVariant = (status: string): "default" | "secondary" | "outline" | "destructive" => {
    switch (status) {
      case 'started':
        return 'default'
      case 'completed':
        return 'secondary'
      case 'failed':
        return 'destructive'
      default:
        return 'outline'
    }
  }

  const getDisplayStatus = (status: string) => {
    switch (status) {
      case 'not_found':
        return 'Not Started'
      case 'started':
        return 'Running'
      case 'queued':
        return 'Queued'
      case 'completed':
        return 'Completed'
      case 'failed':
        return 'Failed'
      default:
        return status
    }
  }

  // Use live progress if available and sync is running
  const displayProgress = liveProgress || syncStatus?.metadata
  const progressPercent = displayProgress?.progress_percent || 0

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Media Sync</h1>
        <p className="text-muted-foreground mt-2">
          Synchronize media files from storage provider to the database
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Sync Status</CardTitle>
          <CardDescription>
            Current status of the media synchronization process
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Status Overview */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {syncStatus && getStatusIcon(syncStatus.status)}
              <span className="text-lg font-medium">
                Status:{' '}
                <Badge variant={getStatusBadgeVariant(syncStatus?.status || 'not_found')}>
                  {getDisplayStatus(syncStatus?.status || 'not_found')}
                </Badge>
              </span>
            </div>
            
            <div className="flex gap-2">
              {(!syncStatus || syncStatus.status === 'not_found' || syncStatus.status === 'completed' || syncStatus.status === 'failed') && (
                <>
                  <Button
                    onClick={() => startSync(true)}
                    disabled={isStarting}
                    variant="outline"
                  >
                    {isStarting ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    Dry Run
                  </Button>
                  <Button
                    onClick={() => startSync(false)}
                    disabled={isStarting}
                  >
                    {isStarting ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    Start Sync
                  </Button>
                </>
              )}
              
              {(syncStatus?.status === 'started' || syncStatus?.status === 'queued') && (
                <Button
                  onClick={cancelSync}
                  variant="destructive"
                >
                  <Pause className="mr-2 h-4 w-4" />
                  Cancel
                </Button>
              )}
            </div>
          </div>

          {/* Progress */}
          {displayProgress && (syncStatus?.status === 'started' || syncStatus?.status === 'queued') && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Progress</span>
                <span>{progressPercent}%</span>
              </div>
              <Progress value={progressPercent} className="h-2" />
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>
                  {'stage' in displayProgress ? displayProgress.stage : displayProgress.current_stage || 'Processing'}
                </span>
                <span>
                  {displayProgress.processed_items || 0} / {displayProgress.total_items || 0} items
                </span>
              </div>
            </div>
          )}

          {/* Sync Details */}
          {syncStatus && syncStatus.status !== 'not_found' && (
            <div className="space-y-2 border-t pt-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Job ID:</span>
                  <p className="font-mono">{syncStatus.job_id}</p>
                </div>
                
                {syncStatus.started_at && (
                  <div>
                    <span className="text-muted-foreground">Started:</span>
                    <p>{new Date(syncStatus.started_at).toLocaleString()}</p>
                  </div>
                )}
                
                {syncStatus.duration_seconds && (
                  <div>
                    <span className="text-muted-foreground">Duration:</span>
                    <p>{Math.round(syncStatus.duration_seconds)} seconds</p>
                  </div>
                )}
                
                {syncStatus.metadata.path_filter && (
                  <div>
                    <span className="text-muted-foreground">Path Filter:</span>
                    <p>{syncStatus.metadata.path_filter}</p>
                  </div>
                )}
                
                {syncStatus.metadata.dry_run && (
                  <div>
                    <span className="text-muted-foreground">Mode:</span>
                    <p>Dry Run</p>
                  </div>
                )}
                
                {displayProgress?.queued_items !== undefined && (
                  <div>
                    <span className="text-muted-foreground">Queued for Processing:</span>
                    <p>{displayProgress.queued_items} items</p>
                  </div>
                )}
              </div>
              
              {syncStatus.metadata.error_message && (
                <Alert variant="destructive" className="mt-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Sync Error</AlertTitle>
                  <AlertDescription>{syncStatus.metadata.error_message}</AlertDescription>
                </Alert>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Information Card */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>About Media Sync</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>
            The media sync process scans all files in your storage provider and ensures they are
            properly indexed in the database with thumbnails and metadata.
          </p>
          <ul className="list-disc list-inside space-y-1">
            <li>
              <strong>Dry Run:</strong> Simulates the sync process without actually queuing files for processing
            </li>
            <li>
              <strong>Full Sync:</strong> Scans all files and queues any missing items for thumbnail generation
            </li>
            <li>
              Rate limited to 1 sync per hour to prevent system overload
            </li>
            <li>
              Only processes supported image formats (JPEG, PNG, HEIC)
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}