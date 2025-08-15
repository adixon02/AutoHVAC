// Dynamic imports for code splitting - each step loads only when needed
import dynamic from 'next/dynamic'
import React from 'react'

const LoadingComponent = () => React.createElement('div', { 
  className: 'animate-pulse h-96 bg-gray-100 rounded-xl' 
})

export const Step1ProjectSetup = dynamic(() => import('./Step1ProjectSetup'), {
  loading: LoadingComponent
})

export const Step2BuildingBasics = dynamic(() => import('./Step2BuildingBasics'), {
  loading: LoadingComponent
})

export const Step3DuctConfig = dynamic(() => import('./Step3DuctConfig'), {
  loading: LoadingComponent
})

export const Step4HeatingSystem = dynamic(() => import('./Step4HeatingSystem'), {
  loading: LoadingComponent
})

export const Step5ZipCode = dynamic(() => import('./Step5ZipCode'), {
  loading: LoadingComponent
})

export const Step6Orientation = dynamic(() => import('./Step6Orientation'), {
  loading: LoadingComponent
})

export const Step7Review = dynamic(() => import('./Step7Review'), {
  loading: LoadingComponent
})

export const Step8EmailCollection = dynamic(() => import('./Step8EmailCollection'), {
  loading: LoadingComponent
})

// Shared types
export interface ProjectData {
  projectName: string
  blueprintFile: File | null
  squareFootage: string
  zipCode: string
  email: string
  numberOfStories: '1' | '2' | '3+' | 'not_sure'
  heatingFuel: 'gas' | 'heat_pump' | 'electric' | 'not_sure'
  ductConfig: 'ducted_attic' | 'ducted_crawl' | 'ductless' | 'not_sure'
  windowPerformance: 'standard' | 'high_performance' | 'premium' | 'not_sure'
  buildingOrientation: 'N' | 'NE' | 'E' | 'SE' | 'S' | 'SW' | 'W' | 'NW' | 'not_sure' | 'unknown'
}