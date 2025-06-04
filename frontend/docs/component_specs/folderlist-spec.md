# FolderList Component Specification

## TypeScript Interface

```typescript
interface FolderListProps {
  folders: FolderItem[];
  onFolderClick: (folderName: string) => void;
  className?: string;
  emptyMessage?: string;
}

interface FolderItem {
  name: string;
  is_folder: boolean; // Should always be true for folders
}
```

## Component Behavior

### Core Functionality
- Renders a vertical list of clickable folder items
- Calls `onFolderClick(folderName)` when a folder is clicked
- Displays folders in natural sort order
- Shows empty state when no folders provided

### Interaction
- Each folder row is a clickable button with hover effects
- Click calls the provided `onFolderClick` handler with folder name
- Keyboard navigation support (Tab/Enter)
- Proper focus management

### Sorting
- Folders should be displayed in natural sort order (alphanumeric)
- Component handles sorting internally, not relying on prop order

## Visual Requirements

### Layout
- **Container**: Clean white background with subtle border
- **Spacing**: Consistent padding and margins
- **Dividers**: Thin gray lines between folder items
- **Corners**: Square corners (consistent with JLLA design)

### Folder Items
- **Layout**: Horizontal row with icon + text
- **Icon**: Folder icon from Lucide React, colored with JLLA red (`text-jl-red`)
- **Typography**: Clean, readable text
- **Padding**: Comfortable click target (`px-6 py-3`)

### States

#### Default State
- Clean folder row with icon and name
- Subtle hover effect (`hover:bg-gray-50`)
- Smooth transitions

#### Hover State
- Light gray background
- No scale effects (keep it subtle)
- Transition duration: 150ms

#### Empty State
- Centered message in container
- Subtle styling to indicate no content
- Same styling approach as ThumbnailGrid empty state

### Visual Structure
```
┌─────────────────────────────────┐
│ 📁 2024-2025 League Year        │
├─────────────────────────────────┤
│ 📁 test1                        │
├─────────────────────────────────┤
│ 📁 Member Photos                │
└─────────────────────────────────┘
```

## Technical Requirements

### Dependencies
- React 18+
- TypeScript
- Tailwind CSS
- Lucide React (for Folder icon)

### Sorting Implementation
- Use natural sort algorithm for folder names
- Handle mixed alphanumeric folder names correctly
- Case-insensitive sorting

### Performance
- Component should be lightweight
- Efficient re-rendering when folders change
- No unnecessary state management

### Accessibility
- Proper semantic HTML (button elements for clickable items)
- ARIA labels for screen readers
- Keyboard navigation support
- Focus indicators

## Example Usage

```jsx
// Basic usage
<FolderList 
  folders={folderArray} 
  onFolderClick={(name) => navigateToFolder(name)} 
/>

// With custom styling and empty message
<FolderList 
  folders={folders}
  onFolderClick={handleFolderClick}
  className="mt-4 shadow-sm"
  emptyMessage="No subfolders in this directory"
/>

// In context with other components
<div className="bg-white rounded-lg shadow-sm overflow-hidden">
  <BreadcrumbNavigation path={currentPath} />
  <FolderList 
    folders={folders}
    onFolderClick={handleFolderClick}
  />
</div>
```

## Implementation Notes

### File Structure
- Create as: `components/FolderList.tsx`
- Export as default export
- Include TypeScript interfaces in same file

### Default Props
- `className`: `""`
- `emptyMessage`: `"No subfolders in this directory"`

### Natural Sorting
- Implement or import natural sort function
- Should handle cases like: `folder1`, `folder2`, `folder10` (not `folder1`, `folder10`, `folder2`)

### Error Handling
- Handle empty or undefined folders array gracefully
- Handle malformed folder objects
- Don't crash if onFolderClick is undefined

### Integration Points
- Should integrate with existing navigation system
- Should work with current breadcrumb component
- Styling should match existing white card containers

### Styling Consistency
- Use JLLA red for folder icons: `text-jl-red`
- Match hover effects with other interactive components
- Consistent with square corners design language
- Border and shadow styling consistent with other cards
