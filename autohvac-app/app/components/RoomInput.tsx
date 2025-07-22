'use client';

import { useState } from 'react';
import { Room, BuildingInfo } from '../lib/types';

interface RoomInputProps {
  onSubmit: (rooms: Room[]) => void;
  onBack: () => void;
  buildingInfo: BuildingInfo;
}

const COMMON_ROOMS = [
  { name: 'Living Room', area: 300, occupancy: 4 },
  { name: 'Master Bedroom', area: 200, occupancy: 2 },
  { name: 'Kitchen', area: 150, occupancy: 2 },
  { name: 'Dining Room', area: 150, occupancy: 4 },
  { name: 'Bedroom', area: 120, occupancy: 1 },
  { name: 'Bathroom', area: 50, occupancy: 1 },
  { name: 'Office', area: 100, occupancy: 1 },
];

export default function RoomInput({ onSubmit, onBack, buildingInfo }: RoomInputProps) {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [showAddRoom, setShowAddRoom] = useState(false);
  const [newRoom, setNewRoom] = useState<Partial<Room>>({
    name: '',
    area: 100,
    ceilingHeight: buildingInfo.ceilingHeight,
    windowArea: 20,
    exteriorWalls: 1,
    occupancy: 1
  });

  const addRoom = (roomTemplate?: typeof COMMON_ROOMS[0]) => {
    const room: Room = {
      id: Date.now().toString(),
      name: roomTemplate?.name || newRoom.name || 'Room',
      area: roomTemplate?.area || newRoom.area || 100,
      ceilingHeight: buildingInfo.ceilingHeight,
      windowArea: Math.round((roomTemplate?.area || newRoom.area || 100) * 0.15),
      exteriorWalls: 1,
      occupancy: roomTemplate?.occupancy || newRoom.occupancy || 1
    };
    setRooms([...rooms, room]);
    setShowAddRoom(false);
    setNewRoom({
      name: '',
      area: 100,
      ceilingHeight: buildingInfo.ceilingHeight,
      windowArea: 20,
      exteriorWalls: 1,
      occupancy: 1
    });
  };

  const updateRoom = (id: string, field: keyof Room, value: any) => {
    setRooms(rooms.map(room => 
      room.id === id ? { ...room, [field]: value } : room
    ));
  };

  const removeRoom = (id: string) => {
    setRooms(rooms.filter(room => room.id !== id));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (rooms.length > 0) {
      onSubmit(rooms);
    }
  };

  const totalArea = rooms.reduce((sum, room) => sum + room.area, 0);

  return (
    <div className="card max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-hvac-navy">Room Details</h2>
        <p className="text-gray-600 mt-1">
          Building: {buildingInfo.squareFootage} sq ft | 
          Defined: {totalArea} sq ft | 
          Remaining: {buildingInfo.squareFootage - totalArea} sq ft
        </p>
      </div>

      {/* Quick Add Common Rooms */}
      {!showAddRoom && (
        <div className="mb-6">
          <p className="text-sm font-medium text-gray-700 mb-3">Quick Add Common Rooms:</p>
          <div className="flex flex-wrap gap-2">
            {COMMON_ROOMS.map((room) => (
              <button
                key={room.name}
                type="button"
                onClick={() => addRoom(room)}
                className="px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm transition-colors"
              >
                + {room.name}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setShowAddRoom(true)}
              className="px-3 py-1 bg-hvac-blue text-white hover:bg-hvac-navy rounded-lg text-sm transition-colors"
            >
              + Custom Room
            </button>
          </div>
        </div>
      )}

      {/* Add Custom Room Form */}
      {showAddRoom && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="font-semibold mb-3">Add Custom Room</h3>
          <div className="grid grid-cols-3 gap-4">
            <input
              type="text"
              placeholder="Room name"
              className="input-field"
              value={newRoom.name}
              onChange={(e) => setNewRoom({ ...newRoom, name: e.target.value })}
            />
            <input
              type="number"
              placeholder="Area (sq ft)"
              className="input-field"
              value={newRoom.area}
              onChange={(e) => setNewRoom({ ...newRoom, area: parseInt(e.target.value) })}
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => addRoom()}
                className="btn-primary text-sm py-2"
              >
                Add
              </button>
              <button
                type="button"
                onClick={() => setShowAddRoom(false)}
                className="btn-secondary text-sm py-2"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Room List */}
      <form onSubmit={handleSubmit}>
        {rooms.length > 0 ? (
          <div className="space-y-4 mb-6">
            {rooms.map((room) => (
              <div key={room.id} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex justify-between items-start mb-3">
                  <h4 className="font-semibold text-lg">{room.name}</h4>
                  <button
                    type="button"
                    onClick={() => removeRoom(room.id)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Remove
                  </button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Area (sq ft)</label>
                    <input
                      type="number"
                      className="input-field text-sm py-2"
                      value={room.area}
                      onChange={(e) => updateRoom(room.id, 'area', parseInt(e.target.value))}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Window Area (sq ft)</label>
                    <input
                      type="number"
                      className="input-field text-sm py-2"
                      value={room.windowArea}
                      onChange={(e) => updateRoom(room.id, 'windowArea', parseInt(e.target.value))}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Exterior Walls</label>
                    <select
                      className="input-field text-sm py-2"
                      value={room.exteriorWalls}
                      onChange={(e) => updateRoom(room.id, 'exteriorWalls', parseInt(e.target.value))}
                    >
                      <option value="0">0 (Interior)</option>
                      <option value="1">1 Wall</option>
                      <option value="2">2 Walls</option>
                      <option value="3">3 Walls</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Occupancy</label>
                    <input
                      type="number"
                      className="input-field text-sm py-2"
                      value={room.occupancy}
                      onChange={(e) => updateRoom(room.id, 'occupancy', parseInt(e.target.value))}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            No rooms added yet. Use the quick add buttons above or create a custom room.
          </div>
        )}

        <div className="flex justify-between pt-4">
          <button type="button" onClick={onBack} className="btn-secondary">
            Back
          </button>
          <button 
            type="submit" 
            className="btn-primary"
            disabled={rooms.length === 0}
          >
            Calculate Load & Get Recommendations
          </button>
        </div>
      </form>
    </div>
  );
}