import { ClimateZone } from './types';
import { getClimateZoneFromAPI } from './climateApi';

export async function getClimateZone(zipCode: string): Promise<ClimateZone | undefined> {
  try {
    const apiData = await getClimateZoneFromAPI(zipCode);
    if (apiData) {
      return apiData;
    }
  } catch (error) {
    console.warn('Climate API unavailable, using default climate zone');
  }
  
  return defaultClimateZone;
}

// Synchronous version returns default - API should be used for real data
export function getClimateZoneSync(zipCode: string): ClimateZone | undefined {
  return defaultClimateZone;
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