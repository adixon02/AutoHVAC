import { Room, LoadCalculation, ClimateZone } from './types';

// HVAC System Types
export interface HVACUnit {
  id: string;
  type: 'ducted' | 'ductless';
  location: { x: number; y: number; floor: string };
  capacity: { cooling: number; heating: number }; // BTU/hr
  efficiency: { seer: number; hspf: number };
  zones: string[]; // room IDs served
}

export interface DuctedSystem extends HVACUnit {
  type: 'ducted';
  equipmentType: 'furnace' | 'air_handler' | 'packaged_unit';
  mainTrunk: DuctSegment;
  branches: DuctSegment[];
  returns: ReturnDuct[];
}

export interface DuctlessSystem extends HVACUnit {
  type: 'ductless';
  outdoorUnit: { location: { x: number; y: number }; capacity: number };
  indoorUnits: IndoorUnit[];
  linesets: LineSet[];
}

export interface DuctSegment {
  id: string;
  startPoint: { x: number; y: number };
  endPoint: { x: number; y: number };
  size: { width: number; height: number } | { diameter: number };
  cfm: number;
  room?: string;
}

export interface ReturnDuct {
  id: string;
  location: { x: number; y: number };
  size: { width: number; height: number };
  cfm: number;
  room: string;
}

export interface IndoorUnit {
  id: string;
  type: 'wall_mount' | 'ceiling_cassette' | 'ducted_slim' | 'floor_console';
  location: { x: number; y: number; wall?: string };
  capacity: number; // BTU/hr
  room: string;
  cfm?: number; // for ducted slim units
}

export interface LineSet {
  id: string;
  path: { x: number; y: number }[];
  liquidLine: number; // diameter in inches
  suctionLine: number; // diameter in inches
  indoorUnit: string;
}

export interface HVACLayout {
  totalCoolingLoad: number;
  totalHeatingLoad: number;
  systems: (DuctedSystem | DuctlessSystem)[];
  designNotes: string[];
  estimatedCost: {
    equipment: number;
    installation: number;
    total: number;
  };
}

// HVAC Layout Generator
export class HVACLayoutGenerator {
  private rooms: Room[];
  private loadCalculation: LoadCalculation;
  private climate: ClimateZone;

  constructor(rooms: Room[], loadCalculation: LoadCalculation, climate: ClimateZone) {
    this.rooms = rooms;
    this.loadCalculation = loadCalculation;
    this.climate = climate;
  }

  generateLayout(): HVACLayout {
    // Determine optimal system type(s) based on load and building characteristics
    const systemRecommendation = this.determineSystemType();
    
    let systems: (DuctedSystem | DuctlessSystem)[] = [];
    let designNotes: string[] = [];
    
    if (systemRecommendation.primary === 'ducted') {
      const ductedSystem = this.designDuctedSystem();
      systems.push(ductedSystem);
      designNotes.push('Ducted system recommended for efficient whole-house conditioning');
    } else if (systemRecommendation.primary === 'ductless') {
      const ductlessSystem = this.designDuctlessSystem();
      systems.push(ductlessSystem);
      designNotes.push('Ductless system recommended for zone control and efficiency');
    } else {
      // Mixed system - ducted for main areas, ductless for specific zones
      const ductedSystem = this.designDuctedSystem(systemRecommendation.ductedZones);
      const ductlessSystem = this.designDuctlessSystem(systemRecommendation.ductlessZones);
      systems.push(ductedSystem, ductlessSystem);
      designNotes.push('Mixed system: ducted for main areas, ductless for specific zones');
    }

    return {
      totalCoolingLoad: this.loadCalculation.totalCoolingLoad,
      totalHeatingLoad: this.loadCalculation.totalHeatingLoad,
      systems,
      designNotes: [...designNotes, ...this.generateDesignNotes()],
      estimatedCost: this.calculateCosts(systems)
    };
  }

