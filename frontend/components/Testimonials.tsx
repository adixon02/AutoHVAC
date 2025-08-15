import { useState, useEffect } from 'react'

export default function Testimonials() {
  const [currentIndex, setCurrentIndex] = useState(0)

  const testimonials = [
    {
      name: 'Mike Rodriguez',
      title: 'HVAC Contractor',
      company: 'Rodriguez Mechanical',
      location: 'Phoenix, AZ',
      quote: 'AutoHVAC cut my bid prep time from 4 hours to 15 minutes. The calculations are spot-on and the reports look professional. My permit office loves the clean documentation.',
      avatar: '👨‍🔧',
      rating: 5,
    },
    {
      name: 'Sarah Chen',
      title: 'Mechanical Engineer',
      company: 'Chen Engineering',
      location: 'Seattle, WA',
      quote: 'Finally, a tool that understands real-world HVAC design. The Manual J calculations match our in-house engineering, but AutoHVAC delivers them in seconds instead of hours.',
      avatar: '👩‍💼',
      rating: 5,
    },
    {
      name: 'Tom Anderson',
      title: 'Building Inspector',
      company: 'City of Denver',
      location: 'Denver, CO',
      quote: 'Contractors using AutoHVAC submit cleaner, more accurate plans. The code compliance features mean fewer revision cycles and faster permit approvals.',
      avatar: '👨‍💻',
      rating: 5,
    },
    {
      name: 'Jessica Martinez',
      title: 'General Contractor',
      company: 'Martinez Construction',
      location: 'Austin, TX',
      quote: 'As a GC, I need my subs to be fast and accurate. AutoHVAC helps my HVAC guys deliver both. Projects move smoother when everyone has the right info upfront.',
      avatar: '👩‍🏗️',
      rating: 5,
    },
  ]

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentIndex((prevIndex) => (prevIndex + 1) % testimonials.length)
    }, 5000)
    
    return () => clearInterval(timer)
  }, [testimonials.length])

  return (
    <section className="py-16 lg:py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-brand-700 mb-6">
            Trusted by HVAC professionals
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            See what contractors, engineers, and inspectors are saying about AutoHVAC
          </p>
        </div>

        <div className="relative max-w-4xl mx-auto">
          {/* Main testimonial card */}
          <div className="card p-8 lg:p-12 text-center animate-fade-in">
            <div className="flex justify-center mb-6">
              {[...Array(testimonials[currentIndex].rating)].map((_, i) => (
                <svg
                  key={i}
                  className="w-6 h-6 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              ))}
            </div>

            <blockquote className="text-xl lg:text-2xl text-gray-700 mb-8 leading-relaxed">
              "{testimonials[currentIndex].quote}"
            </blockquote>

            <div className="flex items-center justify-center">
              <div className="text-6xl mr-4">
                {testimonials[currentIndex].avatar}
              </div>
              <div className="text-left">
                <div className="font-semibold text-brand-700 text-lg">
                  {testimonials[currentIndex].name}
                </div>
                <div className="text-gray-600">
                  {testimonials[currentIndex].title}
                </div>
                <div className="text-gray-500 text-sm">
                  {testimonials[currentIndex].company} • {testimonials[currentIndex].location}
                </div>
              </div>
            </div>
          </div>

          {/* Navigation dots */}
          <div className="flex justify-center mt-8 space-x-2">
            {testimonials.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentIndex(index)}
                className={`w-3 h-3 rounded-full transition-colors duration-200 ${
                  index === currentIndex ? 'bg-brand-700' : 'bg-gray-300'
                }`}
                aria-label={`Go to testimonial ${index + 1}`}
              />
            ))}
          </div>

          {/* Navigation arrows */}
          <button
            onClick={() => setCurrentIndex((prev) => (prev - 1 + testimonials.length) % testimonials.length)}
            className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-4 w-12 h-12 bg-white rounded-full shadow-lg flex items-center justify-center text-brand-700 hover:bg-brand-50 transition-colors duration-200"
            aria-label="Previous testimonial"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <button
            onClick={() => setCurrentIndex((prev) => (prev + 1) % testimonials.length)}
            className="absolute right-0 top-1/2 transform -translate-y-1/2 translate-x-4 w-12 h-12 bg-white rounded-full shadow-lg flex items-center justify-center text-brand-700 hover:bg-brand-50 transition-colors duration-200"
            aria-label="Next testimonial"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {/* Stats section */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 mt-16 max-w-4xl mx-auto">
          {[
            { number: '2,500+', label: 'Projects Completed' },
            { number: '98%', label: 'Permit Approval Rate' },
            { number: '4.2hrs', label: 'Average Time Saved' },
            { number: '50+', label: 'States Supported' },
          ].map((stat, index) => (
            <div key={index} className="text-center">
              <div className="text-3xl lg:text-4xl font-bold text-brand-700 mb-2">
                {stat.number}
              </div>
              <div className="text-gray-600 text-sm">
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}