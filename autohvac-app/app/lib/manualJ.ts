import { BuildingInfo, Room, LoadCalculation, ClimateZone } from './types';

// Manual J calculation constants
const INFILTRATION_RATES = {
  poor: 1.0,
  average: 0.5,
  good: 0.35,
  excellent: 0.2
};

const WINDOW_U_VALUES = {
  single: 1.04,
  double: 0.48,
  triple: 0.25
};

const WALL_R_VALUES = {
  poor: 7,
  average: 13,
  good: 19,
  excellent: 30
};

const CEILING_R_VALUES = {
  poor: 19,
  average: 30,
  good: 38,
  excellent: 49
};

export function calculateLoadForRoom(
  room: Room,
  building: BuildingInfo,
  climate: ClimateZone
): { coolingLoad: number; heatingLoad: number } {
  // Temperature differences
  const summerTempDiff = climate.designTemperatures.summerDry - 75; // Indoor setpoint 75°F
  const winterTempDiff = 70 - climate.designTemperatures.winterDry; // Indoor setpoint 70°F

  // Wall heat transfer
  const wallArea = room.exteriorWalls * room.ceilingHeight * 10; // Assume 10ft wall sections
  const wallRValue = WALL_R_VALUES[building.insulationQuality];
  const wallCoolingLoad = (wallArea * summerTempDiff) / wallRValue;
  const wallHeatingLoad = (wallArea * winterTempDiff) / wallRValue;

  // Ceiling heat transfer
  const ceilingArea = room.area;
  const ceilingRValue = CEILING_R_VALUES[building.insulationQuality];
  const ceilingCoolingLoad = (ceilingArea * summerTempDiff * 1.2) / ceilingRValue; // 1.2 factor for roof
  const ceilingHeatingLoad = (ceilingArea * winterTempDiff) / ceilingRValue;

  // Window heat transfer
  const windowUValue = WINDOW_U_VALUES[building.windowType];
  const windowCoolingLoad = room.windowArea * windowUValue * summerTempDiff;
  const windowHeatingLoad = room.windowArea * windowUValue * winterTempDiff;

  // Solar gain (simplified)
  const solarGain = room.windowArea * 40; // 40 BTU/hr per sq ft average

  // Internal gains (people, equipment)
  const internalGains = room.occupancy * 230 + room.area * 1.5; // People + equipment

  // Infiltration
  const roomVolume = room.area * room.ceilingHeight;
  const infiltrationRate = INFILTRATION_RATES[building.insulationQuality];
  const infiltrationCooling = roomVolume * infiltrationRate * 1.08 * summerTempDiff;
  const infiltrationHeating = roomVolume * infiltrationRate * 1.08 * winterTempDiff;

  // Latent cooling load (humidity)
  const latentLoad = room.occupancy * 200 + infiltrationCooling * 0.3;

  // Total loads
  const coolingLoad = 
    wallCoolingLoad + 
    ceilingCoolingLoad + 
    windowCoolingLoad + 
    solarGain + 
    internalGains + 
    infiltrationCooling + 
    latentLoad;

  const heatingLoad = 
    wallHeatingLoad + 
    ceilingHeatingLoad + 
    windowHeatingLoad + 
    infiltrationHeating;

  return {
    coolingLoad: Math.round(coolingLoad),
    heatingLoad: Math.round(heatingLoad)
  };
}

export function calculateTotalLoad(
  rooms: Room[],
  building: BuildingInfo,
  climate: ClimateZone
): LoadCalculation {
  const roomLoads = rooms.map(room => {
    const loads = calculateLoadForRoom(room, building, climate);
    return {
      roomId: room.id,
      coolingLoad: loads.coolingLoad,
      heatingLoad: loads.heatingLoad
    };
  });

  const totalCoolingLoad = roomLoads.reduce((sum, room) => sum + room.coolingLoad, 0);
  const totalHeatingLoad = roomLoads.reduce((sum, room) => sum + room.heatingLoad, 0);

  // Apply diversity factor (not all rooms peak at same time)
  const adjustedCoolingLoad = Math.round(totalCoolingLoad * 0.85);
  const adjustedHeatingLoad = Math.round(totalHeatingLoad * 0.9);

  // Sensible vs latent split (typical residential)
  const sensibleCooling = Math.round(adjustedCoolingLoad * 0.75);
  const latentCooling = adjustedCoolingLoad - sensibleCooling;

  return {
    totalCoolingLoad: adjustedCoolingLoad,
    totalHeatingLoad: adjustedHeatingLoad,
    roomLoads,
    sensibleCooling,
    latentCooling
  };
}

// Helper function to convert BTU/hr to tons
export function btuToTons(btu: number): number {
  return Math.round((btu / 12000) * 10) / 10;
}