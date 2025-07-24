export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          AutoHVAC 🚀
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          HVAC Load Calculation Tool
        </p>
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h2 className="text-2xl font-semibold mb-4">System Status</h2>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span>Frontend Deployment:</span>
              <span className="text-green-600 font-semibold">✅ Working</span>
            </div>
            <div className="flex justify-between items-center">
              <span>Backend Connection:</span>
              <span className="text-yellow-600 font-semibold">🔄 Testing</span>
            </div>
          </div>
          <div className="mt-8">
            <p className="text-gray-600 mb-4">
              This is a simplified test page. The full HVAC calculator is being built step by step.
            </p>
            <div className="space-x-4">
              <a 
                href="/test-components" 
                className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                View Components
              </a>
              <a 
                href="/test-flow" 
                className="inline-block bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Test Flow
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}