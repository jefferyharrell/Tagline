'use client';

import { useState, useEffect, useCallback } from 'react';
import { Download, Users, UserCheck, Shield, Copy, ChevronDown } from 'lucide-react';
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
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { toast } from 'sonner';

import { CSVUploader } from '@/components/admin/CSVUploader';
import { ImportPreview } from '@/components/admin/ImportPreview';
import { 
  parseUsersFromFile, 
  generateCSV, 
  generateTSV, 
  downloadCSV, 
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

  const fetchUsers = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      const response = await fetch('/api/admin/users');
      
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

  const handleDownloadCSV = async () => {
    try {
      const userData = await fetchUsersForExport();
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');
      downloadCSV(userData, `tagline_users_${timestamp}.csv`);
      toast.success('Users exported successfully');
    } catch (error) {
      console.error('Error downloading CSV:', error);
      toast.error('Failed to export users');
    }
  };

  const handleCopyFormat = async (format: 'tsv') => {
    try {
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
            const validationErrors = errorData.detail.map((err: any, index: number) => {
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
            const validationErrors = errorData.detail.map((err: any, index: number) => {
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
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Users</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_users}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Members</CardTitle>
              <UserCheck className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.active_users}</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Administrators</CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.administrators}</div>
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
              <Button onClick={handleDownloadCSV} variant="outline">
                <Download className="mr-2 h-4 w-4" />
                Download
              </Button>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline">
                    <Copy className="mr-2 h-4 w-4" />
                    Copy
                    <ChevronDown className="ml-2 h-4 w-4" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-40" align="end">
                  <div className="grid gap-2">
                    <Button
                      variant="ghost"
                      className="justify-start"
                      onClick={() => handleCopyFormat('tsv')}
                    >
                      Copy as TSV
                    </Button>
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[400px] w-full">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Roles</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground">
                      No users found
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{getFullName(user)}</div>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{user.email}</TableCell>
                      <TableCell>
                        <Badge variant={user.is_active ? 'default' : 'secondary'}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell>
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
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </ScrollArea>
        </CardContent>
      </Card>

      <Separator />

      {/* CSV Upload Section */}
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold mb-2">Import Users from CSV</h2>
          <p className="text-muted-foreground text-sm">
            Upload a CSV file to replace the entire user database. Format: firstname, lastname, email, [roles...]
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