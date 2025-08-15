export default function FeatureSteps() {
  const steps = [
    {
      number: '01',
      title: 'Upload Blueprint',
      description: 'Drop your PDF blueprint or architectural drawing. Our AI automatically extracts rooms, dimensions, and building details.',
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      ),
    },
    {
      number: '02',
      title: 'Enter Project Location',
      description: 'Add your zip code and we automatically load local climate data and building codes for accurate calculations.',
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
    },
    {
      number: '03',
      title: 'Generate Manual J Report',
      description: 'Our system processes room layouts, calculates heat loads, and generates complete ACCA-compliant Manual J reports.',
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      ),
    },
    {
      number: '04',
      title: 'Download Results',
      description: 'Get professional reports with equipment sizing, duct layouts, and detailed load calculations ready for permits.',
      icon: (
        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
    },
  ]

  return (
    <section className="py-16 lg:py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-brand-700 mb-6">
            From blueprint to permit in 4 simple steps
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Our AI-powered workflow handles everything from load analysis to equipment sizing, 
            delivering professional reports in minutes instead of hours.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {steps.map((step, index) => (
            <div 
              key={index} 
              className="relative group animate-slide-up"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div className="card p-8 text-center h-full hover:scale-105 transition-transform duration-300">
                {/* Step number */}
                <div className="absolute -top-4 -right-4 w-8 h-8 bg-accent-orange text-white text-sm font-bold rounded-full flex items-center justify-center shadow-md">
                  {step.number}
                </div>

                {/* Icon */}
                <div className="w-16 h-16 bg-brand-100 rounded-xl flex items-center justify-center mx-auto mb-6 text-brand-700 group-hover:bg-brand-700 group-hover:text-white transition-colors duration-300">
                  {step.icon}
                </div>

                {/* Content */}
                <h3 className="text-xl font-semibold text-brand-700 mb-4">
                  {step.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {step.description}
                </p>
              </div>

              {/* Connector line (hidden on last item) */}
              {index < steps.length - 1 && (
                <div className="hidden lg:block absolute top-1/2 -right-4 w-8 h-0.5 bg-brand-100 z-10">
                  <div className="absolute right-0 top-1/2 transform -translate-y-1/2 w-2 h-2 bg-brand-500 rounded-full"></div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* CTA Section */}
        <div className="text-center mt-16">
          <div className="card p-8 max-w-2xl mx-auto">
            <h3 className="text-2xl font-semibold text-brand-700 mb-4">
              Ready to streamline your HVAC workflow?
            </h3>
            <p className="text-gray-600 mb-6">
              Join contractors who've upgraded from manual calculations to automated reports. Get accurate results in minutes, not hours.
            </p>
            <button className="btn-primary">
              Start Your Free Analysis
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}