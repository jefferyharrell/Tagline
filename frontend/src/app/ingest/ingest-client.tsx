"use client";

import React, { useState } from 'react';
import { Folder, Home } from 'lucide-react';
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
          {/* Breadcrumb Navigation */}
          <Breadcrumb className="p-3 bg-gray-50 rounded-lg">
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink
                  asChild
                  className="flex items-center text-jl-red hover:text-jl-red-700 cursor-pointer"
                >
                  <button onClick={navigateToRoot}>
                    <Home className="w-4 h-4 mr-1" />
                    Root
                  </button>
                </BreadcrumbLink>
              </BreadcrumbItem>
              
              {currentPath.map((segment, index) => (
                <React.Fragment key={index}>
                  <BreadcrumbSeparator />
                  <BreadcrumbItem>
                    {index === currentPath.length - 1 ? (
                      <BreadcrumbPage className="text-gray-900">
                        {segment}
                      </BreadcrumbPage>
                    ) : (
                      <BreadcrumbLink
                        asChild
                        className="text-jl-red hover:text-jl-red-700 cursor-pointer"
                      >
                        <button onClick={() => navigateToBreadcrumb(index)}>
                          {segment}
                        </button>
                      </BreadcrumbLink>
                    )}
                  </BreadcrumbItem>
                </React.Fragment>
              ))}
            </BreadcrumbList>
          </Breadcrumb>

          {/* Folder Table */}
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-gray-50 hover:bg-gray-50">
                  <TableHead className="text-gray-700">Folder Name</TableHead>
                  <TableHead className="text-gray-700">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subfolders.length === 0 ? (
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={2} className="p-8 text-center text-gray-500">
                      No subfolders in this directory
                    </TableCell>
                  </TableRow>
                ) : (
                  subfolders.map((folder) => (
                    <TableRow key={folder}>
                      <TableCell className="p-4">
                        <div className="flex items-center">
                          <Folder className="w-5 h-5 text-jl-red mr-3" />
                          <span className="font-medium">{folder}</span>
                        </div>
                      </TableCell>
                      <TableCell className="p-4">
                        <button
                          onClick={() => navigateToFolder(folder)}
                          className="text-jl-red hover:text-jl-red-700 transition-colors font-medium"
                        >
                          Enter →
                        </button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Action Buttons */}
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

          {/* Object Prefix Display */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="p-4 bg-jl-red-50 rounded-lg">
              <div className="flex items-baseline gap-2">
                <span className="text-sm font-medium text-gray-700">Object Prefix:</span>
                <span className="font-mono text-lg text-gray-900">
                  {currentPrefix || '<root>'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default IngestClient;