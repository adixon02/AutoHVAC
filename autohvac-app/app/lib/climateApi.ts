import { ClimateZone } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Get climate zone data from the backend API
 * Uses our comprehensive database with 27,789+ ZIP codes
 */
export async function getClimateZoneFromAPI(zipCode: string): Promise<ClimateZone | null> {
  try {
    const response = await fetch(`${API_URL}/api/climate/zone/${zipCode}`);
    
    if (!response.ok) {
      console.error(`Climate API error: ${response.status} ${response.statusText}`);
      return null;
    }
    
    const data = await response.json();
    
    // Convert API response to ClimateZone format
    return {
      zipCode: data.zip_code,
      zone: data.climate_zone,
      heatingDegreeDays: calculateHeatingDegreeDays(data.design_temperatures),
      coolingDegreeDays: calculateCoolingDegreeDays(data.design_temperatures),
      designTemperatures: {
        summerDry: data.design_temperatures.summer_db,
        winterDry: data.design_temperatures.winter_db,
      },
      humidity: {
        summer: data.humidity.summer,
        winter: data.humidity.winter,
      },
    };
  } catch (error) {
    console.error('Error fetching climate data:', error);
    return null;
  }
}

/**
 * Search for ZIP codes by city, state, or partial ZIP
 */
export async function searchClimateZones(query: string, limit: number = 10): Promise<any[]> {
  try {
    const response = await fetch(
      `${API_URL}/api/climate/search?query=${encodeURIComponent(query)}&limit=${limit}`
    );
    
    if (!response.ok) {
      console.error(`Climate search error: ${response.status} ${response.statusText}`);
      return [];
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error searching climate zones:', error);
    return [];
  }
}

/**
 * Get climate database statistics
 */
export async function getClimateStats(): Promise<any> {
  try {
    const response = await fetch(`${API_URL}/api/climate/stats`);
    
    if (!response.ok) {
      console.error(`Climate stats error: ${response.status} ${response.statusText}`);
      return null;
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching climate stats:', error);
    return null;
  }
}

// Helper functions to estimate degree days from design temperatures
function calculateHeatingDegreeDays(designTemps: any): number {
  // Rough estimation based on winter design temperature
  const winterDb = designTemps.winter_db || 20;
  
  if (winterDb <= -10) return 8000;
  if (winterDb <= 0) return 7000;
  if (winterDb <= 10) return 6000;
  if (winterDb <= 20) return 5000;
  if (winterDb <= 30) return 4000;
  if (winterDb <= 40) return 3000;
  return 2000;
}

function calculateCoolingDegreeDays(designTemps: any): number {
  // Rough estimation based on summer design temperature
  const summerDb = designTemps.summer_db || 90;
  
  if (summerDb >= 100) return 3000;
  if (summerDb >= 95) return 2500;
  if (summerDb >= 90) return 2000;
  if (summerDb >= 85) return 1500;
  if (summerDb >= 80) return 1000;
  return 500;
}