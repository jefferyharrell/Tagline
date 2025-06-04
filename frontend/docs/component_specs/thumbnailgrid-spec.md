# ThumbnailGrid Component Specification

## TypeScript Interface

```typescript
interface ThumbnailGridProps {
  children: React.ReactNode;
  className?: string;
  isLoading?: boolean;
  loadingCount: number;
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
}
```

## Component Behavior

### Core Functionality
- Renders children in a responsive grid layout
- Handles loading states with skeleton placeholders
- Shows empty state when no children provided
- Responsive design that adapts to screen size

### Layout Responsiveness
- Mobile (1 column): `grid-cols-1`
- Small tablet (2 columns): `sm:grid-cols-2` 
- Medium tablet (3 columns): `md:grid-cols-3`
- Desktop (4 columns): `lg:grid-cols-4`
- Large desktop (5 columns): `xl:grid-cols-5`
- Extra large (6 columns): `2xl:grid-cols-6`

### States
1. **Content State**: Display provided children in grid
2. **Loading State**: Show skeleton placeholders while content loads
3. **Empty State**: Show message and icon when no content available

## Visual Requirements

### Grid Layout
- **Gap**: `gap-6` between grid items
- **Aspect Ratio**: Children should maintain square aspect ratio
- **Background**: Inherit from parent (transparent)

### Loading State
- Show skeleton placeholders in grid layout using `loadingCount` prop
- Skeletons should match expected thumbnail dimensions
- Subtle pulse animation on skeletons

### Empty State
- Centered content with icon and message
- **Border**: Dashed border `border-2 border-dashed border-gray-300`
- **Background**: Light gray `bg-gray-50`
- **Padding**: Generous padding `p-16`
- **Corners**: Square corners (consistent with JLLA design)
- **Typography**: 
  - Heading: `text-sm font-medium text-gray-900`
  - Subtext: `text-sm text-gray-500`

### Responsive Behavior
- Grid should reflow naturally on screen size changes
- Maintain consistent gaps across all breakpoints
- Children should scale appropriately

## Technical Requirements

### Dependencies
- React 18+
- TypeScript
- Tailwind CSS
- Skeleton component from UI library

### Performance Considerations
- Component should be lightweight and fast to render
- No complex state management needed
- Should handle large numbers of children efficiently

### Accessibility
- Proper semantic HTML structure
- Grid should be navigable via keyboard
- Empty state should have appropriate ARIA labels

## Example Usage

```jsx
// Basic usage with photos
<ThumbnailGrid>
  {photos.map(photo => (
    <PhotoThumbnail 
      key={photo.object_key}
      media={photo}
      onClick={handlePhotoClick}
    />
  ))}
</ThumbnailGrid>

// Loading state
<ThumbnailGrid 
  isLoading={true} 
  loadingCount={18}
/>

// Empty state with custom message
<ThumbnailGrid 
  emptyMessage="No photos in this folder"
  emptyIcon={<CameraIcon className="w-12 h-12 text-gray-400" />}
>
  {/* No children = empty state */}
</ThumbnailGrid>

// Mixed media types (future use)
<ThumbnailGrid>
  <PhotoThumbnail media={photo1} onClick={handleClick} />
  <VideoThumbnail media={video1} onClick={handleClick} />
  <PhotoThumbnail media={photo2} onClick={handleClick} />
</ThumbnailGrid>

// With custom styling
<ThumbnailGrid className="mt-8 bg-white p-6 rounded-lg shadow">
  {thumbnails}
</ThumbnailGrid>
```

## Implementation Notes

### File Structure
- Create as: `components/ThumbnailGrid.tsx`
- Export as default export
- Include TypeScript interfaces in same file

### Default Props
- `className`: `""`
- `isLoading`: `false`
- `emptyMessage`: `"No items to display"`
- `emptyIcon`: Generic icon from Lucide React

### Error Handling
- Component should handle undefined/null children gracefully
- Should not crash if children array is malformed
- Fallback to empty state if children is not iterable

### Integration Points
- Should work seamlessly with existing PhotoThumbnail component
- Should be ready for future VideoThumbnail/AudioThumbnail components
- Should integrate with existing Skeleton component from UI library

### Testing Considerations
- Test responsive behavior at different screen sizes
- Test with various numbers of children (0, 1, many)
- Test loading and empty states
- Verify accessibility with screen readers