  private determineSystemType(): { 
    primary: 'ducted' | 'ductless' | 'mixed';
    ductedZones?: string[];
    ductlessZones?: string[];
  } {
    const totalLoad = this.loadCalculation.totalCoolingLoad;
    const roomCount = this.rooms.length;
    const hasBasement = this.rooms.some(r => r.name.toLowerCase().includes('basement'));
    const hasGarage = this.rooms.some(r => r.name.toLowerCase().includes('garage'));

    // Decision logic for system type
    if (totalLoad > 48000 && roomCount > 6) {
      // Large house - likely needs ducted system
      return { primary: 'ducted' };
    } else if (totalLoad < 24000 && roomCount <= 4) {
      // Small house - ductless might be ideal
      return { primary: 'ductless' };
    } else if (hasBasement || hasGarage) {
      // Mixed system - ducted for main, ductless for specific zones
      const mainRooms = this.rooms.filter(r => 
        !r.name.toLowerCase().includes('basement') && 
        !r.name.toLowerCase().includes('garage')
      );
      const separateZones = this.rooms.filter(r => 
        r.name.toLowerCase().includes('basement') || 
        r.name.toLowerCase().includes('garage')
      );
      
      if (separateZones.length > 0) {
        return {
          primary: 'mixed',
          ductedZones: mainRooms.map(r => r.id),
          ductlessZones: separateZones.map(r => r.id)
        };
      }
    }

    // Default to ducted for new construction
    return { primary: 'ducted' };
  }

  private designDuctedSystem(limitToRooms?: string[]): DuctedSystem {
    const servedRooms = limitToRooms 
      ? this.rooms.filter(r => limitToRooms.includes(r.id))
      : this.rooms.filter(r => !r.name.toLowerCase().includes('garage')); // Exclude garage from main system

    const totalCoolingLoad = servedRooms.reduce((sum, room) => {
      const roomLoad = this.loadCalculation.roomLoads.find(rl => rl.roomId === room.id);
      return sum + (roomLoad?.coolingLoad || 0);
    }, 0);

    // Equipment sizing (add 20% safety factor)
    const equipmentCapacity = Math.ceil(totalCoolingLoad * 1.2 / 6000) * 6000; // Round to nearest 6k BTU

    // Determine equipment location (prefer garage, basement, or utility area)
    const equipmentLocation = this.findEquipmentLocation();

    // Design trunk and branch system
    const { mainTrunk, branches } = this.designDuctwork(servedRooms, equipmentLocation);
    
    // Design return system
    const returns = this.designReturnSystem(servedRooms);

    return {
      id: 'ducted-main',
      type: 'ducted',
      equipmentType: 'air_handler',
      location: equipmentLocation,
      capacity: { 
        cooling: equipmentCapacity, 
        heating: Math.ceil(equipmentCapacity * 0.9) // Heat pumps typically 90% heating efficiency
      },
      efficiency: { seer: 16, hspf: 9.5 }, // High efficiency for new construction
      zones: servedRooms.map(r => r.id),
      mainTrunk,
      branches,
      returns
    };
  }

  private designDuctlessSystem(limitToRooms?: string[]): DuctlessSystem {
    const servedRooms = limitToRooms 
      ? this.rooms.filter(r => limitToRooms.includes(r.id))
      : this.rooms;

    const totalCoolingLoad = servedRooms.reduce((sum, room) => {
      const roomLoad = this.loadCalculation.roomLoads.find(rl => rl.roomId === room.id);
      return sum + (roomLoad?.coolingLoad || 0);
    }, 0);

    // Design indoor units for each room/zone
    const indoorUnits = this.designIndoorUnits(servedRooms);
    
    // Design outdoor unit location and capacity
    const outdoorUnit = {
      location: this.findOutdoorUnitLocation(),
      capacity: Math.ceil(totalCoolingLoad * 1.1 / 6000) * 6000 // 10% safety factor
    };

    // Design refrigerant line routing
    const linesets = this.designLinesets(indoorUnits, outdoorUnit.location);

    return {
      id: 'ductless-main',
      type: 'ductless',
      location: outdoorUnit.location,
      capacity: { 
        cooling: outdoorUnit.capacity, 
        heating: Math.ceil(outdoorUnit.capacity * 0.95) // Ductless heat pumps more efficient
      },
      efficiency: { seer: 20, hspf: 12 }, // Higher efficiency for ductless
      zones: servedRooms.map(r => r.id),
      outdoorUnit,
      indoorUnits,
      linesets
    };
  }

