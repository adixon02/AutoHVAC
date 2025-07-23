'use client';

import { useState, useCallback } from 'react';
import { ProjectInfo, BuildingInfo, Room, LoadCalculation, SystemRecommendation } from '../lib/types';
import { getClimateZone, getClimateZoneSync, defaultClimateZone } from '../lib/climateData';
import { calculateTotalLoad } from '../lib/manualJ';
import { generateSystemRecommendations } from '../lib/systemRecommendations';

interface UseCalculationsReturn {
  // State
  loadCalculation: LoadCalculation | null;
  recommendations: SystemRecommendation[];
  isCalculating: boolean;
  calculationError: string | null;
  
  // Actions
  performCalculations: (
    rooms: Room[], 
    buildingInfo: BuildingInfo, 
    projectInfo: ProjectInfo
  ) => Promise<void>;
  clearCalculations: () => void;
  
  // Computed
  hasResults: boolean;
}

export function useCalculations(): UseCalculationsReturn {
  const [loadCalculation, setLoadCalculation] = useState<LoadCalculation | null>(null);
  const [recommendations, setRecommendations] = useState<SystemRecommendation[]>([]);
  const [isCalculating, setIsCalculating] = useState(false);
  const [calculationError, setCalculationError] = useState<string | null>(null);

  const performCalculations = useCallback(async (
    rooms: Room[], 
    buildingInfo: BuildingInfo, 
    projectInfo: ProjectInfo
  ) => {
    if (!rooms.length || !buildingInfo || !projectInfo) {
      setCalculationError('Missing required data for calculations');
      return;
    }

    setIsCalculating(true);
    setCalculationError(null);

    try {
      // Try to get climate data from API, fallback to sync version
      let climate = await getClimateZone(projectInfo.zipCode);
      if (!climate) {
        climate = getClimateZoneSync(projectInfo.zipCode) || defaultClimateZone;
      }
      
      // Perform load calculations
      const loadCalc = calculateTotalLoad(rooms, buildingInfo, climate);
      setLoadCalculation(loadCalc);
      
      // Generate system recommendations
      const systemRecs = generateSystemRecommendations(loadCalc, buildingInfo);
      setRecommendations(systemRecs);
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Calculation failed';
      setCalculationError(errorMessage);
      console.error('Calculation error:', error);
    } finally {
      setIsCalculating(false);
    }
  }, []);

  const clearCalculations = useCallback(() => {
    setLoadCalculation(null);
    setRecommendations([]);
    setCalculationError(null);
    setIsCalculating(false);
  }, []);

  const hasResults = loadCalculation !== null && recommendations.length > 0;

  return {
    // State
    loadCalculation,
    recommendations,
    isCalculating,
    calculationError,
    
    // Actions
    performCalculations,
    clearCalculations,
    
    // Computed
    hasResults,
  };
}