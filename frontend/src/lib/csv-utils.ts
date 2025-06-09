/**
 * CSV/TSV utilities using Papa Parse
 * 
 * Handles conversion between JSON user data and CSV/TSV formats
 * for import/export functionality in user management.
 */

import Papa from 'papaparse';

export interface UserData {
  email: string;
  firstname?: string;
  lastname?: string;
  roles: string[];
}

export interface ParseResult {
  data: UserData[];
  errors: string[];
}

/**
 * Parse CSV or TSV content into user data array
 */
export function parseUsersFromText(content: string): ParseResult {
  const errors: string[] = [];
  
  // Auto-detect delimiter by checking first line
  const firstLine = content.split('\n')[0] || '';
  const delimiter = firstLine.includes('\t') && firstLine.split('\t').length > firstLine.split(',').length ? '\t' : ',';
  
  // Parse with Papa Parse - don't use header mode for variable columns
  const parseResult = Papa.parse(content, {
    delimiter,
    header: false,
    skipEmptyLines: true,
  });

  if (parseResult.errors.length > 0) {
    errors.push(...parseResult.errors.map(err => {
      // Debug: log the full error object to see what Papa Parse returns
      console.log('Papa Parse error object:', err);
      
      // Handle different error object structures
      if (typeof err === 'string') {
        return err;
      }
      
      // For object errors, try to extract meaningful information
      const parts = [];
      
      if (err.row !== undefined) {
        parts.push(`Row ${err.row + 1}`);
      }
      
      if (err.type) {
        parts.push(`Type: ${err.type}`);
      }
      
      if (err.code) {
        parts.push(`Code: ${err.code}`);
      }
      
      if (err.message) {
        parts.push(err.message);
      } else if (typeof err === 'object') {
        // If no message property, stringify the whole object as fallback
        parts.push(JSON.stringify(err));
      }
      
      return parts.length > 0 ? parts.join(' - ') : 'Unknown error';
    }));
  }

  const users: UserData[] = [];
  const rows = parseResult.data as string[][];
  
  if (rows.length === 0) {
    errors.push('No data found in file');
    return { data: users, errors };
  }
  
  // Check if first row looks like a header (contains 'firstname', 'lastname', 'email', etc.)
  const firstRow = rows[0];
  const isHeader = firstRow && firstRow.length >= 3 && (
    firstRow[0]?.toLowerCase().includes('firstname') ||
    firstRow[1]?.toLowerCase().includes('lastname') ||
    firstRow[2]?.toLowerCase().includes('email') ||
    firstRow.some(cell => cell?.toLowerCase() === 'email')
  );
  
  // Start from row 1 if header, row 0 if no header
  const startRow = isHeader ? 1 : 0;
  
  for (let i = startRow; i < rows.length; i++) {
    const row = rows[i];
    const rowNum = i + 1; // Row number for error reporting (1-based)
    
    // Skip empty rows
    if (!row || row.length === 0 || row.every(cell => !cell || !cell.trim())) {
      continue;
    }
    
    // Validate minimum required fields (firstname, lastname, email)
    if (row.length < 3) {
      errors.push(`Row ${rowNum}: Insufficient columns. Expected at least 3 (firstname, lastname, email)`);
      continue;
    }
    
    const firstname = row[0]?.trim() || '';
    const lastname = row[1]?.trim() || '';
    const email = row[2]?.trim();
    
    // Validate email
    if (!email || !email.includes('@')) {
      errors.push(`Row ${rowNum}: Missing or invalid email`);
      continue;
    }

    // Extract roles from remaining columns (index 3+)
    const roles: string[] = [];
    for (let j = 3; j < row.length; j++) {
      const roleValue = row[j]?.trim();
      if (roleValue && roleValue !== '…') {
        roles.push(roleValue);
      }
    }

    users.push({
      email: email.toLowerCase(),
      firstname,
      lastname,
      roles,
    });
  }

  return { data: users, errors };
}

/**
 * Parse uploaded file into user data array
 */
