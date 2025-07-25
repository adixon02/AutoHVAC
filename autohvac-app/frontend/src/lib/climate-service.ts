/**
 * Frontend Climate Service
 * Calls backend API for climate data lookups
 * Following docs/02-development/api-checklist.md
 */

export interface ClimateData {
  zipCode: string;
  zone: string;
  heatingDegreeDays: number;
  coolingDegreeDays: number;
  winterDesignTemp: number;
  summerDesignTemp: number;
  humidity: number;
}

export interface ClimateServiceError {
  message: string;
  code?: string;
}

class ClimateServiceImpl {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://autohvac.onrender.com';
  }

  /**
   * Get climate data for a ZIP code
   * @param zipCode 5-digit ZIP code
   * @returns Climate data or throws error
   */
  async getClimateData(zipCode: string): Promise<ClimateData> {
    try {
      // Validate ZIP code format on frontend
      if (!zipCode || zipCode.length !== 5 || !/^\d{5}$/.test(zipCode)) {
        throw new Error('Please enter a valid 5-digit ZIP code');
      }

      const response = await fetch(`${this.baseUrl}/api/v2/climate/${zipCode}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        switch (response.status) {
          case 400:
            throw new Error('Please enter a valid 5-digit ZIP code');
          case 404:
            throw new Error(`Climate data not available for ZIP code ${zipCode}. Please try a different location.`);
          case 500:
            throw new Error('Climate service temporarily unavailable. Please try again later.');
          default:
            throw new Error(errorData.detail || 'Unable to get climate data');
        }
      }

      const data = await response.json();
      
      // Convert snake_case to camelCase for frontend
      return {
        zipCode: data.zip_code,
        zone: data.zone,
        heatingDegreeDays: data.heating_degree_days,
        coolingDegreeDays: data.cooling_degree_days,
        winterDesignTemp: data.winter_design_temp,
        summerDesignTemp: data.summer_design_temp,
        humidity: data.humidity,
      };

    } catch (error) {
      console.error(`Climate service error for ZIP ${zipCode}:`, error);
      
      if (error instanceof Error) {
        throw error;
      }
      
      throw new Error('Unable to get climate data. Please check your connection and try again.');
    }
  }

  /**
   * Validate if we support a ZIP code
   * @param zipCode 5-digit ZIP code
   * @returns true if supported, false otherwise
   */
  async validateZipCode(zipCode: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v2/climate/${zipCode}/validate`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (response.ok) {
        const result = await response.json();
        return result.data === true;
      }
      
      return false;
    } catch (error) {
      console.error(`ZIP validation error for ${zipCode}:`, error);
      return false;
    }
  }

  /**
   * Get climate zone display name
   * @param zone ASHRAE climate zone (e.g., "3A", "4A")
   * @returns Human-readable description
   */
  getClimateZoneDescription(zone: string): string {
    const descriptions: Record<string, string> = {
      '1A': 'Very Hot - Humid',
      '1B': 'Very Hot - Dry',
      '2A': 'Hot - Humid',
      '2B': 'Hot - Dry',
      '3A': 'Warm - Humid',
      '3B': 'Warm - Dry',
      '3C': 'Warm - Marine',
      '4A': 'Mixed - Humid',
      '4B': 'Mixed - Dry',
      '4C': 'Mixed - Marine',
      '5A': 'Cool - Humid',
      '5B': 'Cool - Dry',
      '5C': 'Cool - Marine',
      '6A': 'Cold - Humid',
      '6B': 'Cold - Dry',
      '7': 'Very Cold',
      '8': 'Subarctic',
    };

    return descriptions[zone] || `Climate Zone ${zone}`;
  }
}

// Export singleton instance
export const ClimateService = new ClimateServiceImpl();