export interface ProjectInfo {
  zipCode: string;
  projectName: string;
  projectType: 'residential' | 'commercial';
  constructionType: 'new' | 'retrofit';
  inputMethod?: 'manual' | 'blueprint';
}

export interface BuildingInfo {
  squareFootage: number;
  stories: number;
  ceilingHeight: number;
  foundationType: 'slab' | 'crawlspace' | 'basement';
  insulationQuality: 'poor' | 'average' | 'good' | 'excellent';
  windowType: 'single' | 'double' | 'triple';
  windowArea: number;
  orientation: 'north' | 'south' | 'east' | 'west';
}

export interface Room {
  id: string;
  name: string;
  area: number;
  ceilingHeight: number;
  windowArea: number;
  exteriorWalls: number;
  occupancy: number;
}

export interface LoadCalculation {
  totalCoolingLoad: number;
  totalHeatingLoad: number;
  roomLoads: {
    roomId: string;
    coolingLoad: number;
    heatingLoad: number;
  }[];
  sensibleCooling: number;
  latentCooling: number;
}

export interface SystemRecommendation {
  systemType: 'split' | 'packaged' | 'minisplit' | 'geothermal';
  coolingCapacity: number;
  heatingCapacity: number;
  efficiency: {
    seer: number;
    hspf: number;
  };
  tier: 'economy' | 'standard' | 'premium' | 'ultra-premium';
  estimatedCost: {
    equipment: number;
    installation: number;
    total: number;
  };
}

export interface ClimateZone {
  zipCode: string;
  zone: string;
  heatingDegreeDays: number;
  coolingDegreeDays: number;
  designTemperatures: {
    summerDry: number;
    winterDry: number;
  };
  humidity: {
    summer: number;
    winter: number;
  };
}