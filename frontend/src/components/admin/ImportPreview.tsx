'use client';

import { AlertCircle, UserPlus, UserMinus, RefreshCw } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';

interface UserChange {
  email: string;
  firstname?: string;
  lastname?: string;
  roles: string[];
  previous_roles?: string[];
}

interface ImportPreviewProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  preview: {
    to_add: UserChange[];
    to_update: UserChange[];
    to_deactivate: UserChange[];
    invalid_roles?: string[];
    validation_errors?: string[];
  } | null;
  onConfirm: () => void;
  loading?: boolean;
}

export function ImportPreview({
  open,
  onOpenChange,
  preview,
  onConfirm,
  loading = false,
}: ImportPreviewProps) {
  if (!preview) return null;

  const totalChanges = preview.to_add.length + preview.to_update.length + preview.to_deactivate.length;
  const hasErrors = (preview.validation_errors?.length || 0) > 0 || (preview.invalid_roles?.length || 0) > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Import Preview</DialogTitle>
          <DialogDescription>
            Review the changes that will be made to your user database.
            {totalChanges > 0 && ` ${totalChanges} total changes will be applied.`}
          </DialogDescription>
        </DialogHeader>

        {hasErrors && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <div className="space-y-1">
                {preview.validation_errors?.map((error, idx) => (
                  <div key={idx}>{error}</div>
                ))}
                {preview.invalid_roles && preview.invalid_roles.length > 0 && (
                  <div>Invalid roles found: {preview.invalid_roles.join(', ')}</div>
                )}
              </div>
            </AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue="add" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="add" className="flex items-center gap-2">
              <UserPlus className="w-4 h-4" />
              To Add ({preview.to_add.length})
            </TabsTrigger>
            <TabsTrigger value="update" className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4" />
              To Update ({preview.to_update.length})
            </TabsTrigger>
            <TabsTrigger value="deactivate" className="flex items-center gap-2">
              <UserMinus className="w-4 h-4" />
              To Deactivate ({preview.to_deactivate.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="add" className="mt-4">
            <ScrollArea className="h-[300px] w-full rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>First Name</TableHead>
                    <TableHead>Last Name</TableHead>
                    <TableHead>Roles</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.to_add.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center text-muted-foreground">
                        No new users to add
                      </TableCell>
                    </TableRow>
                  ) : (
                    preview.to_add.map((user) => (
                      <TableRow key={user.email}>
                        <TableCell className="font-mono text-sm">{user.email}</TableCell>
                        <TableCell>{user.firstname || '-'}</TableCell>
                        <TableCell>{user.lastname || '-'}</TableCell>
                        <TableCell>
                          <div className="flex gap-1 flex-wrap">
                            {user.roles.map((role) => (
                              <Badge key={role} variant="secondary" className="text-xs">
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
          </TabsContent>

          <TabsContent value="update" className="mt-4">
            <ScrollArea className="h-[300px] w-full rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>First Name</TableHead>
                    <TableHead>Last Name</TableHead>
                    <TableHead>Current Roles</TableHead>
                    <TableHead>New Roles</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.to_update.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground">
                        No users to update
                      </TableCell>
                    </TableRow>
                  ) : (
                    preview.to_update.map((user) => (
                      <TableRow key={user.email}>
                        <TableCell className="font-mono text-sm">{user.email}</TableCell>
                        <TableCell>{user.firstname || '-'}</TableCell>
                        <TableCell>{user.lastname || '-'}</TableCell>
                        <TableCell>
                          <div className="flex gap-1 flex-wrap">
                            {user.previous_roles?.map((role) => (
                              <Badge key={role} variant="outline" className="text-xs">
                                {role}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1 flex-wrap">
                            {user.roles.map((role) => (
                              <Badge key={role} variant="secondary" className="text-xs">
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
          </TabsContent>

          <TabsContent value="deactivate" className="mt-4">
            <ScrollArea className="h-[300px] w-full rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>First Name</TableHead>
                    <TableHead>Last Name</TableHead>
                    <TableHead>Roles to Remove</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.to_deactivate.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="text-center text-muted-foreground">
                        No users to deactivate
                      </TableCell>
                    </TableRow>
                  ) : (
                    preview.to_deactivate.map((user) => (
                      <TableRow key={user.email}>
                        <TableCell className="font-mono text-sm">{user.email}</TableCell>
                        <TableCell>{user.firstname || '-'}</TableCell>
                        <TableCell>{user.lastname || '-'}</TableCell>
                        <TableCell>
                          <div className="flex gap-1 flex-wrap">
                            {user.roles.map((role) => (
                              <Badge key={role} variant="destructive" className="text-xs">
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
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            disabled={loading || hasErrors}
          >
            {loading ? 'Importing...' : 'Confirm Import'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}