import React from 'react';
import { CheckCircle, ArrowRight, Play } from 'lucide-react';

interface HowToStep {
  title: string;
  description: string;
  details?: string;
  image?: string;
}

interface HowToSectionProps {
  title: string;
  description: string;
  steps: HowToStep[];
  estimatedTime?: string;
  difficulty?: 'Easy' | 'Medium' | 'Advanced';
  tools?: string[];
  className?: string;
  showSchema?: boolean;
}

export default function HowToSection({
  title,
  description,
  steps,
  estimatedTime = "5 minutes",
  difficulty = "Easy",
  tools = ["Computer or mobile device", "Building plans or measurements"],
  className = "",
  showSchema = true
}: HowToSectionProps) {
  return (
    <>
      {/* HowTo Schema */}
      {showSchema && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "HowTo",
              "name": title,
              "description": description,
              "image": "https://autohvac.ai/how-to-image.png",
              "totalTime": `PT${estimatedTime.replace(/\D/g, '')}M`,
              "estimatedCost": {
                "@type": "MonetaryAmount",
                "currency": "USD",
                "value": "0"
              },
              "supply": tools.map(tool => ({
                "@type": "HowToSupply",
                "name": tool
              })),
              "tool": [
                {
                  "@type": "HowToTool",
                  "name": "AutoHVAC Calculator",
                  "url": "https://autohvac.ai/calculator"
                }
              ],
              "step": steps.map((step, index) => ({
                "@type": "HowToStep",
                "position": index + 1,
                "name": step.title,
                "text": step.description,
                "image": step.image || "https://autohvac.ai/step-image.png",
                "url": `https://autohvac.ai/calculator#step-${index + 1}`
              }))
            })
          }}
        />
      )}

      {/* HowTo Section */}
      <section 
        className={`py-8 md:py-12 ${className}`} 
        itemScope 
        itemType="https://schema.org/HowTo"
      >
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8 md:mb-12">
            <div className="flex items-center justify-center mb-4">
              <Play className="w-8 h-8 text-brand-600 mr-3" />
              <h2 className="text-2xl md:text-3xl font-bold text-gray-900" itemProp="name">
                {title}
              </h2>
            </div>
            <p className="text-lg text-gray-600 max-w-3xl mx-auto mb-6" itemProp="description">
              {description}
            </p>
            
            {/* Meta info */}
            <div className="flex flex-wrap items-center justify-center gap-4 md:gap-6 text-sm text-gray-600">
              <div className="flex items-center">
                <CheckCircle className="w-4 h-4 mr-2 text-green-600" />
                <span>Difficulty: <strong className="text-gray-900">{difficulty}</strong></span>
              </div>
              <div className="flex items-center">
                <CheckCircle className="w-4 h-4 mr-2 text-blue-600" />
                <span>Time: <strong className="text-gray-900" itemProp="totalTime">{estimatedTime}</strong></span>
              </div>
              <div className="flex items-center">
                <CheckCircle className="w-4 h-4 mr-2 text-purple-600" />
                <span>Cost: <strong className="text-gray-900">Free</strong></span>
              </div>
            </div>
          </div>

          {/* Tools/Requirements */}
          {tools.length > 0 && (
            <div className="bg-gray-50 rounded-lg p-6 mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">What You'll Need:</h3>
              <ul className="grid md:grid-cols-2 gap-2">
                {tools.map((tool, index) => (
                  <li key={index} className="flex items-center" itemProp="supply" itemScope itemType="https://schema.org/HowToSupply">
                    <CheckCircle className="w-4 h-4 text-green-600 mr-2 flex-shrink-0" />
                    <span className="text-gray-700" itemProp="name">{tool}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Steps */}
          <div className="space-y-6">
            {steps.map((step, index) => (
              <div
                key={index}
                className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow"
                itemProp="step"
                itemScope
                itemType="https://schema.org/HowToStep"
              >
                <div className="flex items-start">
                  <div className="flex-shrink-0 mr-4">
                    <div className="w-8 h-8 bg-brand-600 text-white rounded-full flex items-center justify-center font-bold text-sm">
                      {index + 1}
                    </div>
                  </div>
                  <div className="flex-grow">
                    <h3 className="text-xl font-semibold text-gray-900 mb-3" itemProp="name">
                      {step.title}
                    </h3>
                    <p className="text-gray-700 leading-relaxed mb-4" itemProp="text">
                      {step.description}
                    </p>
                    {step.details && (
                      <div className="bg-brand-50 border-l-4 border-brand-600 p-4 rounded">
                        <p className="text-sm text-gray-700">
                          <strong className="text-brand-900">Pro Tip:</strong> {step.details}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* CTA after steps */}
          <div className="mt-8 md:mt-12 text-center">
            <div className="bg-gradient-to-r from-brand-600 to-brand-700 rounded-xl p-6 md:p-8 text-white">
              <h3 className="text-xl md:text-2xl font-bold mb-3">
                Ready to Get Started?
              </h3>
              <p className="text-lg mb-6 opacity-95">
                Use our free calculator to get instant, professional HVAC load calculations.
              </p>
              <a
                href="/calculator"
                className="inline-flex items-center bg-white text-brand-700 px-6 py-3 rounded-lg font-semibold hover:shadow-xl transition-all hover:scale-105"
              >
                Start Free Calculation
                <ArrowRight className="ml-2 w-4 h-4" />
              </a>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

// Predefined HowTo sequences
export const HVAC_HOWTO_SEQUENCES = {
  tonnageCalculation: {
    title: "How to Calculate AC Tonnage for Your Home",
    description: "Follow these simple steps to determine the correct air conditioner size using professional ACCA Manual J methods.",
    estimatedTime: "5 minutes",
    difficulty: "Easy" as const,
    steps: [
      {
        title: "Gather Building Information",
        description: "Collect your home's square footage, ceiling heights, insulation details, window specifications, and orientation. You can find this information on building plans or by taking measurements.",
        details: "If you don't have exact insulation R-values, you can estimate based on your home's age and construction type."
      },
      {
        title: "Access the AutoHVAC Calculator",
        description: "Go to our free calculator and select 'Residential Load Calculation.' No signup required for your first calculation.",
        details: "The calculator works on any device and saves your progress automatically."
      },
      {
        title: "Input Building Details",
        description: "Enter your home's dimensions, construction details, and location. Our AI will guide you through each step with helpful explanations.",
        details: "Use the 'Quick Estimate' feature if you're missing some details - our AI can fill in reasonable assumptions."
      },
      {
        title: "Review and Generate Report",
        description: "Verify all information and click 'Calculate Load.' You'll receive a complete Manual J report with tonnage recommendations in 60 seconds.",
        details: "Your report includes room-by-room breakdowns and equipment sizing recommendations from top manufacturers."
      }
    ]
  },
  manualJProcess: {
    title: "How to Perform Manual J Load Calculations",
    description: "Learn the complete ACCA Manual J process for accurate residential HVAC load calculations.",
    estimatedTime: "10 minutes",
    difficulty: "Medium" as const,
    steps: [
      {
        title: "Collect Building Data",
        description: "Gather detailed information about construction materials, insulation levels, window specifications, and internal heat sources according to ACCA standards."
      },
      {
        title: "Calculate Heat Transfer",
        description: "Determine heat gain/loss through walls, windows, roof, and floors using ACCA-approved U-factors and temperature differentials."
      },
      {
        title: "Account for Internal Loads",
        description: "Add sensible and latent loads from occupants, lighting, appliances, and other internal heat sources."
      },
      {
        title: "Apply Safety Factors",
        description: "Include appropriate safety margins while avoiding oversizing, following ACCA guidelines for equipment selection."
      },
      {
        title: "Generate Equipment Recommendations",
        description: "Select properly sized equipment that matches your calculated loads and provides optimal comfort and efficiency."
      }
    ]
  }
};