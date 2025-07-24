import Link from 'next/link';
import { Button, Card, CardHeader, CardTitle, CardContent } from '@/components/ui';

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            AutoHVAC V2 🚀
          </h1>
          <p className="text-xl text-gray-600 mb-2">
            Clean rebuild from the ground up
          </p>
          <p className="text-lg text-gray-500">
            Following our planning documents to build it right this time
          </p>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle>Development Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 border border-green-200 bg-green-50 rounded-lg">
                <h3 className="font-semibold text-green-900">✅ Backend API</h3>
                <p className="text-sm text-green-700">Climate service & Manual J calculator</p>
              </div>
              <div className="p-4 border border-green-200 bg-green-50 rounded-lg">
                <h3 className="font-semibold text-green-900">✅ UI Components</h3>
                <p className="text-sm text-green-700">Complete component library</p>
              </div>
              <div className="p-4 border border-yellow-200 bg-yellow-50 rounded-lg">
                <h3 className="font-semibold text-yellow-900">🔄 Form Components</h3>
                <p className="text-sm text-yellow-700">Project, Building, Room forms</p>
              </div>
              <div className="p-4 border border-gray-200 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-900">⏳ State Management</h3>
                <p className="text-sm text-gray-700">Zustand store setup</p>
              </div>
            </div>
            
            <div className="pt-4">
              <Link href="/test-components">
                <Button className="w-full">
                  View Component Library →
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}