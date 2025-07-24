'use client';

import { useState } from 'react';
import { Header } from '@/components/layout/Header';
import { ProgressIndicator } from '@/components/layout/ProgressIndicator';
import { 
  Button, 
  Input, 
  Select, 
  Card, 
  CardHeader, 
  CardTitle, 
  CardContent,
  ProgressBar,
  Alert 
} from '@/components/ui';

const sampleSteps = [
  { id: '1', name: 'Project', status: 'complete' as const },
  { id: '2', name: 'Building', status: 'complete' as const },
  { id: '3', name: 'Rooms', status: 'current' as const, description: 'Add room details' },
  { id: '4', name: 'Results', status: 'upcoming' as const },
];

const selectOptions = [
  { value: 'residential', label: 'Residential' },
  { value: 'commercial', label: 'Commercial' },
];

export default function TestComponents() {
  const [loading, setLoading] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [selectValue, setSelectValue] = useState('');
  
  const handleTestAction = () => {
    setLoading(true);
    setTimeout(() => setLoading(false), 2000);
  };
  
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">UI Components Test</h2>
          <ProgressIndicator steps={sampleSteps} />
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Buttons */}
          <Card>
            <CardHeader>
              <CardTitle>Buttons</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4 flex-wrap">
                <Button variant="primary">Primary</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="ghost">Ghost</Button>
              </div>
              <div className="flex gap-4 flex-wrap">
                <Button size="sm">Small</Button>
                <Button size="md">Medium</Button>
                <Button size="lg">Large</Button>
              </div>
              <div className="flex gap-4">
                <Button loading={loading} onClick={handleTestAction}>
                  {loading ? 'Loading...' : 'Test Loading'}
                </Button>
                <Button disabled>Disabled</Button>
              </div>
            </CardContent>
          </Card>
          
          {/* Form Controls */}
          <Card>
            <CardHeader>
              <CardTitle>Form Controls</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                label="Project Name"
                placeholder="Enter project name"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                helperText="This will be used in reports"
                required
              />
              <Input
                label="ZIP Code"
                placeholder="12345"
                error={inputValue.length > 0 && inputValue.length !== 5 ? "ZIP code must be 5 digits" : undefined}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
              />
              <Select
                label="Building Type"
                options={selectOptions}
                value={selectValue}
                onChange={(e) => setSelectValue(e.target.value)}
                placeholder="Select building type"
                required
              />
            </CardContent>
          </Card>
          
          {/* Progress & Alerts */}
          <Card>
            <CardHeader>
              <CardTitle>Progress & Feedback</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <ProgressBar progress={75} />
              <ProgressBar progress={100} color="green" showPercentage={false} />
              <ProgressBar progress={30} color="yellow" size="sm" />
            </CardContent>
          </Card>
          
          {/* Alerts */}
          <Card>
            <CardHeader>
              <CardTitle>Alerts</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Alert variant="success" title="Success">
                Your calculation completed successfully!
              </Alert>
              <Alert variant="warning" title="Warning">
                Some data may be incomplete.
              </Alert>
              <Alert variant="error" title="Error">
                Unable to calculate loads. Please check your input.
              </Alert>
              <Alert variant="info">
                Climate data loaded for ZIP code 30301.
              </Alert>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}