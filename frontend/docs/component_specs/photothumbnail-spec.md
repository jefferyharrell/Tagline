# PhotoThumbnail Component Specification

## TypeScript Interface

```typescript
interface PhotoThumbnailProps {
  media: MediaObject;
  onClick: (media: MediaObject) => void;
  className?: string;
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
- Renders a clickable square thumbnail for a photo
- Calls `onClick(media)` when the thumbnail is clicked
- Handles loading states gracefully
- Shows processing indicator for pending media

### State Management
- `isImageLoaded`: Track if thumbnail image has loaded
- `isHovered`: Track hover state for visual feedback

### Loading States
1. **Pending/Processing**: Show skeleton with "Processing..." overlay
2. **Loading**: Show skeleton while image loads
3. **Loaded**: Show actual thumbnail image
4. **Error**: Show placeholder with error indication

## Visual Requirements

### Layout
- **Aspect Ratio**: Perfect square (1:1)
- **Corners**: Sharp/square corners (not rounded) per JLLA design language
- **Background**: White background for the card

### States

#### Default State
- Clean white background
- Subtle drop shadow: `shadow-sm`
- Square corners
- Thumbnail image fills the square area

#### Hover State
- Slight scale transform: `scale-105`
- Enhanced shadow: `shadow-md`
- Smooth transition (200ms)

#### Loading State
- Gray skeleton background
- Subtle pulse animation
- Image icon placeholder in center

#### Processing State (for pending ingestion)
- Skeleton background with overlay
- Semi-transparent dark overlay with "Processing..." text
- Small loading spinner or pulse animation

### Typography & Spacing
- No text content on thumbnail itself (keep it clean)
- Padding around image content: `p-0` (full bleed)
- Use Tailwind classes consistent with existing app

## Technical Requirements

### Dependencies
- React 18+
- TypeScript
- Tailwind CSS
- Lucide React (for icons if needed)

### API Endpoint
- Thumbnail images served from: `/api/library/${encodeURIComponent(media.object_key)}/thumbnail`

### Error Handling
- Gracefully handle missing thumbnails
- Show appropriate placeholder for failed image loads
- Don't crash if `media` object is malformed

## Example Usage

```jsx
// Basic usage
<PhotoThumbnail 
  media={photoObject} 
  onClick={(media) => openModal(media)} 
/>

// With custom styling
<PhotoThumbnail 
  media={photoObject} 
  onClick={handlePhotoClick}
  className="border-2 border-gray-200"
/>

// In a grid context
<div className="grid grid-cols-6 gap-6">
  {photos.map(photo => (
    <PhotoThumbnail 
      key={photo.object_key}
      media={photo}
      onClick={handlePhotoClick}
    />
  ))}
</div>
```

## Implementation Notes

### File Structure
- Create as: `components/PhotoThumbnail.tsx`
- Export as default export
- Include TypeScript interfaces in same file

### Performance Considerations
- Use lazy loading for images
- Implement proper error boundaries
- Optimize for grid rendering (avoid unnecessary re-renders)

### Accessibility
- Include proper alt text for images
- Ensure keyboard navigation works
- Use semantic HTML elements

### Testing Considerations
- Component should handle missing/malformed props gracefully
- Should work with different screen sizes
- Should handle slow image loading
