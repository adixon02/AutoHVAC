'use client';

import { useState, useCallback } from 'react';
import { ProjectInfo, BuildingInfo, Room } from '../lib/types';

type Step = 'project' | 'building' | 'rooms' | 'results' | 'blueprint';

interface UseProjectReturn {
  // State
  currentStep: Step;
  projectInfo: ProjectInfo | null;
  buildingInfo: BuildingInfo | null;
  rooms: Room[];
  inputMethod: 'manual' | 'blueprint';
  
  // Actions
  setProjectInfo: (data: ProjectInfo) => void;
  setBuildingInfo: (data: BuildingInfo) => void;
  setRooms: (data: Room[]) => void;
  navigateToStep: (step: Step) => void;
  navigateBack: () => void;
  startOver: () => void;
  
  // Computed
  canNavigateBack: boolean;
  isComplete: boolean;
}

export function useProject(): UseProjectReturn {
  const [currentStep, setCurrentStep] = useState<Step>('project');
  const [projectInfo, setProjectInfoState] = useState<ProjectInfo | null>(null);
  const [buildingInfo, setBuildingInfoState] = useState<BuildingInfo | null>(null);
  const [rooms, setRoomsState] = useState<Room[]>([]);
  const [inputMethod, setInputMethod] = useState<'manual' | 'blueprint'>('manual');

  const setProjectInfo = useCallback((data: ProjectInfo) => {
    setProjectInfoState(data);
    setInputMethod(data.inputMethod || 'manual');
    
    if (data.inputMethod === 'blueprint') {
      setCurrentStep('blueprint');
    } else {
      setCurrentStep('building');
    }
  }, []);

  const setBuildingInfo = useCallback((data: BuildingInfo) => {
    setBuildingInfoState(data);
    setCurrentStep('rooms');
  }, []);

  const setRooms = useCallback((data: Room[]) => {
    setRoomsState(data);
    setCurrentStep('results');
  }, []);

  const navigateToStep = useCallback((step: Step) => {
    setCurrentStep(step);
  }, []);

  const navigateBack = useCallback(() => {
    switch (currentStep) {
      case 'building':
        setCurrentStep('project');
        break;
      case 'rooms':
        setCurrentStep('building');
        break;
      case 'results':
        if (inputMethod === 'blueprint') {
          setCurrentStep('blueprint');
        } else {
          setCurrentStep('rooms');
        }
        break;
      case 'blueprint':
        setCurrentStep('project');
        break;
    }
  }, [currentStep, inputMethod]);

  const startOver = useCallback(() => {
    setCurrentStep('project');
    setProjectInfoState(null);
    setBuildingInfoState(null);
    setRoomsState([]);
    setInputMethod('manual');
  }, []);

  const canNavigateBack = currentStep !== 'project';
  const isComplete = currentStep === 'results' && 
    (inputMethod === 'blueprint' || Boolean(projectInfo && buildingInfo && rooms.length > 0));

  return {
    // State
    currentStep,
    projectInfo,
    buildingInfo,
    rooms,
    inputMethod,
    
    // Actions
    setProjectInfo,
    setBuildingInfo,
    setRooms,
    navigateToStep,
    navigateBack,
    startOver,
    
    // Computed
    canNavigateBack,
    isComplete,
  };
}