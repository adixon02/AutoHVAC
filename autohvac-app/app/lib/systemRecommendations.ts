import { LoadCalculation, SystemRecommendation, BuildingInfo } from './types';
import { btuToTons } from './manualJ';

export function generateSystemRecommendations(
  loadCalc: LoadCalculation,
  building: BuildingInfo
): SystemRecommendation[] {
  const coolingTons = btuToTons(loadCalc.totalCoolingLoad);
  const heatingBtu = loadCalc.totalHeatingLoad;

  const recommendations: SystemRecommendation[] = [];

  // Economy Tier - Basic split system
  if (building.squareFootage < 3000) {
    recommendations.push({
      systemType: 'split',
      coolingCapacity: Math.ceil(coolingTons) * 12000,
      heatingCapacity: Math.ceil(heatingBtu / 10000) * 10000,
      efficiency: {
        seer: 14,
        hspf: 8.2
      },
      tier: 'economy',
      estimatedCost: {
        equipment: Math.round(coolingTons * 1200),
        installation: Math.round(coolingTons * 800),
        total: Math.round(coolingTons * 2000)
      }
    });
  }

  // Standard Tier - Higher efficiency split or mini-split
  const standardSeer = building.squareFootage > 2500 ? 16 : 18;
  recommendations.push({
    systemType: building.squareFootage > 2500 ? 'split' : 'minisplit',
    coolingCapacity: Math.ceil(coolingTons) * 12000,
    heatingCapacity: Math.ceil(heatingBtu / 10000) * 10000,
    efficiency: {
      seer: standardSeer,
      hspf: 9.0
    },
    tier: 'standard',
    estimatedCost: {
      equipment: Math.round(coolingTons * 1800),
      installation: Math.round(coolingTons * 1000),
      total: Math.round(coolingTons * 2800)
    }
  });

  // Premium Tier - High efficiency with zoning
  const premiumType = coolingTons > 3 ? 'split' : 'minisplit';
  recommendations.push({
    systemType: premiumType,
    coolingCapacity: Math.ceil(coolingTons) * 12000,
    heatingCapacity: Math.ceil(heatingBtu / 10000) * 10000,
    efficiency: {
      seer: premiumType === 'minisplit' ? 22 : 20,
      hspf: 10.0
    },
    tier: 'premium',
    estimatedCost: {
      equipment: Math.round(coolingTons * 2500),
      installation: Math.round(coolingTons * 1500),
      total: Math.round(coolingTons * 4000)
    }
  });

  // Add geothermal option for larger homes
  if (building.squareFootage > 3000) {
    recommendations.push({
      systemType: 'geothermal',
      coolingCapacity: Math.ceil(coolingTons) * 12000,
      heatingCapacity: Math.ceil(heatingBtu / 10000) * 10000,
      efficiency: {
        seer: 30, // EER equivalent
        hspf: 4.0 // COP equivalent
      },
      tier: 'premium',
      estimatedCost: {
        equipment: Math.round(coolingTons * 3500),
        installation: Math.round(coolingTons * 4500),
        total: Math.round(coolingTons * 8000)
      }
    });
  }

  return recommendations;
}

export function getSystemTypeDescription(type: SystemRecommendation['systemType']): string {
  const descriptions = {
    split: 'Traditional central air system with outdoor condenser and indoor air handler',
    packaged: 'All-in-one outdoor unit, ideal for homes with limited indoor space',
    minisplit: 'Ductless system with individual room control and high efficiency',
    geothermal: 'Ground-source heat pump using earth\'s stable temperature'
  };
  return descriptions[type];
}

export function formatEfficiency(seer: number, hspf: number): string {
  return `${seer} SEER / ${hspf} HSPF`;
}