  private findEquipmentLocation(): { x: number; y: number; floor: string } {
    // Priority: garage > basement > utility room > closet
    const garage = this.rooms.find(r => r.name.toLowerCase().includes('garage'));
    if (garage) {
      return { x: 0, y: 0, floor: 'main' }; // Simplified location
    }

    const basement = this.rooms.find(r => r.name.toLowerCase().includes('basement'));
    if (basement) {
      return { x: 0, y: 0, floor: 'basement' };
    }

    // Default to utility area or central location
    return { x: 0, y: 0, floor: 'main' };
  }

  private findOutdoorUnitLocation(): { x: number; y: number } {
    // Prefer side or back of house, away from windows
    return { x: -10, y: 0 }; // Simplified - would need actual building layout
  }

  private designDuctwork(rooms: Room[], equipmentLocation: { x: number; y: number; floor: string }): {
    mainTrunk: DuctSegment;
    branches: DuctSegment[];
  } {
    // Calculate total CFM requirement
    const totalCFM = rooms.reduce((sum, room) => {
      const roomLoad = this.loadCalculation.roomLoads.find(rl => rl.roomId === room.id);
      return sum + Math.ceil((roomLoad?.coolingLoad || 0) / 1.1); // 1.1 BTU per CFM rule of thumb
    }, 0);

    // Main trunk sizing (velocity around 800-1000 FPM)
    const trunkVelocity = 900; // FPM
    const trunkArea = totalCFM / trunkVelocity; // sq ft
    const trunkDimensions = this.calculateRectangularDuctSize(trunkArea);

    const mainTrunk: DuctSegment = {
      id: 'main-trunk',
      startPoint: equipmentLocation,
      endPoint: { x: equipmentLocation.x + 40, y: equipmentLocation.y }, // 40ft run
      size: trunkDimensions,
      cfm: totalCFM
    };

    // Branch ducts for each room
    const branches: DuctSegment[] = rooms.map((room, index) => {
      const roomLoad = this.loadCalculation.roomLoads.find(rl => rl.roomId === room.id);
      const roomCFM = Math.ceil((roomLoad?.coolingLoad || 0) / 1.1);
      const branchSize = this.calculateRoundDuctSize(roomCFM);

      return {
        id: `branch-${room.id}`,
        startPoint: { x: equipmentLocation.x + 10 + (index * 8), y: equipmentLocation.y },
        endPoint: { x: equipmentLocation.x + 10 + (index * 8), y: equipmentLocation.y + 20 },
        size: { diameter: branchSize },
        cfm: roomCFM,
        room: room.id
      };
    });

    return { mainTrunk, branches };
  }

  private designReturnSystem(rooms: Room[]): ReturnDuct[] {
    // Design return ducts - typically one central return or returns in main living areas
    const livingAreas = rooms.filter(r => 
      r.name.toLowerCase().includes('living') || 
      r.name.toLowerCase().includes('family') ||
      r.name.toLowerCase().includes('great')
    );

    if (livingAreas.length > 0) {
      // Central return in main living area
      const totalReturnCFM = rooms.reduce((sum, room) => {
        const roomLoad = this.loadCalculation.roomLoads.find(rl => rl.roomId === room.id);
        return sum + Math.ceil((roomLoad?.coolingLoad || 0) / 1.1);
      }, 0);

      return [{
        id: 'central-return',
        location: { x: 20, y: 10 },
        size: this.calculateRectangularDuctSize(totalReturnCFM / 600), // 600 FPM for return
        cfm: totalReturnCFM,
        room: livingAreas[0].id
      }];
    }

    return [];
  }

  private designIndoorUnits(rooms: Room[]): IndoorUnit[] {
    return rooms.map(room => {
      const roomLoad = this.loadCalculation.roomLoads.find(rl => rl.roomId === room.id);
      const roomBTU = roomLoad?.coolingLoad || 9000;

      // Determine unit type based on room characteristics
      let unitType: IndoorUnit['type'] = 'wall_mount';
      if (room.name.toLowerCase().includes('bedroom') && room.area > 150) {
        unitType = 'ceiling_cassette';
      } else if (room.name.toLowerCase().includes('living') || room.name.toLowerCase().includes('great')) {
        unitType = 'ducted_slim'; // For open areas
      }

      return {
        id: `indoor-${room.id}`,
        type: unitType,
        location: { x: 5, y: 5, wall: 'exterior' }, // Simplified
        capacity: Math.ceil(roomBTU / 3000) * 3000, // Round to nearest 3k BTU
        room: room.id,
        cfm: unitType === 'ducted_slim' ? Math.ceil(roomBTU / 1.1) : undefined
      };
    });
  }

