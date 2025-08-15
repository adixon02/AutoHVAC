import React, { useState } from 'react';
import { ChevronDown, ChevronUp, HelpCircle } from 'lucide-react';

interface FAQ {
  question: string;
  answer: string;
}

interface FAQSectionProps {
  faqs: FAQ[];
  title?: string;
  description?: string;
  className?: string;
  showSchema?: boolean;
}

export default function FAQSection({
  faqs,
  title = "Frequently Asked Questions",
  description,
  className = "",
  showSchema = true
}: FAQSectionProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggleFAQ = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  if (!faqs || faqs.length === 0) {
    return null;
  }

  return (
    <>
      {/* FAQ Schema for Featured Snippets */}
      {showSchema && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "FAQPage",
              "mainEntity": faqs.map(faq => ({
                "@type": "Question",
                "name": faq.question,
                "acceptedAnswer": {
                  "@type": "Answer",
                  "text": faq.answer
                }
              }))
            })
          }}
        />
      )}
      
      {/* FAQ Section */}
      <section className={`py-8 md:py-12 ${className}`} itemScope itemType="https://schema.org/FAQPage">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8 md:mb-12">
            <div className="flex items-center justify-center mb-4">
              <HelpCircle className="w-8 h-8 text-brand-600 mr-3" />
              <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
                {title}
              </h2>
            </div>
            {description && (
              <p className="text-lg text-gray-600 max-w-3xl mx-auto">
                {description}
              </p>
            )}
          </div>

          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <div
                key={index}
                className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow"
                itemScope
                itemProp="mainEntity"
                itemType="https://schema.org/Question"
              >
                <button
                  className="w-full px-6 py-4 text-left focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-inset"
                  onClick={() => toggleFAQ(index)}
                  aria-expanded={openIndex === index}
                  aria-controls={`faq-answer-${index}`}
                >
                  <div className="flex items-center justify-between">
                    <h3 
                      className="text-lg font-semibold text-gray-900 pr-4"
                      itemProp="name"
                    >
                      {faq.question}
                    </h3>
                    {openIndex === index ? (
                      <ChevronUp className="w-5 h-5 text-brand-600 flex-shrink-0" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0" />
                    )}
                  </div>
                </button>
                
                {openIndex === index && (
                  <div
                    id={`faq-answer-${index}`}
                    className="px-6 pb-4"
                    itemScope
                    itemProp="acceptedAnswer"
                    itemType="https://schema.org/Answer"
                  >
                    <div 
                      className="text-gray-700 leading-relaxed border-t border-gray-100 pt-4"
                      itemProp="text"
                      dangerouslySetInnerHTML={{ __html: faq.answer }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* CTA after FAQ section */}
          <div className="mt-8 md:mt-12 text-center">
            <div className="bg-gradient-to-r from-brand-50 to-brand-100 rounded-xl p-6 md:p-8 border border-brand-200">
              <h3 className="text-xl md:text-2xl font-bold text-gray-900 mb-3">
                Still Have Questions?
              </h3>
              <p className="text-gray-700 mb-6 text-base md:text-lg">
                Get instant, accurate HVAC load calculations with our free calculator.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <a
                  href="/calculator"
                  className="inline-flex items-center justify-center bg-brand-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-brand-700 transition-colors"
                >
                  Try Free Calculator
                </a>
                <a
                  href="/contact"
                  className="inline-flex items-center justify-center bg-white text-brand-600 px-6 py-3 rounded-lg font-semibold border border-brand-600 hover:bg-brand-50 transition-colors"
                >
                  Contact Support
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

// Predefined FAQ sets for different topics
export const HVAC_FAQ_SETS = {
  tonnage: [
    {
      question: "How do I calculate the right AC tonnage for my home?",
      answer: "AC tonnage calculation requires analyzing your home's total cooling load using ACCA Manual J procedures. This includes factors like square footage, insulation levels, window types, climate zone, orientation, and internal heat sources. Our <a href='/calculator' class='text-brand-600 hover:underline'>free calculator</a> provides precise tonnage recommendations in 60 seconds."
    },
    {
      question: "What size air conditioner do I need for a 1500 sq ft house?",
      answer: "A 1500 sq ft house typically needs 2.5-4 tons of cooling, but square footage alone isn't sufficient for accurate sizing. The actual tonnage depends on insulation quality, window efficiency, ceiling height, climate, and many other factors. Use our ACCA-compliant calculator for precise sizing."
    },
    {
      question: "Is bigger always better when sizing an AC unit?",
      answer: "No, oversized AC units cause problems including poor humidity control, short cycling, uneven temperatures, and higher energy costs. Proper sizing using Manual J calculations ensures optimal comfort, efficiency, and equipment longevity."
    }
  ],
  manualJ: [
    {
      question: "What is ACCA Manual J and why is it important?",
      answer: "ACCA Manual J is the industry standard for residential HVAC load calculations. It ensures proper equipment sizing by analyzing all factors affecting heating and cooling loads. Manual J compliance is required by many codes and helps avoid the problems of oversized or undersized equipment."
    },
    {
      question: "Can I do Manual J calculations manually?",
      answer: "While possible, manual Manual J calculations are extremely time-consuming and error-prone, typically taking 4-8 hours per home. Professional software like <a href='/calculator' class='text-brand-600 hover:underline'>AutoHVAC</a> provides the same accuracy in 60 seconds with automated data processing."
    },
    {
      question: "How accurate are AutoHVAC's Manual J calculations?",
      answer: "AutoHVAC uses the same ACCA Manual J 8th Edition procedures as expensive desktop software, with AI-powered automation for speed. Our calculations are fully compliant and match professional-grade tools while delivering results 100x faster."
    }
  ],
  general: [
    {
      question: "Why choose AutoHVAC over other HVAC calculation tools?",
      answer: "AutoHVAC combines professional-grade Manual J accuracy with unmatched speed and ease of use. We provide complete ACCA-compliant calculations, professional reports, and 60-second turnaround times at a fraction of the cost of traditional software."
    },
    {
      question: "Is AutoHVAC suitable for contractors and engineers?",
      answer: "Yes, AutoHVAC is designed for HVAC professionals who need fast, accurate load calculations. Our reports meet professional standards and can be used for permits, customer presentations, and equipment specification."
    },
    {
      question: "How much does AutoHVAC cost?",
      answer: "Your first report is completely free with no credit card required. After that, we offer flexible subscription plans starting at $29/month. <a href='/pricing' class='text-brand-600 hover:underline'>View our pricing options</a> for detailed information."
    }
  ]
};