import { ClimateZone } from './types';
import { getClimateZoneFromAPI } from './climateApi';

// Sample climate zones for major US cities - MVP fallback data
export const climateZones: ClimateZone[] = [
  // Hot-Humid
  {
    zipCode: '33101',
    zone: '1A',
    heatingDegreeDays: 150,
    coolingDegreeDays: 4500,
    designTemperatures: { summerDry: 91, winterDry: 47 },
    humidity: { summer: 75, winter: 65 }
  },
  {
    zipCode: '77001',
    zone: '2A',
    heatingDegreeDays: 1400,
    coolingDegreeDays: 3000,
    designTemperatures: { summerDry: 95, winterDry: 32 },
    humidity: { summer: 75, winter: 65 }
  },
  // Hot-Dry
  {
    zipCode: '85001',
    zone: '2B',
    heatingDegreeDays: 1100,
    coolingDegreeDays: 3900,
    designTemperatures: { summerDry: 108, winterDry: 37 },
    humidity: { summer: 35, winter: 45 }
  },
  {
    zipCode: '89101',
    zone: '3B',
    heatingDegreeDays: 2200,
    coolingDegreeDays: 3200,
    designTemperatures: { summerDry: 106, winterDry: 31 },
    humidity: { summer: 20, winter: 35 }
  },
  // Mixed-Humid
  {
    zipCode: '30301',
    zone: '3A',
    heatingDegreeDays: 3000,
    coolingDegreeDays: 1800,
    designTemperatures: { summerDry: 92, winterDry: 25 },
    humidity: { summer: 70, winter: 60 }
  },
  {
    zipCode: '37201',
    zone: '4A',
    heatingDegreeDays: 3700,
    coolingDegreeDays: 1400,
    designTemperatures: { summerDry: 93, winterDry: 18 },
    humidity: { summer: 70, winter: 60 }
  },
  // Cold
  {
    zipCode: '10001',
    zone: '4A',
    heatingDegreeDays: 4900,
    coolingDegreeDays: 1100,
    designTemperatures: { summerDry: 88, winterDry: 15 },
    humidity: { summer: 65, winter: 60 }
  },
  {
    zipCode: '60601',
    zone: '5A',
    heatingDegreeDays: 6500,
    coolingDegreeDays: 900,
    designTemperatures: { summerDry: 89, winterDry: 2 },
    humidity: { summer: 65, winter: 65 }
  },
  {
    zipCode: '80201',
    zone: '5B',
    heatingDegreeDays: 6100,
    coolingDegreeDays: 700,
    designTemperatures: { summerDry: 91, winterDry: 2 },
    humidity: { summer: 35, winter: 45 }
  },
  // Marine - Pacific Northwest
  {
    zipCode: '98101',
    zone: '4C',
    heatingDegreeDays: 4800,
    coolingDegreeDays: 200,
    designTemperatures: { summerDry: 83, winterDry: 28 },
    humidity: { summer: 55, winter: 75 }
  },
  {
    zipCode: '98188',
    zone: '5B',
    heatingDegreeDays: 5200,
    coolingDegreeDays: 300,
    designTemperatures: { summerDry: 85, winterDry: 25 },
    humidity: { summer: 60, winter: 80 }
  },
  {
    zipCode: '94102',
    zone: '3C',
    heatingDegreeDays: 3000,
    coolingDegreeDays: 100,
    designTemperatures: { summerDry: 80, winterDry: 38 },
    humidity: { summer: 60, winter: 70 }
  },
  // Very Cold
  {
    zipCode: '55401',
    zone: '6A',
    heatingDegreeDays: 7900,
    coolingDegreeDays: 700,
    designTemperatures: { summerDry: 88, winterDry: -9 },
    humidity: { summer: 65, winter: 70 }
  }
];

export async function getClimateZone(zipCode: string): Promise<ClimateZone | undefined> {
  // First, try to get data from our comprehensive API
  try {
    const apiData = await getClimateZoneFromAPI(zipCode);
    if (apiData) {
      return apiData;
    }
  } catch (error) {
    console.warn('Climate API unavailable, falling back to local data');
  }
  
  // Fallback to local data - check first 3 digits of ZIP
  const zip3 = zipCode.substring(0, 3);
  return climateZones.find(zone => zone.zipCode.startsWith(zip3));
}

// Synchronous version for immediate UI feedback (uses only local data)
export function getClimateZoneSync(zipCode: string): ClimateZone | undefined {
  const zip3 = zipCode.substring(0, 3);
  return climateZones.find(zone => zone.zipCode.startsWith(zip3));
}

// Default climate zone for unknown ZIPs (Zone 4A - moderate)
export const defaultClimateZone: ClimateZone = {
  zipCode: '00000',
  zone: '4A',
  heatingDegreeDays: 4000,
  coolingDegreeDays: 1200,
  designTemperatures: { summerDry: 90, winterDry: 20 },
  humidity: { summer: 65, winter: 60 }
};