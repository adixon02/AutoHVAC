import { useState, useEffect } from 'react'

interface ROICalculatorProps {
  onGetStarted: () => void
}

export default function ROICalculator({ onGetStarted }: ROICalculatorProps) {
  const [quotesPerWeek, setQuotesPerWeek] = useState(10)
  const [currentTimePerQuote, setCurrentTimePerQuote] = useState(30)
  const [results, setResults] = useState({
    hoursPerWeek: 0,
    hoursPerMonth: 0,
    hoursSavedPerMonth: 0,
    moneySavedPerMonth: 0,
    autoHVACCost: 97,
    netSavings: 0,
    timeToROI: 0
  })

  useEffect(() => {
    // Calculate current time spent
    const hoursPerWeek = (quotesPerWeek * currentTimePerQuote) / 60
    const hoursPerMonth = hoursPerWeek * 4.33

    // With AutoHVAC (1 minute per quote)
    const autoHVACHoursPerMonth = (quotesPerWeek * 1 * 4.33) / 60
    const hoursSavedPerMonth = hoursPerMonth - autoHVACHoursPerMonth

    // Money calculations (assume $75/hour contractor time)
    const moneySavedPerMonth = hoursSavedPerMonth * 75
    const netSavings = moneySavedPerMonth - 97
    const timeToROI = 97 / moneySavedPerMonth

    setResults({
      hoursPerWeek,
      hoursPerMonth,
      hoursSavedPerMonth,
      moneySavedPerMonth,
      autoHVACCost: 97,
      netSavings,
      timeToROI
    })
  }, [quotesPerWeek, currentTimePerQuote])

  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-brand-600 to-brand-700 py-16 lg:py-24">
      {/* Background pattern for depth */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute top-20 -right-10 w-96 h-96 bg-white rounded-full mix-blend-screen filter blur-3xl"></div>
        <div className="absolute -bottom-10 -left-10 w-96 h-96 bg-brand-400 rounded-full mix-blend-multiply filter blur-3xl"></div>
      </div>
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-6">
            Calculate Your <span className="text-brand-200">ROI</span>
          </h2>
          <p className="text-xl text-brand-100 max-w-3xl mx-auto">
            See exactly how much time and money AutoHVAC saves your business every month.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-12 items-start">
          {/* Calculator Inputs */}
          <div className="card p-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">Your Current Workflow</h3>
            
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  How many Manual J quotes do you do per week?
                </label>
                <div className="relative">
                  <input
                    type="range"
                    min="1"
                    max="50"
                    value={quotesPerWeek}
                    onChange={(e) => setQuotesPerWeek(Number(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between text-sm text-gray-500 mt-1">
                    <span>1</span>
                    <span className="font-semibold text-brand-700">{quotesPerWeek} quotes/week</span>
                    <span>50+</span>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  How long does each Manual J calculation take you now?
                </label>
                <div className="relative">
                  <input
                    type="range"
                    min="10"
                    max="90"
                    step="5"
                    value={currentTimePerQuote}
                    onChange={(e) => setCurrentTimePerQuote(Number(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between text-sm text-gray-500 mt-1">
                    <span>10 min</span>
                    <span className="font-semibold text-brand-700">{currentTimePerQuote} minutes</span>
                    <span>90+ min</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-8 p-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600">
                <div className="flex justify-between mb-2">
                  <span>Time per week:</span>
                  <span className="font-semibold">{results.hoursPerWeek.toFixed(1)} hours</span>
                </div>
                <div className="flex justify-between">
                  <span>Time per month:</span>
                  <span className="font-semibold">{results.hoursPerMonth.toFixed(1)} hours</span>
                </div>
              </div>
            </div>
          </div>

          {/* Results */}
          <div className="card p-8 border-2 border-brand-200 bg-brand-50">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">Your AutoHVAC Savings</h3>
            
            <div className="space-y-6">
              {/* Time Savings */}
              <div className="bg-white p-6 rounded-lg border border-brand-200">
                <div className="flex items-center mb-4">
                  <div className="w-12 h-12 bg-brand-100 rounded-lg flex items-center justify-center mr-4">
                    <svg className="w-6 h-6 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-brand-700">{results.hoursSavedPerMonth.toFixed(0)} hours</div>
                    <div className="text-sm text-gray-600">saved per month</div>
                  </div>
                </div>
                <p className="text-sm text-gray-600">
                  That's {(results.hoursSavedPerMonth / 8).toFixed(1)} full workdays back in your schedule
                </p>
              </div>

              {/* Money Savings */}
              <div className="bg-white p-6 rounded-lg border border-brand-200">
                <div className="flex items-center mb-4">
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mr-4">
                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                    </svg>
                  </div>
                  <div>
                    <div className="text-3xl font-bold text-green-700">${results.moneySavedPerMonth.toFixed(0)}</div>
                    <div className="text-sm text-gray-600">time value saved per month</div>
                  </div>
                </div>
                <div className="space-y-2 text-sm text-gray-600">
                  <div className="flex justify-between">
                    <span>Time savings value:</span>
                    <span className="font-semibold">${results.moneySavedPerMonth.toFixed(0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>AutoHVAC cost:</span>
                    <span className="font-semibold">-$97</span>
                  </div>
                  <div className="border-t border-gray-200 pt-2"></div>
                  <div className="flex justify-between font-semibold text-green-700">
                    <span>Net monthly savings:</span>
                    <span>${results.netSavings.toFixed(0)}</span>
                  </div>
                </div>
              </div>

            </div>

            {/* CTA */}
            <div className="mt-8 p-6 bg-white rounded-lg border-2 border-brand-200 text-center">
              <h4 className="text-xl font-bold mb-2 text-gray-900">
                Why wait? Get your first report FREE
              </h4>
              <p className="text-gray-600 mb-4 text-sm font-medium">
                Zero risk. See the time savings yourself. No credit card required.
              </p>
              <button 
                onClick={onGetStarted}
                className="btn-primary w-full"
              >
                Get My Free Manual J Report
              </button>
            </div>
          </div>
        </div>

      </div>
      
      <style jsx>{`
        @keyframes blob {
          0% {
            transform: translate(0px, 0px) scale(1);
          }
          33% {
            transform: translate(30px, -50px) scale(1.1);
          }
          66% {
            transform: translate(-20px, 20px) scale(0.9);
          }
          100% {
            transform: translate(0px, 0px) scale(1);
          }
        }
        .animate-blob {
          animation: blob 7s infinite;
        }
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        .animation-delay-4000 {
          animation-delay: 4s;
        }
      `}</style>
    </section>
  )
}