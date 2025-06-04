# LibraryView Component Specification

## TypeScript Interface

```typescript
interface LibraryViewProps {
  initialPath: string;
  className?: string;
}

interface BrowseResponse {
  folders: FolderItem[];
  media_objects: MediaObject[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

interface FolderItem {
  name: string;
  is_folder: boolean;
}

interface MediaObject {
  object_key: string;
  has_thumbnail: boolean;
  metadata?: {
    description?: string;
    [key: string]: any;
  };
  ingestion_status?: 'pending' | 'complete' | 'error';
}
```

## Component Behavior

### Core Functionality
- Manages folder navigation and photo display for `/library` routes
- Fetches folders and photos from `/api/library` endpoint
- Handles folder navigation by updating current path
- Manages photo modal display and navigation
- Synchronizes browser URL with current path

### State Management
- `currentPath`: Array of folder names representing current location
- `folders`: Array of folders at current path
- `photos`: Array of photos at current path
- `isLoading`: Loading state during data fetching
- `selectedPhoto`: Currently selected photo for modal
- `isModalOpen`: Modal visibility state
- `error`: Error state for failed requests

### Data Fetching
- Fetch on component mount using `initialPath`
- Re-fetch when `currentPath` changes
- Single API call to `/api/library?path=${pathString}`
- Handle loading and error states appropriately

### Navigation Handling
- Folder clicks update `currentPath` and trigger new data fetch
- Breadcrumb clicks navigate to specific path levels
- URL updates reflect current path changes
- Browser back/forward should work correctly

### Photo Click Handling
- Normal click: Open modal with photo details
- Cmd/Ctrl + click: Allow browser navigation to `/media/{object_key}`
- Middle click: Allow browser navigation to `/media/{object_key}`
- Pass event details to photo click handler for proper routing

## Visual Requirements

### Layout Structure
```
┌─── Breadcrumb Navigation ───┐
├─── Folder List (if any) ────┤
├─── Photo Grid ──────────────┤
└─── Modal (when open) ───────┘
```

### Spacing and Layout
- **Container**: Clean vertical stack with consistent spacing
- **Sections**: Clear separation between breadcrumbs, folders, and photos
- **Background**: Inherit from parent (likely gray-50)
- **Responsive**: Should work on desktop, tablet, and mobile

### Loading States
- Show loading skeletons while fetching data
- Maintain layout structure during loading
- Progressive loading for individual photo thumbnails

### Error States
- Display error message for failed API requests
- Provide retry mechanism for failed loads
- Graceful degradation when possible

## Technical Requirements

### Dependencies
- React 18+
- TypeScript
- Next.js (for routing)
- Existing components: FolderList, ThumbnailGrid, PhotoThumbnail
- Existing MediaModal component (reuse for now)

### API Integration
- **Endpoint**: `/api/library?path=${encodeURIComponent(pathString)}`
- **Response**: BrowseResponse with folders and media_objects
- **Error handling**: Handle network errors, 404s, and malformed responses

### URL Synchronization
- Update browser URL when path changes
- Handle browser back/forward navigation
- Use Next.js router for navigation
- Encode/decode path segments properly

### Performance Considerations
- Efficient re-rendering when data changes
- Proper cleanup of event listeners and timers
- Optimize for common navigation patterns

## Example Usage

```jsx
// Basic usage (root library)
<LibraryView initialPath="" />

// Nested folder path
<LibraryView initialPath="2024-2025 League Year/Events" />

// With custom styling
<LibraryView 
  initialPath="photos/recent"
  className="container mx-auto py-8"
/>
```

## Implementation Notes

### File Structure
- Create as: `components/LibraryView.tsx`
- Export as default export
- Include TypeScript interfaces in same file

### Path Handling
- Convert `initialPath` string to array: `initialPath.split('/').filter(Boolean)`
- Handle URL encoding/decoding of path segments
- Empty string initialPath = root library view

### Error Recovery
- Graceful handling of malformed path parameters
- Fallback to root library on navigation errors
- Clear error states on successful navigation

### Modal Integration
- Reuse existing MediaModal component
- Pass selected photo data to modal
- Handle modal close and URL restoration
- Ensure modal covers full viewport (uses portals)

### Event Handling
- Folder click: `(folderName) => setCurrentPath([...currentPath, folderName])`
- Photo click: `(photo, event) => handlePhotoClick(photo, event)`
- Breadcrumb click: `(index) => setCurrentPath(currentPath.slice(0, index + 1))`

### Integration Points
- Should integrate with existing routing system
- Compatible with sidebar layout structure
- Modal should work within nested component hierarchy
- Breadcrumb styling should match existing patterns

## Future Considerations

### Extensibility
- Component designed to work with planned `/search` page separation
- Modal architecture ready for PhotoView component when available
- Path structure flexible for future organization schemes

### Performance Optimization
- Ready for future pagination if needed
- Component structure supports caching strategies
- Data fetching pattern can be enhanced without interface changes