export function parseUsersFromFile(file: File): Promise<ParseResult> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (!content) {
        resolve({ data: [], errors: ['Failed to read file content'] });
        return;
      }
      
      try {
        const result = parseUsersFromText(content);
        resolve(result);
      } catch (error) {
        resolve({ 
          data: [], 
          errors: [`Error parsing file: ${error instanceof Error ? error.message : 'Unknown error'}`] 
        });
      }
    };
    
    reader.onerror = () => {
      resolve({ data: [], errors: ['Failed to read file'] });
    };
    
    reader.readAsText(file);
  });
}

/**
 * Convert user data array to CSV format
 */
export function generateCSV(users: UserData[]): string {
  if (users.length === 0) {
    return 'firstname,lastname,email,role,…\n';
  }

  // Sort users by lastname, firstname, email
  const sortedUsers = [...users].sort((a, b) => {
    const aLast = (a.lastname || '').toLowerCase();
    const bLast = (b.lastname || '').toLowerCase();
    const aFirst = (a.firstname || '').toLowerCase();
    const bFirst = (b.firstname || '').toLowerCase();
    
    if (aLast !== bLast) return aLast.localeCompare(bLast);
    if (aFirst !== bFirst) return aFirst.localeCompare(bFirst);
    return a.email.localeCompare(b.email);
  });

  // Create rows with variable columns for roles
  const rows: string[][] = [];
  
  // Header row
  rows.push(['firstname', 'lastname', 'email', 'role', '…']);
  
  // Data rows
  for (const user of sortedUsers) {
    const row = [
      user.firstname || '',
      user.lastname || '',
      user.email,
      // Sort roles consistently (member first, admin second, others alphabetically)
      ...user.roles.sort((a, b) => {
        if (a === 'member' && b !== 'member') return -1;
        if (b === 'member' && a !== 'member') return 1;
        if (a === 'administrator' && b !== 'administrator') return -1;
        if (b === 'administrator' && a !== 'administrator') return 1;
        return a.localeCompare(b);
      })
    ];
    rows.push(row);
  }

  return Papa.unparse(rows, {
    delimiter: ',',
    header: false,
  });
}

/**
 * Convert user data array to TSV format
 */
export function generateTSV(users: UserData[]): string {
  if (users.length === 0) {
    return 'firstname\tlastname\temail\trole\t…\n';
  }

  // Sort users by lastname, firstname, email
  const sortedUsers = [...users].sort((a, b) => {
    const aLast = (a.lastname || '').toLowerCase();
    const bLast = (b.lastname || '').toLowerCase();
    const aFirst = (a.firstname || '').toLowerCase();
    const bFirst = (b.firstname || '').toLowerCase();
    
    if (aLast !== bLast) return aLast.localeCompare(bLast);
    if (aFirst !== bFirst) return aFirst.localeCompare(bFirst);
    return a.email.localeCompare(b.email);
  });

  // Create rows with variable columns for roles
  const rows: string[][] = [];
  
  // Header row
  rows.push(['firstname', 'lastname', 'email', 'role', '…']);
  
  // Data rows
  for (const user of sortedUsers) {
    const row = [
      user.firstname || '',
      user.lastname || '',
      user.email,
      // Sort roles consistently (member first, admin second, others alphabetically)
      ...user.roles.sort((a, b) => {
        if (a === 'member' && b !== 'member') return -1;
        if (b === 'member' && a !== 'member') return 1;
        if (a === 'administrator' && b !== 'administrator') return -1;
        if (b === 'administrator' && a !== 'administrator') return 1;
        return a.localeCompare(b);
      })
    ];
    rows.push(row);
  }

  return Papa.unparse(rows, {
    delimiter: '\t',
    header: false,
  });
}

/**
 * Download user data as CSV file
 */
export function downloadCSV(users: UserData[], filename: string = 'users.csv'): void {
  const csvContent = generateCSV(users);
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  URL.revokeObjectURL(url);
}

/**
 * Copy user data to clipboard in specified format
 */
export async function copyToClipboard(users: UserData[], format: 'csv' | 'tsv' = 'tsv'): Promise<void> {
  const content = format === 'csv' ? generateCSV(users) : generateTSV(users);
  await navigator.clipboard.writeText(content);
}