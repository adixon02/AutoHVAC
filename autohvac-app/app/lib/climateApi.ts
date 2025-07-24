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
      zone: data.zone,
      heatingDegreeDays: data.heating_degree_days,
      coolingDegreeDays: data.cooling_degree_days,
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

