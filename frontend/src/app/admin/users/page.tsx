'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Download, Users, UserCheck, Shield, Copy, ChevronDown, Check } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { TableVirtuoso } from 'react-virtuoso';
import { Separator } from '@/components/ui/separator';
import { 
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';

import { CSVUploader } from '@/components/admin/CSVUploader';
import { ImportPreview } from '@/components/admin/ImportPreview';
import { 
  parseUsersFromFile, 
  downloadCSV, 
  generateTSV,
  copyToClipboard,
  type UserData 
} from '@/lib/csv-utils';

interface UserChange {
  email: string;
  firstname?: string;
  lastname?: string;
  roles: string[];
  previous_roles?: string[];
}

interface User {
  id: string;
  email: string;
  firstname?: string;
  lastname?: string;
  is_active: boolean;
  roles: string[];
  created_at?: string;
}

interface Statistics {
  total_users: number;
  active_users: number;
  administrators: number;
}

interface ImportSummary {
  users_added: number;
  users_updated: number;
  users_deactivated: number;
  errors: string[];
  warnings: string[];
}

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [previewData, setPreviewData] = useState<{
    to_add: UserChange[];
    to_update: UserChange[];
    to_deactivate: UserChange[];
    invalid_roles?: string[];
    validation_errors?: string[];
  } | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [downloadPopoverOpen, setDownloadPopoverOpen] = useState(false);
  const [copyPopoverOpen, setCopyPopoverOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'active' | 'inactive' | 'all'>('active');

  // Filter users based on active status
  const filteredUsers = useMemo(() => {
    if (activeFilter === 'active') {
      return users.filter(user => user.is_active);
    } else if (activeFilter === 'inactive') {
      return users.filter(user => !user.is_active);
    }
    return users; // 'all'
  }, [users, activeFilter]);

  const handleDownloadPopoverChange = useCallback((open: boolean) => {
    setDownloadPopoverOpen(open);
  }, []);

  const handleCopyPopoverChange = useCallback((open: boolean) => {
    setCopyPopoverOpen(open);
  }, []);

  const fetchUsers = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      const response = await fetch('/api/admin/users?limit=10000');
      
      if (!response.ok) {
        throw new Error('Failed to fetch users');
      }
      
      const data = await response.json();
      setUsers(data.users || []);
      setStatistics(data.statistics || null);
    } catch (error) {
      console.error('Error fetching users:', error);
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const fetchUsersForExport = async (): Promise<UserData[]> => {
    const response = await fetch('/api/admin/users/export');
    if (!response.ok) {
      throw new Error('Failed to fetch users');
    }
    return response.json();
  };

  const handleDownloadFormat = async (format: 'csv' | 'tsv') => {
    try {
      setDownloadPopoverOpen(false); // Close the popover
      const userData = await fetchUsersForExport();
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');
      
      if (format === 'csv') {
        downloadCSV(userData, `tagline_users_${timestamp}.csv`);
      } else {
        // Download TSV format
        const tsvContent = generateTSV(userData);
        const blob = new Blob([tsvContent], { type: 'text/tab-separated-values;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `tagline_users_${timestamp}.tsv`;
        link.style.display = 'none';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
      }
      
      toast.success(`Users exported as ${format.toUpperCase()} successfully`);
    } catch (error) {
      console.error(`Error downloading ${format.toUpperCase()}:`, error);
      toast.error('Failed to export users');
    }
  };

  const handleCopyFormat = async (format: 'csv' | 'tsv') => {
    try {
      setCopyPopoverOpen(false); // Close the popover
      const userData = await fetchUsersForExport();
      await copyToClipboard(userData, format);
      toast.success(`Users copied as ${format.toUpperCase()} to clipboard`);
    } catch (error) {
      console.error('Error copying users:', error);
      toast.error('Failed to copy users to clipboard');
    }
  };

  const handleFileSelect = async (file: File) => {
    setSelectedFile(file);
    setUploadError(null);
    
    try {
      setUploadProgress(25);
      
      // Parse the file using our CSV utilities
      const parseResult = await parseUsersFromFile(file);
      
      setUploadProgress(50);
      
      if (parseResult.errors.length > 0) {
        const errorMessage = `Parsing errors:\n${parseResult.errors.join('\n')}`;
        setUploadError(errorMessage);
        return;
      }
      
      if (parseResult.data.length === 0) {
        setUploadError('No valid user data found in file');
        return;
      }
      
      // Send parsed data to preview endpoint
      const response = await fetch('/api/admin/users/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ users: parseResult.data }),
      });
      
      setUploadProgress(100);
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error('Preview error details:', errorData);
        
        // Handle different error formats - show actual backend errors
        let errorMessage = 'Failed to preview import';
        if (errorData.detail) {
          if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          } else if (Array.isArray(errorData.detail)) {
            // Pydantic validation errors - format them nicely
            const validationErrors = errorData.detail.map((err: { loc?: string[], msg?: string, input?: string }, index: number) => {
              const location = err.loc ? err.loc.join('.') : 'unknown';
              const message = err.msg || 'validation error';
              const input = err.input ? `"${err.input}"` : '';
              
              // Extract row number from location (e.g., "body.users.224.email" -> "Row 225")
              const rowMatch = location.match(/users\.(\d+)\./);
              const rowInfo = rowMatch ? `Row ${parseInt(rowMatch[1]) + 1}` : location;
              
              return `${index + 1}. ${rowInfo}: ${message}${input ? ` (${input})` : ''}`;
            });
            errorMessage = `Validation errors found:\n\n${validationErrors.join('\n\n')}`;
          } else {
            // Backend sent non-string, non-array data
            errorMessage = `Server error: ${JSON.stringify(errorData.detail)}`;
          }
        }
        
        throw new Error(errorMessage);
      }
      
      const preview = await response.json();
      setPreviewData(preview);
      setShowPreview(true);
    } catch (error) {
      console.error('Error previewing import:', error);
      setUploadError(error instanceof Error ? error.message : 'Failed to preview import');
    } finally {
      setUploadProgress(0);
    }
  };

  const handleConfirmImport = async () => {
    if (!selectedFile) return;
    
    try {
      setImporting(true);
      
      // Parse the file again to get the user data
      const parseResult = await parseUsersFromFile(selectedFile);
      
      if (parseResult.errors.length > 0) {
        throw new Error(`Parsing errors:\n${parseResult.errors.join('\n')}`);
      }
      
      // Send parsed data to sync endpoint
      const response = await fetch('/api/admin/users/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ users: parseResult.data }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        console.error('Sync error details:', errorData);
        
        // Handle different error formats - show actual backend errors
        let errorMessage = 'Failed to sync users';
        if (errorData.detail) {
          if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          } else if (Array.isArray(errorData.detail)) {
            // Pydantic validation errors - format them nicely
            const validationErrors = errorData.detail.map((err: { loc?: string[], msg?: string, input?: string }, index: number) => {
              const location = err.loc ? err.loc.join('.') : 'unknown';
              const message = err.msg || 'validation error';
              const input = err.input ? `"${err.input}"` : '';
              
              // Extract row number from location (e.g., "body.users.224.email" -> "Row 225")
              const rowMatch = location.match(/users\.(\d+)\./);
              const rowInfo = rowMatch ? `Row ${parseInt(rowMatch[1]) + 1}` : location;
              
              return `${index + 1}. ${rowInfo}: ${message}${input ? ` (${input})` : ''}`;
            });
            errorMessage = `Validation errors found:\n\n${validationErrors.join('\n\n')}`;
          } else {
            // Backend sent non-string, non-array data
            errorMessage = `Server error: ${JSON.stringify(errorData.detail)}`;
          }
        }
        
        throw new Error(errorMessage);
      }
      
      const result: ImportSummary = await response.json();
      
      // Show success message
      toast.success(
        `Sync completed: ${result.users_added} added, ${result.users_updated} updated, ${result.users_deactivated} deactivated`
      );
      
      // Show warnings if any
      if (result.warnings.length > 0) {
        result.warnings.forEach(warning => toast.warning(warning));
      }
      
      // Refresh the users list
      await fetchUsers();
      
      // Close preview and reset state
      setShowPreview(false);
      setPreviewData(null);
      setSelectedFile(null);
    } catch (error) {
      console.error('Error syncing users:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to sync users');
    } finally {
      setImporting(false);
    }
  };

  const getFullName = (user: User) => {
    const parts = [user.firstname, user.lastname].filter(Boolean);
    return parts.length > 0 ? parts.join(' ') : 'No name';
  };

  if (loading) {
    return <div className="p-8">Loading users...</div>;
  }

  return (
    <div className="container mx-auto p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">User Management</h1>
          <p className="text-muted-foreground">
            Manage JLLA member access via CSV import/export
          </p>
        </div>
      </div>

      {/* Statistics Cards */}
      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1">
              <CardTitle className="text-sm font-medium">Total Users</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-center">{statistics.total_users}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1">
              <CardTitle className="text-sm font-medium">Active Members</CardTitle>
              <UserCheck className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-center">{statistics.active_users}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1">
              <CardTitle className="text-sm font-medium">Administrators</CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-center">{statistics.administrators}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Current Users Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Current Users</CardTitle>
            <div className="flex items-center gap-2">
              <Popover open={downloadPopoverOpen} onOpenChange={handleDownloadPopoverChange}>
                <PopoverTrigger asChild>
                  <Button variant="outline">
                    <Download className="mr-2 h-4 w-4" />
                    Download
                    <ChevronDown className="ml-2 h-4 w-4" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-56" align="end">
                  <div className="grid gap-2">
                    <Button
                      variant="ghost"
                      className="justify-start h-auto py-2"
                      onClick={() => handleDownloadFormat('csv')}
                    >
                      <div className="text-left">
                        <div>Download as CSV</div>
                        <div className="text-xs text-muted-foreground">Comma-separated values</div>
                      </div>
                    </Button>
                    <Button
                      variant="ghost"
                      className="justify-start h-auto py-2"
                      onClick={() => handleDownloadFormat('tsv')}
                    >
                      <div className="text-left">
                        <div>Download as TSV</div>
                        <div className="text-xs text-muted-foreground">Best for Google Sheets</div>
                      </div>
                    </Button>
                  </div>
                </PopoverContent>
              </Popover>
              <Popover open={copyPopoverOpen} onOpenChange={handleCopyPopoverChange}>
                <PopoverTrigger asChild>
                  <Button variant="outline">
                    <Copy className="mr-2 h-4 w-4" />
                    Copy
                    <ChevronDown className="ml-2 h-4 w-4" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-56" align="end">
                  <div className="grid gap-2">
                    <Button
                      variant="ghost"
                      className="justify-start h-auto py-2"
                      onClick={() => handleCopyFormat('csv')}
                    >
                      <div className="text-left">
                        <div>Copy as CSV</div>
                        <div className="text-xs text-muted-foreground">Comma-separated values</div>
                      </div>
                    </Button>
                    <Button
                      variant="ghost"
                      className="justify-start h-auto py-2"
                      onClick={() => handleCopyFormat('tsv')}
                    >
                      <div className="text-left">
                        <div>TSV</div>
                        <div className="text-xs text-muted-foreground">Best for Google Sheets</div>
                      </div>
                    </Button>
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          </div>
        </CardHeader>
        
        {/* Filter Controls */}
        <div className="px-6 pb-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium">Show:</label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="w-40 justify-between">
                    {activeFilter === 'active' ? 'Active only' : 
                     activeFilter === 'inactive' ? 'Inactive only' : 'All users'}
                    <ChevronDown className="ml-2 h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-40">
                  <DropdownMenuItem onClick={() => setActiveFilter('active')}>
                    Active only
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setActiveFilter('inactive')}>
                    Inactive only
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setActiveFilter('all')}>
                    All users
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <div className="text-sm text-muted-foreground">
              Showing {filteredUsers.length} of {users.length} users
            </div>
          </div>
        </div>
        
        <CardContent>
          {filteredUsers.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              No users found
            </div>
          ) : (
            <TableVirtuoso
              style={{ height: '400px' }}
              data={filteredUsers}
              fixedHeaderContent={() => (
                <TableRow>
                  <TableHead style={{ width: '200px', minWidth: '200px' }}>Name</TableHead>
                  <TableHead style={{ width: '300px', minWidth: '300px' }}>Email</TableHead>
                  <TableHead style={{ width: '100px', minWidth: '100px' }} className="text-center">Active</TableHead>
                  <TableHead style={{ width: '200px', minWidth: '200px' }}>Roles</TableHead>
                </TableRow>
              )}
              components={{
                Table: ({ style, ...props }) => (
                  <Table {...props} style={{ ...style, width: '100%', tableLayout: 'fixed' }} />
                ),
                TableHead: ({ style, ...props }) => (
                  <TableHeader {...props} style={{ ...style }} />
                ),
                TableBody: ({ style, ...props }) => (
                  <TableBody {...props} style={{ ...style }} />
                ),
                TableRow: ({ style, ...props }) => (
                  <TableRow {...props} style={{ ...style }} />
                ),
              }}
              itemContent={(index, user) => (
                <>
                  <TableCell style={{ width: '200px', minWidth: '200px' }}>
                    <div>
                      <div className="font-medium">{getFullName(user)}</div>
                    </div>
                  </TableCell>
                  <TableCell className="font-mono text-sm" style={{ width: '300px', minWidth: '300px' }}>{user.email}</TableCell>
                  <TableCell style={{ width: '100px', minWidth: '100px' }}>
                    <div className="flex justify-center">
                      {user.is_active && (
                        <Check className="h-4 w-4" />
                      )}
                    </div>
                  </TableCell>
                  <TableCell style={{ width: '200px', minWidth: '200px' }}>
                    <div className="flex gap-1 flex-wrap">
                      {user.roles.map((role) => (
                        <Badge 
                          key={role} 
                          variant={role === 'administrator' ? 'destructive' : 'secondary'}
                          className="text-xs"
                        >
                          {role}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                </>
              )}
            />
          )}
        </CardContent>
      </Card>

      <Separator />

      {/* CSV Upload Section */}
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold mb-2">Import Users from File</h2>
          <p className="text-muted-foreground text-sm">
            Upload a CSV or TSV file to replace the entire user database. Format: firstname, lastname, email, [roles...]
          </p>
        </div>

        <Alert>
          <AlertDescription>
            <strong>Warning:</strong> This will replace your entire user database. 
            Users not in the CSV will be deactivated (except administrators). 
            Please download the current users first as a backup.
          </AlertDescription>
        </Alert>

        <CSVUploader
          onFileSelect={handleFileSelect}
          uploading={uploadProgress > 0}
          progress={uploadProgress}
          error={uploadError}
        />
      </div>

      {/* Import Preview Modal */}
      <ImportPreview
        open={showPreview}
        onOpenChange={setShowPreview}
        preview={previewData}
        onConfirm={handleConfirmImport}
        loading={importing}
      />
    </div>
  );
}