  private designLinesets(indoorUnits: IndoorUnit[], outdoorLocation: { x: number; y: number }): LineSet[] {
    return indoorUnits.map(unit => {
      const capacity = unit.capacity;
      
      // Line set sizing based on capacity and distance
      let liquidLine = 0.375; // 3/8" for small units
      let suctionLine = 0.75;  // 3/4" for small units
      
      if (capacity > 12000) {
        liquidLine = 0.5;   // 1/2"
        suctionLine = 0.875; // 7/8"
      }
      if (capacity > 18000) {
        liquidLine = 0.625; // 5/8"
        suctionLine = 1.125; // 1-1/8"
      }

      return {
        id: `lineset-${unit.id}`,
        path: [
          outdoorLocation,
          { x: outdoorLocation.x + 10, y: outdoorLocation.y },
          unit.location
        ],
        liquidLine,
        suctionLine,
        indoorUnit: unit.id
      };
    });
  }

  private calculateRectangularDuctSize(area: number): { width: number; height: number } {
    // Standard aspect ratios for rectangular ducts
    const aspectRatio = 2; // 2:1 ratio common
    const height = Math.sqrt(area / aspectRatio);
    const width = area / height;
    
    // Round to standard sizes
    return {
      width: Math.ceil(width),
      height: Math.ceil(height)
    };
  }

  private calculateRoundDuctSize(cfm: number): number {
    // Velocity around 700 FPM for branches
    const velocity = 700;
    const area = cfm / velocity; // sq ft
    const diameter = Math.sqrt(area * 4 / Math.PI) * 12; // Convert to inches
    
    // Round to standard duct sizes
    const standardSizes = [4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20];
    return standardSizes.find(size => size >= diameter) || 8;
  }

  private generateDesignNotes(): string[] {
    const notes: string[] = [];
    
    // Climate-specific notes
    if (this.climate.zone.includes('5') || this.climate.zone.includes('6')) {
      notes.push('Cold climate heat pump recommended with backup heat');
    }
    
    // Load-specific notes
    if (this.loadCalculation.totalCoolingLoad > 60000) {
      notes.push('Consider zoning system for large load');
    }
    
    // Standard notes
    notes.push('All ductwork to be insulated to R-8 minimum');
    notes.push('Include manual dampers for system balancing');
    notes.push('Refrigerant lines to be insulated per manufacturer specs');
    
    return notes;
  }

  private calculateCosts(systems: (DuctedSystem | DuctlessSystem)[]): {
    equipment: number;
    installation: number;
    total: number;
  } {
    let equipmentCost = 0;
    let installationCost = 0;

    systems.forEach(system => {
      if (system.type === 'ducted') {
        // Ducted system costs
        const tonnage = system.capacity.cooling / 12000;
        equipmentCost += tonnage * 1500; // $1500 per ton equipment
        installationCost += tonnage * 2500 + (system.branches.length * 800); // Installation + ductwork
      } else {
        // Ductless system costs  
        const tonnage = system.capacity.cooling / 12000;
        equipmentCost += tonnage * 2000; // $2000 per ton for ductless
        installationCost += system.indoorUnits.length * 1200; // $1200 per indoor unit installation
      }
    });

    return {
      equipment: Math.round(equipmentCost),
      installation: Math.round(installationCost),
      total: Math.round(equipmentCost + installationCost)
    };
  }
}

// Export utility function for quick layout generation
export function generateHVACLayout(
  rooms: Room[],
  loadCalculation: LoadCalculation,
  climate: ClimateZone
): HVACLayout {
  const generator = new HVACLayoutGenerator(rooms, loadCalculation, climate);
  return generator.generateLayout();
}