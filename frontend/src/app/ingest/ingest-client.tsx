"use client";

import React, { useState } from 'react';
import { ChevronRight, Folder, Home } from 'lucide-react';
import { SidebarTrigger } from "@/components/ui/sidebar";

// Mock data structure representing your Dropbox folders
const mockFolderStructure = {
  "2024": {
    "Spring Gala": {
      "Photos": {},
      "Videos": {}
    },
    "Volunteer Fair": {
      "Setup": {},
      "Event": {},
      "Cleanup": {}
    }
  },
  "2023": {
    "Holiday Party": {
      "Decorations": {},
      "Guests": {},
      "Food": {}
    },
    "Summer Picnic": {
      "Games": {},
      "Activities": {}
    }
  },
  "Archives": {
    "2022": {
      "Annual Meeting": {}
    },
    "Historical": {}
  }
};

const IngestClient = () => {
  const [currentPath, setCurrentPath] = useState([]);
  const [selectedPrefix, setSelectedPrefix] = useState("");

  // Navigate through the folder structure based on current path
  const getCurrentFolder = () => {
    let current = mockFolderStructure;
    for (const segment of currentPath) {
      current = current[segment] || {};
    }
    return current;
  };

  // Get the subfolders in the current directory
  const getSubfolders = () => {
    const current = getCurrentFolder();
    return Object.keys(current).filter(key => 
      typeof current[key] === 'object' && current[key] !== null
    );
  };

  // Handle clicking into a subfolder
  const navigateToFolder = (folderName) => {
    setCurrentPath([...currentPath, folderName]);
  };

  // Handle clicking on a breadcrumb to navigate back
  const navigateToBreadcrumb = (index) => {
    setCurrentPath(currentPath.slice(0, index + 1));
  };

  // Go back to root
  const navigateToRoot = () => {
    setCurrentPath([]);
  };

  // Generate the object prefix from current path
  const generatePrefix = () => {
    return currentPath.join('/') + (currentPath.length > 0 ? '/' : '');
  };

  // Handle selecting this path as the batch prefix
  const selectCurrentPath = () => {
    const prefix = generatePrefix();
    setSelectedPrefix(prefix);
    // In real implementation, this would trigger the batch ingest workflow
    console.log('Selected prefix:', prefix);
  };

  const subfolders = getSubfolders();
  const currentPrefix = generatePrefix();

  return (
    <>
      <div className="bg-white border-b border-gray-200">
        <div className="px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <SidebarTrigger />
            <h1 className="text-2xl font-semibold text-gray-900">Batch Ingest</h1>
          </div>
        </div>
      </div>
      
      <div className="container mx-auto py-8">
        <div className="w-full max-w-4xl mx-auto space-y-6">
          <div className="bg-white rounded-lg shadow-sm p-6 space-y-4">
            <h2 className="text-2xl font-semibold">Select Batch Ingest Folder</h2>
            
            {/* Breadcrumb Navigation */}
            <div className="flex items-center space-x-2 p-3 bg-gray-50 rounded-lg">
              <button 
                onClick={navigateToRoot}
                className="flex items-center text-jl-red hover:text-jl-red-700 transition-colors"
              >
                <Home className="w-4 h-4 mr-1" />
                Root
              </button>
              
              {currentPath.map((segment, index) => (
                <React.Fragment key={index}>
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                  <button
                    onClick={() => navigateToBreadcrumb(index)}
                    className="text-jl-red hover:text-jl-red-700 transition-colors"
                  >
                    {segment}
                  </button>
                </React.Fragment>
              ))}
            </div>

            {/* Current Path Display */}
            <div className="p-3 bg-jl-red-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">Current Object Prefix:</div>
              <div className="font-mono text-lg">
                {currentPrefix || '<root>'}
              </div>
            </div>
          </div>

          {/* Folder Table */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-4 font-medium text-gray-700">
                    Folder Name
                  </th>
                  <th className="text-left p-4 font-medium text-gray-700">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {subfolders.length === 0 ? (
                  <tr>
                    <td colSpan={2} className="p-8 text-center text-gray-500">
                      No subfolders in this directory
                    </td>
                  </tr>
                ) : (
                  subfolders.map((folder) => (
                    <tr key={folder} className="border-t hover:bg-gray-50 transition-colors">
                      <td className="p-4">
                        <div className="flex items-center">
                          <Folder className="w-5 h-5 text-jl-red mr-3" />
                          <span className="font-medium">{folder}</span>
                        </div>
                      </td>
                      <td className="p-4">
                        <button
                          onClick={() => navigateToFolder(folder)}
                          className="text-jl-red hover:text-jl-red-700 transition-colors font-medium"
                        >
                          Enter →
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Action Buttons */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex justify-between items-center">
              <button
                onClick={() => setCurrentPath(currentPath.slice(0, -1))}
                disabled={currentPath.length === 0}
                className="px-4 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ← Go Back
              </button>
              
              <button
                onClick={selectCurrentPath}
                className="px-6 py-2 bg-jl-red text-white rounded-lg hover:bg-jl-red-700 transition-colors font-medium"
              >
                Use This Path for Batch Ingest
              </button>
            </div>
          </div>

          {/* Selected Prefix Display */}
          {selectedPrefix && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="text-sm text-green-700 mb-1">Selected for batch ingest:</div>
              <div className="font-mono text-lg text-green-800">{selectedPrefix}</div>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default IngestClient;