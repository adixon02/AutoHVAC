import { useState } from 'react'

interface ContractorFAQProps {
  onGetStarted: () => void
}

export default function ContractorFAQ({ onGetStarted }: ContractorFAQProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  const contractorFAQs = [
    {
      question: "Is AutoHVAC ACCA approved and compliant?",
      answer: "Yes, AutoHVAC follows ACCA Manual J 8th Edition procedures and generates reports that meet professional standards. Our calculations use the same methodology as traditional software but with AI automation for speed and accuracy."
    },
    {
      question: "What about liability and professional insurance?",
      answer: "AutoHVAC generates professional Manual J reports that are suitable for permit applications and professional use. You maintain the same professional liability coverage as with any calculation tool. Our reports include all necessary technical details and calculations."
    },
    {
      question: "How accurate are the AI calculations compared to manual work?",
      answer: "Our AI is trained on thousands of professional Manual J calculations and follows exact ACCA procedures. Many contractors find our reports more consistent than manual calculations because AI eliminates human error in data entry and arithmetic."
    },
    {
      question: "Do I need training to use AutoHVAC?",
      answer: "No training required. If you understand Manual J concepts, you can use AutoHVAC immediately. The interface is intuitive - just upload your blueprint, enter the zip code, and get your report. Most contractors are productive within minutes."
    },
    {
      question: "What file formats can I upload?",
      answer: "We accept PDF blueprints, CAD files (DWG, DXF), and image files (JPG, PNG). Our AI can analyze any clear architectural drawing or floor plan. If you're unsure about a file, try the free report - there's no risk."
    },
    {
      question: "What if AutoHVAC doesn't work for my projects?",
      answer: "Your first report is completely free with no commitment. If AutoHVAC doesn't meet your needs, you haven't lost anything. Most contractors see immediate value, but there's zero risk to try it."
    },
    {
      question: "How does this compare to desktop software like Elite, CoolCalc, or others?",
      answer: "AutoHVAC offers the same ACCA-compliant calculations but 30x faster and works on any device. Desktop software requires manual data entry and takes 30+ minutes per calculation. AutoHVAC analyzes blueprints automatically in 60 seconds."
    },
    {
      question: "Can I use this on job sites without internet?",
      answer: "AutoHVAC works on any device with internet connection. For job sites, you can use your phone's hotspot or mobile data. Many contractors upload blueprints before heading to the site and have reports ready for customer meetings."
    },
    {
      question: "What's included in the $97/month subscription?",
      answer: "Unlimited Manual J calculations, blueprint analysis, professional reports, equipment sizing recommendations, and customer support. No per-report fees or hidden costs. Cancel anytime."
    },
    {
      question: "Is my project data secure and private?",
      answer: "Yes, all uploads are encrypted and secure. We don't share or sell your project data. Your blueprints and reports remain completely confidential. You can delete projects anytime."
    }
  ]

  return (
    <section className="py-16 lg:py-24 bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
            Questions? <span className="text-brand-700">We've got answers</span>
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Everything you need to know about AutoHVAC. Still have questions? Your first report is free - try it risk-free.
          </p>
        </div>

        <div className="space-y-4">
          {contractorFAQs.map((faq, index) => (
            <div 
              key={index} 
              className="card overflow-hidden transition-all duration-200 hover:shadow-md"
            >
              <button
                className="w-full p-6 text-left flex items-center justify-between focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-inset"
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
              >
                <h3 className="text-lg font-semibold text-gray-900 pr-4">
                  {faq.question}
                </h3>
                <div className="flex-shrink-0">
                  <svg 
                    className={`w-6 h-6 text-brand-600 transform transition-transform duration-200 ${
                      openIndex === index ? 'rotate-180' : ''
                    }`} 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>
              
              <div className={`transition-all duration-200 ease-in-out ${
                openIndex === index ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
              } overflow-hidden`}>
                <div className="px-6 pb-6">
                  <p className="text-gray-600 leading-relaxed">
                    {faq.answer}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Bottom CTA */}
        <div className="mt-16 text-center">
          <div className="bg-white rounded-xl border-2 border-brand-200 p-8 shadow-lg bg-gradient-to-br from-brand-50 to-white">
            <h3 className="text-2xl font-semibold text-gray-900 mb-4">
              Still have questions? Try it free
            </h3>
            <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
              The best way to see if AutoHVAC works for you is to try it. Upload any blueprint 
              and get a professional Manual J report in 60 seconds. Completely free, no strings attached.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <button 
                onClick={onGetStarted}
                className="btn-primary btn-lg"
              >
                Get My Free Manual J Report
              </button>
              <div className="flex items-center text-sm text-gray-500">
                <svg className="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                No credit card required
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}