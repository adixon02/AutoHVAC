'use client';

import React, { useState } from 'react';
import { Room, LoadCalculation, SystemRecommendation } from '../lib/types';

interface HVACLayoutViewerProps {
  rooms: Room[];
  loadCalculation: LoadCalculation;
  recommendations: SystemRecommendation[];
}

interface LayoutRoom {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  area: number;
  vents: { x: number; y: number; type: 'supply' | 'return' }[];
}

interface Equipment {
  id: string;
  type: 'air_handler' | 'condenser' | 'thermostat';
  name: string;
  x: number;
  y: number;
}

interface DuctSegment {
  id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  size: string;
  type: 'main' | 'branch' | 'return';
}

export default function HVACLayoutViewer({ rooms, loadCalculation, recommendations }: HVACLayoutViewerProps) {
  const [selectedFloor, setSelectedFloor] = useState<'main' | 'upper' | 'basement'>('main');
  const [selectedSystem, setSelectedSystem] = useState(0);

  // Generate layout based on rooms and load calculations
  const generateLayout = () => {
    const layoutRooms: LayoutRoom[] = [];
    const equipment: Equipment[] = [];
    const ductwork: DuctSegment[] = [];

    // Create a simplified floor layout
    const floorWidth = 800;
    const floorHeight = 600;
    
    // Arrange rooms in a grid-like pattern
    const roomsPerRow = Math.ceil(Math.sqrt(rooms.length));
    const roomWidth = (floorWidth - 80) / roomsPerRow;
    const roomHeight = (floorHeight - 80) / Math.ceil(rooms.length / roomsPerRow);

    rooms.forEach((room, index) => {
      const row = Math.floor(index / roomsPerRow);
      const col = index % roomsPerRow;
      
      const x = 40 + col * roomWidth;
      const y = 40 + row * roomHeight;
      
      // Calculate number of vents based on room load
      const roomLoad = loadCalculation.roomLoads[index];
      const ventCount = Math.max(1, Math.floor(roomLoad.coolingLoad / 8000)); // 1 vent per ~8k BTU
      
      const vents = [];
      for (let i = 0; i < ventCount; i++) {
        vents.push({
          x: x + (roomWidth / (ventCount + 1)) * (i + 1),
          y: y + roomHeight * 0.2,
          type: 'supply' as const
        });
      }
      
      // Add return vent for larger rooms
      if (room.area > 200) {
        vents.push({
          x: x + roomWidth * 0.8,
          y: y + roomHeight * 0.8,
          type: 'return' as const
        });
      }

      layoutRooms.push({
        id: room.id,
        name: room.name,
        x,
        y,
        width: roomWidth,
        height: roomHeight,
        area: room.area,
        vents
      });
    });

    // Place equipment
    const selectedRec = recommendations[selectedSystem];
    
    // Air handler placement (usually central or basement/utility)
    equipment.push({
      id: 'air_handler_1',
      type: 'air_handler',
      name: 'Air Handler',
      x: floorWidth / 2 - 30,
      y: floorHeight - 100
    });

    // Condenser (outside)
    equipment.push({
      id: 'condenser_1', 
      type: 'condenser',
      name: 'Outdoor Unit',
      x: floorWidth - 80,
      y: floorHeight / 2
    });

    // Thermostat (main living area)
    const mainRoom = layoutRooms.find(r => r.name.toLowerCase().includes('living')) || layoutRooms[0];
    if (mainRoom) {
      equipment.push({
        id: 'thermostat_1',
        type: 'thermostat',
        name: 'Thermostat',
        x: mainRoom.x + mainRoom.width * 0.1,
        y: mainRoom.y + mainRoom.height * 0.5
      });
    }

    // Generate ductwork
    const airHandler = equipment.find(e => e.type === 'air_handler');
    if (airHandler) {
      // Main trunk line
      ductwork.push({
        id: 'main_trunk',
        x1: airHandler.x + 30,
        y1: airHandler.y,
        x2: airHandler.x + 30,
        y2: 100,
        size: '20"x8"',
        type: 'main'
      });

      // Branch ducts to each room
      layoutRooms.forEach((room, index) => {
        room.vents.forEach((vent, ventIndex) => {
          if (vent.type === 'supply') {
            // Connect vent to main trunk
            ductwork.push({
              id: `branch_${room.id}_${ventIndex}`,
              x1: airHandler.x + 30,
              y1: 100,
              x2: vent.x,
              y2: vent.y,
              size: '8" round',
              type: 'branch'
            });
          }
        });
      });

      // Return ducts
      layoutRooms.forEach((room) => {
        const returnVent = room.vents.find(v => v.type === 'return');
        if (returnVent) {
          ductwork.push({
            id: `return_${room.id}`,
            x1: returnVent.x,
            y1: returnVent.y,
            x2: airHandler.x - 30,
            y2: airHandler.y,
            size: '14"x8"',
            type: 'return'
          });
        }
      });
    }

    return { layoutRooms, equipment, ductwork };
  };

  const { layoutRooms, equipment, ductwork } = generateLayout();
  const selectedRec = recommendations[selectedSystem] || recommendations[0];

  return (
    <div className="card">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-xl font-bold">HVAC System Layout</h3>
          <p className="text-gray-600">
            {selectedRec?.systemType} - {(selectedRec?.coolingCapacity / 12000).toFixed(1)} tons
          </p>
        </div>
        
        <div className="flex gap-4">
          {/* System Selection */}
          <select
            value={selectedSystem}
            onChange={(e) => setSelectedSystem(Number(e.target.value))}
            className="px-3 py-2 border rounded-md"
          >
            {recommendations.map((rec, index) => (
              <option key={index} value={index}>
                {rec.tier.charAt(0).toUpperCase() + rec.tier.slice(1)} - {(rec.coolingCapacity / 12000).toFixed(1)} tons
              </option>
            ))}
          </select>

          {/* Floor Selection */}
          <div className="flex border rounded-md overflow-hidden">
            <button
              onClick={() => setSelectedFloor('main')}
              className={`px-4 py-2 text-sm ${
                selectedFloor === 'main' ? 'bg-blue-500 text-white' : 'bg-gray-100'
              }`}
            >
              Main Level
            </button>
            <button
              onClick={() => setSelectedFloor('upper')}
              className={`px-4 py-2 text-sm ${
                selectedFloor === 'upper' ? 'bg-blue-500 text-white' : 'bg-gray-100'
              }`}
            >
              Upper Level
            </button>
            <button
              onClick={() => setSelectedFloor('basement')}
              className={`px-4 py-2 text-sm ${
                selectedFloor === 'basement' ? 'bg-blue-500 text-white' : 'bg-gray-100'
              }`}
            >
              Basement
            </button>
          </div>
        </div>
      </div>

      {/* Layout Canvas */}
      <div className="relative border-2 border-gray-300 bg-white rounded-lg overflow-hidden" style={{ height: '600px' }}>
        <svg width="100%" height="100%" viewBox="0 0 800 600">
          {/* Room outlines */}
          {layoutRooms.map((room) => (
            <g key={room.id}>
              <rect
                x={room.x}
                y={room.y}
                width={room.width}
                height={room.height}
                fill="none"
                stroke="#333"
                strokeWidth="2"
              />
              <text
                x={room.x + room.width / 2}
                y={room.y + room.height / 2}
                textAnchor="middle"
                className="text-sm font-medium"
                fill="#333"
              >
                {room.name}
              </text>
              <text
                x={room.x + room.width / 2}
                y={room.y + room.height / 2 + 16}
                textAnchor="middle"
                className="text-xs"
                fill="#666"
              >
                {room.area} sq ft
              </text>
            </g>
          ))}

          {/* Ductwork */}
          {ductwork.map((duct) => (
            <g key={duct.id}>
              <line
                x1={duct.x1}
                y1={duct.y1}
                x2={duct.x2}
                y2={duct.y2}
                stroke={duct.type === 'main' ? '#2563eb' : duct.type === 'branch' ? '#3b82f6' : '#ef4444'}
                strokeWidth={duct.type === 'main' ? 4 : 2}
                strokeDasharray={duct.type === 'return' ? '5,5' : 'none'}
              />
            </g>
          ))}

          {/* Vents */}
          {layoutRooms.map((room) =>
            room.vents.map((vent, index) => (
              <g key={`${room.id}-vent-${index}`}>
                <circle
                  cx={vent.x}
                  cy={vent.y}
                  r={vent.type === 'supply' ? 8 : 6}
                  fill={vent.type === 'supply' ? '#3b82f6' : '#ef4444'}
                />
                <text
                  x={vent.x}
                  y={vent.y - 12}
                  textAnchor="middle"
                  className="text-xs font-medium"
                  fill="#333"
                >
                  {vent.type === 'supply' ? 'S' : 'R'}
                </text>
              </g>
            ))
          )}

          {/* Equipment */}
          {equipment.map((item) => (
            <g key={item.id}>
              <rect
                x={item.x}
                y={item.y}
                width={item.type === 'thermostat' ? 20 : 60}
                height={item.type === 'thermostat' ? 15 : 40}
                fill={item.type === 'air_handler' ? '#10b981' : item.type === 'condenser' ? '#f59e0b' : '#6b7280'}
                stroke="#333"
                strokeWidth="1"
                rx="2"
              />
              <text
                x={item.x + (item.type === 'thermostat' ? 10 : 30)}
                y={item.y - 5}
                textAnchor="middle"
                className="text-xs font-medium"
                fill="#333"
              >
                {item.name}
              </text>
            </g>
          ))}
        </svg>

        {/* Legend */}
        <div className="absolute top-4 left-4 bg-white p-3 rounded-md shadow-md border text-xs">
          <div className="font-semibold mb-2">Legend</div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-4 h-1 bg-blue-600"></div>
            <span>Main Trunk</span>
          </div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-4 h-1 bg-blue-400"></div>
            <span>Branch Ducts</span>
          </div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-4 h-1 bg-red-500" style={{ borderTop: '1px dashed' }}></div>
            <span>Return Ducts</span>
          </div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-3 h-3 rounded-full bg-blue-500"></div>
            <span>Supply Vents</span>
          </div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <span>Return Vents</span>
          </div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-4 h-3 bg-green-500 rounded-sm"></div>
            <span>Air Handler</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-3 bg-amber-500 rounded-sm"></div>
            <span>Condenser</span>
          </div>
        </div>
      </div>

      {/* System Details */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
        <div className="bg-gray-50 p-4 rounded-md">
          <h4 className="font-semibold mb-2">Equipment Specifications</h4>
          <div className="space-y-1">
            <div>Air Handler: {(selectedRec?.coolingCapacity / 12000).toFixed(1)} ton</div>
            <div>Outdoor Unit: {(selectedRec?.coolingCapacity / 12000).toFixed(1)} ton</div>
            <div>Efficiency: {selectedRec?.efficiency.seer} SEER / {selectedRec?.efficiency.hspf} HSPF</div>
          </div>
        </div>
        
        <div className="bg-gray-50 p-4 rounded-md">
          <h4 className="font-semibold mb-2">Ductwork Summary</h4>
          <div className="space-y-1">
            <div>Main Trunk: 20" x 8"</div>
            <div>Branch Ducts: 6" - 8" round</div>
            <div>Return Ducts: 14" x 8"</div>
            <div>Total Length: ~{Math.floor(ductwork.length * 8)} ft</div>
          </div>
        </div>
        
        <div className="bg-gray-50 p-4 rounded-md">
          <h4 className="font-semibold mb-2">Installation Notes</h4>
          <div className="space-y-1 text-xs">
            <div>• All ducts routed through attic/crawl space</div>
            <div>• Insulation R-8 minimum required</div>
            <div>• Include balancing dampers at branches</div>
            <div>• Install programmable thermostat</div>
          </div>
        </div>
      </div>
    </div>
  );
}