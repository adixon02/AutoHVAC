/**
 * AutoHVAC V2 - Main Application Store
 * Clean state management following our system map
 * Single convergent data flow: Manual OR Blueprint → Same Data Structure → Calculations
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import {
  ProjectInfo,
  BuildingCharacteristics,
  Room,
  ClimateData,
  LoadCalculation,
  SystemRecommendation,
  AppStep,
  ProcessingState,
  CalculationRequest,
  CalculationResponse
} from '@/types';
import { ClimateService } from '@/lib/climate-service';
import { config } from '@/lib/config';

// App State Interface
interface AppState {
  // Navigation State
  currentStep: AppStep;
  
  // Core Data (Single Source of Truth)
  project: ProjectInfo | null;
  building: BuildingCharacteristics | null;
  rooms: Room[];
  climate: ClimateData | null;
  
  // Results Data
  loadCalculation: LoadCalculation | null;
  recommendations: SystemRecommendation[];
  
  // UI State
  processing: ProcessingState;
  errors: Record<string, string>;
  
  // Blueprint-specific State
  blueprintJobId: string | null;
  blueprintAnalysis: any | null; // Raw blueprint analysis data
}

// App Actions Interface
interface AppActions {
  // Navigation Actions
  setCurrentStep: (step: AppStep) => void;
  navigateBack: () => void;
  startOver: () => void;
  
  // Project Actions
  setProject: (project: ProjectInfo) => void;
  updateProject: (updates: Partial<ProjectInfo>) => void;
  
  // Building Actions
  setBuilding: (building: BuildingCharacteristics) => void;
  updateBuilding: (updates: Partial<BuildingCharacteristics>) => void;
  
  // Room Actions
  setRooms: (rooms: Room[]) => void;
  addRoom: (room: Room) => void;
  updateRoom: (roomId: string, updates: Partial<Room>) => void;
  removeRoom: (roomId: string) => void;
  
  // Climate Actions
  loadClimateData: (zipCode: string) => Promise<void>;
  
  // Calculation Actions
  performCalculations: () => Promise<void>;
  clearCalculations: () => void;
  
  // Blueprint Actions  
  handleBlueprintUpload: (jobId: string, fileNames: string[]) => Promise<void>;
  setBlueprintAnalysis: (analysis: any) => void;
  clearBlueprintData: () => void;
  
  // Processing Actions
  setProcessing: (state: Partial<ProcessingState>) => void;
  setError: (key: string, message: string) => void;
  clearError: (key: string) => void;
  clearAllErrors: () => void;
  
  // Utility Actions
  canNavigateBack: () => boolean;
  isReadyForCalculations: () => boolean;
  hasResults: () => boolean;
}

type AppStore = AppState & AppActions;

// Initial State
const initialState: AppState = {
  currentStep: 'project',
  project: null,
  building: null,
  rooms: [],
  climate: null,
  loadCalculation: null,
  recommendations: [],
  processing: {
    status: 'idle',
    progress: 0,
    message: '',
  },
  errors: {},
  blueprintJobId: null,
  blueprintAnalysis: null,
};

// Create the store
export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,
        
        // Navigation Actions
        setCurrentStep: (step) => set({ currentStep: step }, false, 'setCurrentStep'),
        
        navigateBack: () => {
          const { currentStep, project } = get();
          let newStep: AppStep = 'project';
          
          switch (currentStep) {
            case 'input':
              newStep = 'project';
              break;
            case 'results':
              newStep = project?.inputMethod === 'blueprint' ? 'input' : 'project';
              break;
          }
          
          set({ currentStep: newStep }, false, 'navigateBack');
        },
        
        startOver: () => set({ ...initialState }, false, 'startOver'),
        
        // Project Actions
        setProject: (project) => {
          set({ project }, false, 'setProject');
          
          // Auto-load climate data when project is set
          if (project.zipCode) {
            get().loadClimateData(project.zipCode);
          }
        },
        
        updateProject: (updates) => {
          const { project } = get();
          if (!project) return;
          
          const updatedProject = { ...project, ...updates, updatedAt: new Date() };
          set({ project: updatedProject }, false, 'updateProject');
          
          // Reload climate data if ZIP code changed
          if (updates.zipCode && updates.zipCode !== project.zipCode) {
            get().loadClimateData(updates.zipCode);
          }
        },
        
        // Building Actions
        setBuilding: (building) => set({ building }, false, 'setBuilding'),
        
        updateBuilding: (updates) => {
          const { building } = get();
          if (!building) return;
          
          const updatedBuilding = { ...building, ...updates };
          set({ building: updatedBuilding }, false, 'updateBuilding');
        },
        
        // Room Actions
        setRooms: (rooms) => set({ rooms }, false, 'setRooms'),
        
        addRoom: (room) => {
          const { rooms } = get();
          set({ rooms: [...rooms, room] }, false, 'addRoom');
        },
        
        updateRoom: (roomId, updates) => {
          const { rooms } = get();
          const updatedRooms = rooms.map(room => 
            room.id === roomId ? { ...room, ...updates } : room
          );
          set({ rooms: updatedRooms }, false, 'updateRoom');
        },
        
        removeRoom: (roomId) => {
          const { rooms } = get();
          const filteredRooms = rooms.filter(room => room.id !== roomId);
          set({ rooms: filteredRooms }, false, 'removeRoom');
        },
        
        // Climate Actions
        loadClimateData: async (zipCode) => {
          try {
            get().clearError('climate');
            const climateData = await ClimateService.getClimateData(zipCode);
            set({ climate: climateData }, false, 'loadClimateData:success');
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to load climate data';
            get().setError('climate', errorMessage);
            console.error('Climate data loading failed:', error);
          }
        },
        
        // Calculation Actions
        performCalculations: async () => {
          const { project, building, rooms, climate } = get();
          
          if (!project || !building || !rooms.length || !climate) {
            get().setError('calculation', 'Missing required data for calculations');
            return;
          }
          
          try {
            get().setProcessing({ status: 'processing', progress: 0, message: 'Calculating HVAC loads...' });
            get().clearError('calculation');
            
            // Transform camelCase data to snake_case for API
            const apiRequest = {
              project: {
                id: project.id,
                project_name: project.projectName,
                zip_code: project.zipCode,
                building_type: project.buildingType,
                construction_type: project.constructionType,
                input_method: project.inputMethod,
                created_at: project.createdAt.toISOString(),
                updated_at: project.updatedAt.toISOString(),
              },
              building: {
                total_square_footage: building.totalSquareFootage,
                foundation_type: building.foundationType,
                wall_insulation: building.wallInsulation,
                ceiling_insulation: building.ceilingInsulation,
                window_type: building.windowType,
                building_orientation: building.buildingOrientation,
                stories: building.stories,
                building_age: building.buildingAge,
              },
              rooms: rooms.map(room => ({
                id: room.id,
                name: room.name,
                area: room.area,
                ceiling_height: room.ceilingHeight,
                exterior_walls: room.exteriorWalls,
                window_area: room.windowArea,
                occupants: room.occupants,
                equipment_load: room.equipmentLoad,
                room_type: room.roomType,
              }))
            };
            
            const response = await fetch(`${config.api.baseUrl}/api/v2/calculations/calculate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(apiRequest),
            });
            
            if (!response.ok) {
              const errorData = await response.json().catch(() => ({}));
              throw new Error(errorData.detail || `Calculation failed: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Transform snake_case response back to camelCase
            const transformedResult: CalculationResponse = {
              loadCalculation: {
                projectId: result.load_calculation.project_id,
                totalCoolingLoad: result.load_calculation.total_cooling_load,
                totalHeatingLoad: result.load_calculation.total_heating_load,
                coolingTons: result.load_calculation.cooling_tons,
                heatingTons: result.load_calculation.heating_tons,
                roomLoads: result.load_calculation.room_loads?.map((roomLoad: any) => ({
                  roomId: roomLoad.room_id,
                  coolingLoad: roomLoad.cooling_load,
                  heatingLoad: roomLoad.heating_load,
                })) || [],
                calculatedAt: new Date(result.load_calculation.calculated_at),
              },
              recommendations: result.recommendations.map((rec: any) => ({
                tier: rec.tier,
                coolingSystem: {
                  type: rec.cooling_system.type,
                  size: rec.cooling_system.size,
                  seer: rec.cooling_system.seer,
                  brand: rec.cooling_system.brand,
                  model: rec.cooling_system.model,
                  estimatedCost: rec.cooling_system.estimated_cost,
                },
                heatingSystem: {
                  type: rec.heating_system.type,
                  size: rec.heating_system.size,
                  efficiency: rec.heating_system.efficiency,
                  brand: rec.heating_system.brand,
                  model: rec.heating_system.model,
                  estimatedCost: rec.heating_system.estimated_cost,
                }
              }))
            };
            
            set({
              loadCalculation: transformedResult.loadCalculation,
              recommendations: transformedResult.recommendations,
              processing: { status: 'completed', progress: 100, message: 'Calculations complete!' },
              currentStep: 'results',
            }, false, 'performCalculations:success');
            
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Calculation failed';
            get().setError('calculation', errorMessage);
            get().setProcessing({ status: 'error', progress: 0, message: 'Calculation failed' });
            console.error('Calculation failed:', error);
          }
        },
        
        clearCalculations: () => {
          set({
            loadCalculation: null,
            recommendations: [],
          }, false, 'clearCalculations');
        },
        
        // Blueprint Actions
        handleBlueprintUpload: async (jobId, fileNames) => {
          try {
            get().setProcessing({
              status: 'processing',
              progress: 50,
              message: 'Processing blueprint analysis...',
              jobId,
            });
            
            // Fetch actual results from API
            const response = await fetch(`${config.api.baseUrl}/api/v2/blueprint/results/${jobId}`);
            
            if (!response.ok) {
              throw new Error(`Failed to fetch blueprint results: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Blueprint API response:', data);
            
            // Extract and transform the data from API response
            const { results } = data;
            
            // Transform building data
            const building: BuildingCharacteristics = {
              totalSquareFootage: Math.max(results.total_area || 500, 500),
              foundationType: 'slab' as const, // Default for now
              wallInsulation: 'good' as const,
              ceilingInsulation: 'good' as const,
              windowType: 'double' as const,
              buildingOrientation: 'south' as const,
              stories: results.building_details?.floors || 1,
              buildingAge: 'new' as const,
            };
            
            // Transform rooms data
            const rooms: Room[] = results.rooms.map((room: any, index: number) => ({
              id: `room-${index + 1}`,
              name: room.name || `Room ${index + 1}`,
              area: Math.max(room.area || 200, 50),
              ceilingHeight: Math.max(Math.floor(room.height || 10), 8),
              exteriorWalls: room.exterior_walls || 0,
              windowArea: (room.windows || 0) * 15, // Assume 15 sq ft per window
              occupants: room.name?.toLowerCase().includes('bedroom') ? 2 : 4,
              equipmentLoad: room.name?.toLowerCase().includes('kitchen') ? 800 : 
                            room.name?.toLowerCase().includes('bedroom') ? 200 : 500,
              roomType: room.name?.toLowerCase().includes('bedroom') ? 'bedroom' as const :
                       room.name?.toLowerCase().includes('kitchen') ? 'kitchen' as const :
                       room.name?.toLowerCase().includes('bathroom') ? 'bathroom' as const :
                       room.name?.toLowerCase().includes('dining') ? 'dining' as const :
                       'living' as const,
            }));
            
            // Set the extracted data in our store
            set({
              blueprintJobId: jobId,
              blueprintAnalysis: data,
              building,
              rooms,
              processing: {
                status: 'completed',
                progress: 100,
                message: 'Blueprint analysis complete!',
                jobId,
              },
            }, false, 'handleBlueprintUpload:success');
            
            // Auto-proceed to calculations
            setTimeout(() => {
              get().performCalculations();
            }, 1000);
            
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Blueprint processing failed';
            get().setError('blueprint', errorMessage);
            get().setProcessing({ status: 'error', progress: 0, message: errorMessage });
            console.error('Blueprint upload handling failed:', error);
          }
        },
        
        setBlueprintAnalysis: (analysis) => {
          set({ blueprintAnalysis: analysis }, false, 'setBlueprintAnalysis');
        },
        
        clearBlueprintData: () => {
          set({
            blueprintJobId: null,
            blueprintAnalysis: null,
          }, false, 'clearBlueprintData');
        },
        
        // Processing Actions
        setProcessing: (state) => {
          const { processing } = get();
          set({ processing: { ...processing, ...state } }, false, 'setProcessing');
        },
        
        setError: (key, message) => {
          const { errors } = get();
          set({ errors: { ...errors, [key]: message } }, false, 'setError');
        },
        
        clearError: (key) => {
          const { errors } = get();
          const { [key]: removed, ...remainingErrors } = errors;
          set({ errors: remainingErrors }, false, 'clearError');
        },
        
        clearAllErrors: () => set({ errors: {} }, false, 'clearAllErrors'),
        
        // Utility Actions
        canNavigateBack: () => {
          const { currentStep } = get();
          return currentStep !== 'project';
        },
        
        isReadyForCalculations: () => {
          const { project, building, rooms, climate } = get();
          return !!(project && building && rooms.length > 0 && climate);
        },
        
        hasResults: () => {
          const { loadCalculation, recommendations } = get();
          return !!(loadCalculation && recommendations.length > 0);
        },
      }),
      {
        name: 'autohvac-app-store',
        // Only persist essential data, not temporary UI state
        partialize: (state) => ({
          project: state.project,
          building: state.building,
          rooms: state.rooms,
          climate: state.climate,
          blueprintJobId: state.blueprintJobId,
          // Don't persist: processing state, errors, results (regenerate)
        }),
      }
    ),
    { name: 'AutoHVAC Store' }
  )
);