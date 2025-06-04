'use client';

import React from 'react';
import LibraryView from '@/components/LibraryView';

export default function LibraryViewTestPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto py-8 px-4">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">LibraryView Component Test</h1>
        <p className="text-gray-600 mb-8">
          Test the LibraryView component with different initial paths. Try navigating folders, clicking photos, and using cmd/ctrl+click.
        </p>
        
        <div className="space-y-8">
          {/* Root Library View */}
          <section className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Root Library View</h2>
            <p className="text-sm text-gray-600 mb-4">Initial path: &quot;&quot; (empty string for root)</p>
            <LibraryView 
              initialPath="" 
              className="border-t pt-4"
            />
          </section>
          
          {/* Nested Path Example */}
          <section className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Nested Path Example</h2>
            <p className="text-sm text-gray-600 mb-4">Initial path: &quot;2024-2025 League Year&quot;</p>
            <LibraryView 
              initialPath="2024-2025 League Year" 
              className="border-t pt-4"
            />
          </section>
        </div>
        
        <div className="mt-12 p-6 bg-blue-50 rounded-lg">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Testing Instructions</h3>
          <ul className="list-disc list-inside space-y-1 text-gray-700">
            <li>Click on folders to navigate into them</li>
            <li>Click on photos to open them in a modal</li>
            <li>Use Cmd/Ctrl + Click on photos to open in a new tab</li>
            <li>Click breadcrumbs to navigate back</li>
            <li>Try the home icon to return to root</li>
            <li>Check loading states by refreshing the page</li>
            <li>Test error handling by disabling network (if backend is down)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}