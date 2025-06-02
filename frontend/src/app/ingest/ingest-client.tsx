"use client";

import React, { useState } from "react";
import { Folder, Home } from "lucide-react";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

// Mock data structure representing your Dropbox folders
const mockFolderStructure = {
  "2024": {
    "Spring Gala": {
      Photos: {
        Arrivals: {},
        "Cocktail Hour": {},
        Dinner: {},
        Speeches: {},
        Dancing: {},
        "Group Photos": {},
        Candids: {},
        "Venue Shots": {},
        Decorations: {},
        "Behind the Scenes": {},
      },
      Videos: {
        "Highlights Reel": {},
        "Full Speeches": {},
        "Dance Floor": {},
        Interviews: {},
        "B-Roll": {},
      },
    },
    "Volunteer Fair": {
      Setup: {},
      Event: {},
      Cleanup: {},
    },
    "Annual Fundraiser": {},
    "Board Meetings": {
      January: {},
      February: {},
      March: {},
      April: {},
      May: {},
      June: {},
      July: {},
      August: {},
      September: {},
      October: {},
      November: {},
      December: {},
    },
    "Community Outreach": {
      "School Visits": {},
      "Hospital Programs": {},
      "Food Bank": {},
      "Literacy Initiative": {},
      "Senior Center": {},
    },
    "Member Events": {
      "New Member Orientation": {},
      "Monthly Mixers": {},
      "Leadership Training": {},
      Workshops: {},
    },
    "Marketing Materials": {},
    "Press Coverage": {},
    "Social Media Content": {},
  },
  "2023": {
    "Holiday Party": {
      Decorations: {},
      Guests: {},
      Food: {},
    },
    "Summer Picnic": {
      Games: {},
      Activities: {},
    },
    "Fall Fashion Show": {},
    "Winter Ball": {},
    "Spring Luncheon": {},
    "Charity Auction": {},
    "Golf Tournament": {},
    "5K Run": {},
    "Book Club Events": {},
    "Wine Tasting": {},
    "Art Exhibition": {},
    "Cooking Classes": {},
    "Mentorship Program": {},
    "Professional Development": {},
    "Volunteer Recognition": {},
  },
  "2022": {
    "Annual Meeting": {},
    Gala: {},
    "Community Service": {},
    "Educational Programs": {},
    "Fundraising Events": {},
    "Member Activities": {},
    "Board Documentation": {},
    "Financial Records": {},
    "Newsletter Archives": {},
    "Partnership Events": {},
  },
  "2021": {
    "Virtual Events": {},
    "Hybrid Meetings": {},
    "Online Fundraisers": {},
    "Digital Workshops": {},
    "Zoom Socials": {},
  },
  "2020": {
    "Pre-Pandemic Events": {},
    "Transition Period": {},
    "Virtual Pivot": {},
    "Year End Review": {},
  },
  Archives: {
    "2019": {},
    "2018": {},
    "2017": {},
    "2016": {},
    "2015": {},
    "2014": {},
    "2013": {},
    "2012": {},
    "2011": {},
    "2010": {},
    Historical: {
      "Founding Documents": {},
      "Legacy Photos": {},
      "Milestone Events": {},
      "Anniversary Celebrations": {},
      "Leadership History": {},
    },
  },
  Administrative: {
    "Bylaws and Policies": {},
    "Meeting Minutes": {},
    "Financial Documents": {},
    "Legal Records": {},
    Insurance: {},
    Contracts: {},
    "Vendor Information": {},
    "Member Database Exports": {},
  },
  "Special Projects": {
    "Capital Campaign": {},
    "Building Renovation": {},
    "Scholarship Program": {},
    "Endowment Fund": {},
    "Strategic Planning": {},
  },
};

const IngestClient = () => {
  const [currentPath, setCurrentPath] = useState([]);

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
    return Object.keys(current).filter(
      (key) => typeof current[key] === "object" && current[key] !== null,
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
    return currentPath.join("/") + (currentPath.length > 0 ? "/" : "");
  };

  // Handle selecting this path as the batch prefix
  const selectCurrentPath = () => {
    const prefix = generatePrefix();
    setSelectedPrefix(prefix);
    // In real implementation, this would trigger the batch ingest workflow
    console.log("Selected prefix:", prefix);
  };

  const subfolders = getSubfolders();
  const currentPrefix = generatePrefix();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200">
        <div className="px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <SidebarTrigger />
            <h1 className="text-2xl font-semibold text-gray-900">
              Batch Ingest
            </h1>
          </div>
        </div>
      </div>

      <div className="container mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          {/* Breadcrumb Navigation */}
          <div className="px-6 py-4 border-b border-gray-200">
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbLink
                    asChild
                    className="flex items-center text-jl-red hover:text-jl-red-700 cursor-pointer"
                  >
                    <button onClick={navigateToRoot}>
                      <Home className="w-4 h-4 mr-1" />
                      Home
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
          </div>

          {/* Folder Table */}
          <div className="divide-y divide-gray-200 border-t border-gray-200">
            {subfolders.length === 0 ? (
              <div className="px-6 py-8 text-center text-gray-500">
                No subfolders in this directory
              </div>
            ) : (
              subfolders.slice(0, 8).map((folder) => (
                <button
                  key={folder}
                  onClick={() => navigateToFolder(folder)}
                  className="w-full flex items-center px-6 py-3 hover:bg-gray-50 transition-colors text-left"
                >
                  <Folder className="w-5 h-5 text-jl-red mr-3" />
                  <span className="text-sm">{folder}</span>
                </button>
              ))
            )}
          </div>

          {/* Action Buttons and Object Prefix */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setCurrentPath(currentPath.slice(0, -1))}
                disabled={currentPath.length === 0}
                className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ← Go Back
              </button>

              <button
                onClick={selectCurrentPath}
                className="px-4 py-2 bg-jl-red text-white text-sm rounded-md hover:bg-jl-red-700 transition-colors"
              >
                Use This Path for Batch Ingest
              </button>
            </div>

            {/* Object Prefix Display */}
            <div className="mt-4 p-3 bg-jl-red-50 rounded-md">
              <div className="flex items-baseline gap-2">
                <span className="text-sm text-gray-600">Object Prefix:</span>
                <span className="font-mono text-sm font-medium text-gray-900">
                  {currentPrefix || "<root>"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default IngestClient;
