"use client";

import React, { useState, useCallback, useEffect } from "react";
import type { MediaObject } from "@/types/media";

interface NavigationState {
  hasPrev: boolean;
  hasNext: boolean;
}

interface MediaImageViewerProps {
  media: MediaObject;
  onNavigate?: (direction: 'prev' | 'next') => void;
  navigationState?: NavigationState;
}

export default function MediaImageViewer({
  media,
  onNavigate,
  navigationState,
}: MediaImageViewerProps) {
  const [imageLoaded, setImageLoaded] = useState(false);
  
  // Touch gesture state
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  const [touchEnd, setTouchEnd] = useState<{ x: number; y: number } | null>(null);
  const [swipeProgress, setSwipeProgress] = useState(0);
  const [swipeDirection, setSwipeDirection] = useState<'left' | 'right' | null>(null);
  const [isSwipeActive, setIsSwipeActive] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Swipe configuration
  const minSwipeDistance = 80; // Increased threshold for better feel

  // Navigation handlers with smooth transitions
  const handleLeftClick = useCallback(() => {
    if (navigationState?.hasPrev && onNavigate && !isTransitioning) {
      setIsTransitioning(true);
      setSwipeDirection('right');
      setSwipeProgress(1);
      
      // Brief slide animation then navigate
      setTimeout(() => {
        onNavigate('prev');
        setIsTransitioning(false);
        setSwipeDirection(null);
        setSwipeProgress(0);
      }, 200);
    }
  }, [navigationState, onNavigate, isTransitioning]);

  const handleRightClick = useCallback(() => {
    if (navigationState?.hasNext && onNavigate && !isTransitioning) {
      setIsTransitioning(true);
      setSwipeDirection('left');
      setSwipeProgress(1);
      
      // Brief slide animation then navigate
      setTimeout(() => {
        onNavigate('next');
        setIsTransitioning(false);
        setSwipeDirection(null);
        setSwipeProgress(0);
      }, 200);
    }
  }, [navigationState, onNavigate, isTransitioning]);

  // Touch handlers for swipe navigation with visual feedback
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.targetTouches[0];
    setTouchStart({ x: touch.clientX, y: touch.clientY });
    setTouchEnd(null);
    setIsSwipeActive(true);
    setSwipeProgress(0);
    setSwipeDirection(null);
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    const touch = e.targetTouches[0];
    setTouchEnd({ x: touch.clientX, y: touch.clientY });
    
    if (touchStart) {
      const deltaX = touch.clientX - touchStart.x;
      const deltaY = touch.clientY - touchStart.y;
      
      // Only track horizontal swipes (ignore mostly vertical swipes)
      if (Math.abs(deltaX) > Math.abs(deltaY)) {
        const direction = deltaX > 0 ? 'right' : 'left';
        const distance = Math.abs(deltaX);
        const progress = Math.min(distance / minSwipeDistance, 1);
        
        // Check if this direction is allowed
        const canSwipe = (direction === 'right' && navigationState?.hasPrev) || 
                        (direction === 'left' && navigationState?.hasNext);
        
        if (canSwipe) {
          setSwipeDirection(direction);
          setSwipeProgress(progress);
        } else {
          // Reduced movement for disabled directions
          setSwipeDirection(direction);
          setSwipeProgress(Math.min(progress * 0.3, 0.3));
        }
      }
    }
  }, [touchStart, navigationState, minSwipeDistance]);

  const handleTouchEnd = useCallback(() => {
    if (!touchStart || !touchEnd) {
      setIsSwipeActive(false);
      setSwipeProgress(0);
      setSwipeDirection(null);
      return;
    }
    
    const deltaX = touchEnd.x - touchStart.x;
    const deltaY = touchEnd.y - touchStart.y;
    
    // Only consider horizontal swipes (ignore mostly vertical swipes)
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
      if (deltaX > 0 && navigationState?.hasPrev) {
        // Swipe right - go to previous
        setIsTransitioning(true);
        setTimeout(() => {
          handleLeftClick();
          setIsTransitioning(false);
          setIsSwipeActive(false);
          setSwipeProgress(0);
          setSwipeDirection(null);
        }, 150);
      } else if (deltaX < 0 && navigationState?.hasNext) {
        // Swipe left - go to next
        setIsTransitioning(true);
        setTimeout(() => {
          handleRightClick();
          setIsTransitioning(false);
          setIsSwipeActive(false);
          setSwipeProgress(0);
          setSwipeDirection(null);
        }, 150);
      } else {
        // Snap back - incomplete or invalid swipe
        setIsSwipeActive(false);
        setTimeout(() => {
          setSwipeProgress(0);
          setSwipeDirection(null);
        }, 200);
      }
    } else {
      // Not a horizontal swipe - reset
      setIsSwipeActive(false);
      setTimeout(() => {
        setSwipeProgress(0);
        setSwipeDirection(null);
      }, 200);
    }
    
    setTouchStart(null);
    setTouchEnd(null);
  }, [touchStart, touchEnd, handleLeftClick, handleRightClick, navigationState, minSwipeDistance]);

  // Reset image loaded state when media object key changes
  useEffect(() => {
    setImageLoaded(false);
  }, [media.object_key]);

  return (
    <div 
      className="relative inline-block overflow-hidden"
      onTouchStart={onNavigate ? handleTouchStart : undefined}
      onTouchMove={onNavigate ? handleTouchMove : undefined}
      onTouchEnd={onNavigate ? handleTouchEnd : undefined}
    >
      {/* Swipe overlay background */}
      {isSwipeActive && swipeProgress > 0 && (
        <div 
          className={`absolute inset-0 z-0 transition-opacity duration-100 ${(() => {
            // Check if this direction is allowed
            const canSwipe = (swipeDirection === 'right' && navigationState?.hasPrev) || 
                            (swipeDirection === 'left' && navigationState?.hasNext);
            
            if (!canSwipe) {
              return swipeDirection === 'right' ? 'bg-gradient-to-r from-red-500/20 to-transparent' : 
                                                 'bg-gradient-to-l from-red-500/20 to-transparent';
            }
            
            return swipeDirection === 'right' ? 'bg-gradient-to-r from-blue-500/20 to-transparent' : 
                                               'bg-gradient-to-l from-green-500/20 to-transparent';
          })()}`}
          style={{ opacity: Math.min(swipeProgress, 0.6) }}
        />
      )}

      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/library/${encodeURIComponent(media.object_key)}/proxy`}
        alt={media.metadata?.description || "Photo"}
        className={`max-w-full w-auto h-auto transition-opacity duration-300 ${imageLoaded ? "opacity-100" : "opacity-0"} ${
          isSwipeActive ? 'transition-none' : 'transition-transform duration-300 ease-out'
        }`}
        style={{ 
          maxHeight: "calc(100vh - 8rem)",
          transform: isSwipeActive && swipeDirection ? 
            `translateX(${swipeDirection === 'right' ? '' : '-'}${Math.min(swipeProgress * 80, 40)}px) scale(${1 - Math.min(swipeProgress * 0.02, 0.02)})` : 
            isTransitioning && swipeDirection ?
            `translateX(${swipeDirection === 'right' ? '' : '-'}60px) scale(0.98)` :
            'translateX(0) scale(1)'
        }}
        onLoad={() => setImageLoaded(true)}
      />

      {/* Loading overlay */}
      {!imageLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 min-h-[400px] min-w-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-600"></div>
        </div>
      )}

      {/* Swipe progress indicator */}
      {isSwipeActive && swipeProgress > 0.2 && swipeDirection && (
        <div className={`absolute ${swipeDirection === 'right' ? 'left-4' : 'right-4'} top-1/2 -translate-y-1/2 z-10 pointer-events-none`}>
          {(() => {
            // Check if this direction is allowed
            const canSwipe = (swipeDirection === 'right' && navigationState?.hasPrev) || 
                            (swipeDirection === 'left' && navigationState?.hasNext);
            
            if (!canSwipe) {
              // Show red X for disabled directions
              return (
                <div className="bg-red-500 text-white rounded-full p-2 animate-pulse scale-110">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
              );
            }
            
            // Show normal progress indicator for valid directions
            return (
              <>
                <div className={`rounded-full p-2 transition-all duration-100 ${
                  swipeProgress >= 1 
                    ? 'bg-green-500 text-white animate-pulse scale-110' 
                    : 'bg-black/50 text-white/70 scale-100'
                }`}>
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                      d={swipeDirection === 'right' ? "M15 19l-7-7 7-7" : "M9 5l7 7-7 7"} />
                  </svg>
                </div>
                {/* Progress arc */}
                <div className="absolute inset-0 -m-1">
                  <svg className="w-full h-full -rotate-90" viewBox="0 0 40 40">
                    <circle 
                      cx="20" cy="20" r="18" 
                      fill="none" 
                      stroke="rgba(255,255,255,0.3)" 
                      strokeWidth="2"
                    />
                    <circle 
                      cx="20" cy="20" r="18" 
                      fill="none" 
                      stroke={swipeProgress >= 1 ? "#10b981" : "rgba(255,255,255,0.8)"} 
                      strokeWidth="2"
                      strokeDasharray={`${Math.min(swipeProgress, 1) * 113} 113`}
                      className="transition-all duration-100"
                    />
                  </svg>
                </div>
              </>
            );
          })()}
        </div>
      )}

      {/* Navigation zones - only show when navigation is available */}
      {onNavigate && navigationState && (
        <>
          {/* Left navigation zone */}
          <div 
            className={`absolute left-0 top-0 bottom-0 w-1/5 cursor-pointer group ${
              navigationState.hasPrev ? 'hover:bg-black/10' : 'cursor-not-allowed opacity-50'
            }`}
            onClick={navigationState.hasPrev ? handleLeftClick : undefined}
          >
            {/* Left arrow indicator - shows on hover */}
            {navigationState.hasPrev && (
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                <div className="bg-black/70 text-white rounded-full p-2">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </div>
              </div>
            )}
          </div>

          {/* Right navigation zone */}
          <div 
            className={`absolute right-0 top-0 bottom-0 w-1/5 cursor-pointer group ${
              navigationState.hasNext ? 'hover:bg-black/10' : 'cursor-not-allowed opacity-50'
            }`}
            onClick={navigationState.hasNext ? handleRightClick : undefined}
          >
            {/* Right arrow indicator - shows on hover */}
            {navigationState.hasNext && (
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                <div className="bg-black/70 text-white rounded-full p-2">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}