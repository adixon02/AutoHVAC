/**
 * AutoHVAC V2 - Shared Type Definitions
 * Single source of truth following docs/02-development/data-dictionary.md
 */

// Core Data Models

export interface ProjectInfo {
  id: string;
  projectName: string;
  zipCode: string;
  buildingType: "residential" | "commercial";
  constructionType: "new" | "retrofit";
  inputMethod: "manual" | "blueprint";
  createdAt: Date;
  updatedAt: Date;
}

export interface BuildingCharacteristics {
  totalSquareFootage: number;
  foundationType: "slab" | "crawlspace" | "basement" | "pier";
  wallInsulation: "poor" | "average" | "good" | "excellent";
  ceilingInsulation: "poor" | "average" | "good" | "excellent";
  windowType: "single" | "double" | "triple" | "low-E";
  buildingOrientation: "north" | "south" | "east" | "west";
  stories: number;
  buildingAge: "new" | "recent" | "older" | "historic";
}

export interface Room {
  id: string;
  name: string;
  area: number;
  ceilingHeight: number;
  exteriorWalls: number;
  windowArea: number;
  occupants: number;
  equipmentLoad: number;
  roomType: "bedroom" | "bathroom" | "kitchen" | "living" | "dining" | "office" | "other";
}

export interface ClimateData {
  zipCode: string;
  zone: string;
  heatingDegreeDays: number;
  coolingDegreeDays: number;
  winterDesignTemp: number;
  summerDesignTemp: number;
  humidity: number;
}

export interface LoadCalculation {
  projectId: string;
  totalCoolingLoad: number;
  totalHeatingLoad: number;
  coolingTons: number;
  heatingTons: number;
  roomLoads: Array<{
    roomId: string;
    coolingLoad: number;
    heatingLoad: number;
  }>;
  calculatedAt: Date;
}

export interface SystemRecommendation {
  tier: "economy" | "standard" | "premium";
  coolingSystem: {
    type: string;
    size: number;
    seer: number;
    brand: string;
    model: string;
    estimatedCost: number;
  };
  heatingSystem: {
    type: string;
    size: number;
    efficiency: number;
    brand: string;
    model: string;
    estimatedCost: number;
  };
}

// Validation Schema Types (for runtime validation)
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface CalculationRequest {
  project: ProjectInfo;
  building: BuildingCharacteristics;
  rooms: Room[];
}

export interface CalculationResponse {
  loadCalculation: LoadCalculation;
  recommendations: SystemRecommendation[];
}