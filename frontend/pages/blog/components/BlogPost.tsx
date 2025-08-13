import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Calendar, Clock, ArrowRight, CheckCircle, Star } from 'lucide-react';

interface BlogPostProps {
  title: string;
  content: string;
  author?: string;
  date?: string;
  readTime?: number;
  category?: string;
  tags?: string[];
}

// CTA Component for Free Report
const FreeReportCTA = () => (
  <div className="bg-gradient-to-r from-brand-600 to-brand-700 rounded-xl p-8 my-12 text-white">
    <div className="max-w-4xl mx-auto text-center">
      <h2 className="text-3xl font-bold mb-4">
        🎯 Get Your Free HVAC Load Report Today
      </h2>
      <p className="text-xl mb-6 opacity-95">
        Join thousands of HVAC professionals saving time and winning more jobs with AI-powered calculations.
      </p>
      
      <div className="bg-white/10 backdrop-blur rounded-lg p-6 mb-6">
        <h3 className="text-xl font-semibold mb-4">Your First Report Includes:</h3>
        <div className="grid md:grid-cols-2 gap-3 text-left max-w-2xl mx-auto">
          <div className="flex items-center">
            <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0" />
            <span>Complete ACCA Manual J calculations</span>
          </div>
          <div className="flex items-center">
            <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0" />
            <span>Room-by-room load breakdown</span>
          </div>
          <div className="flex items-center">
            <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0" />
            <span>Equipment sizing recommendations</span>
          </div>
          <div className="flex items-center">
            <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0" />
            <span>Professional PDF report</span>
          </div>
          <div className="flex items-center">
            <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0" />
            <span>60-second turnaround time</span>
          </div>
          <div className="flex items-center">
            <CheckCircle className="w-5 h-5 mr-2 flex-shrink-0" />
            <span>No credit card required</span>
          </div>
        </div>
      </div>
      
      <Link 
        href="/start-free"
        className="inline-flex items-center bg-white text-brand-700 px-8 py-4 rounded-lg font-bold text-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
      >
        Get Your Free Report Now
        <ArrowRight className="ml-2 w-5 h-5" />
      </Link>
      
      <p className="mt-4 text-sm opacity-75">
        No credit card required • Setup in 30 seconds • Cancel anytime
      </p>
    </div>
  </div>
);

// Inline CTA Component
const InlineCTA = ({ 
  title = "Ready to Calculate Your HVAC Load?",
  description = "Get accurate Manual J calculations in 60 seconds with our free calculator.",
  buttonText = "Start Free Calculation",
  buttonLink = "/calculator"
}) => (
  <div className="bg-gradient-to-r from-blue-50 to-sky-50 border-l-4 border-brand-600 p-6 my-8 rounded-lg">
    <h3 className="text-xl font-bold text-gray-900 mb-2">{title}</h3>
    <p className="text-gray-700 mb-4">{description}</p>
    <Link 
      href={buttonLink}
      className="inline-flex items-center bg-brand-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-brand-700 transition-colors"
    >
      {buttonText}
      <ArrowRight className="ml-2 w-4 h-4" />
    </Link>
  </div>
);

// Trust Badge Component
const TrustBadge = () => (
  <div className="bg-gray-50 rounded-lg p-6 my-8">
    <div className="flex items-center justify-center space-x-8 flex-wrap">
      <div className="flex items-center space-x-2">
        <CheckCircle className="w-6 h-6 text-green-600" />
        <span className="font-semibold">ACCA Compliant</span>
      </div>
      <div className="flex items-center space-x-2">
        <Star className="w-6 h-6 text-yellow-500" />
        <span className="font-semibold">4.8/5 Rating</span>
      </div>
      <div className="flex items-center space-x-2">
        <Clock className="w-6 h-6 text-blue-600" />
        <span className="font-semibold">60-Second Results</span>
      </div>
    </div>
  </div>
);

// Main Blog Post Component
export default function BlogPost({ 
  title, 
  content, 
  author = "AutoHVAC Team",
  date,
  readTime,
  category,
  tags = []
}: BlogPostProps) {
  
  // Process markdown content to HTML (you might want to use a markdown library)
  // For now, we'll render it as-is with basic styling
  
  return (
    <article className="max-w-4xl mx-auto px-4 py-12">
      {/* Article Header */}
      <header className="mb-12">
        {category && (
          <div className="mb-4">
            <span className="bg-brand-100 text-brand-800 text-sm font-medium px-3 py-1 rounded-full">
              {category}
            </span>
          </div>
        )}
        
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6 leading-tight">
          {title}
        </h1>
        
        <div className="flex items-center space-x-6 text-gray-600">
          {author && (
            <div className="flex items-center">
              <span className="font-medium">{author}</span>
            </div>
          )}
          {date && (
            <div className="flex items-center">
              <Calendar className="w-4 h-4 mr-2" />
              <span>{new Date(date).toLocaleDateString()}</span>
            </div>
          )}
          {readTime && (
            <div className="flex items-center">
              <Clock className="w-4 h-4 mr-2" />
              <span>{readTime} min read</span>
            </div>
          )}
        </div>
      </header>

      {/* Trust Badge */}
      <TrustBadge />

      {/* Article Content */}
      <div className="prose prose-lg max-w-none">
        {/* This is where your markdown content would be rendered */}
        {/* You'll want to use a markdown processor like react-markdown */}
        <div dangerouslySetInnerHTML={{ __html: content }} />
        
        {/* Example of inline CTAs that would be inserted throughout */}
        {/* These would be dynamically placed based on content length */}
      </div>

      {/* Tags */}
      {tags.length > 0 && (
        <div className="mt-12 pt-8 border-t">
          <div className="flex items-center flex-wrap gap-2">
            <span className="text-gray-600 font-medium">Tags:</span>
            {tags.map((tag, index) => (
              <Link
                key={index}
                href={`/blog/tag/${tag.toLowerCase().replace(' ', '-')}`}
                className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1 rounded-lg text-sm transition-colors"
              >
                {tag}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Final CTA - Free Report */}
      <FreeReportCTA />

      {/* Related Articles */}
      <div className="mt-12 pt-8 border-t">
        <h3 className="text-2xl font-bold mb-6">Related Articles</h3>
        <div className="grid md:grid-cols-3 gap-6">
          <Link href="/blog/acca-manual-j-guide" className="group">
            <div className="bg-gray-50 rounded-lg p-4 hover:shadow-lg transition-shadow">
              <h4 className="font-semibold text-gray-900 group-hover:text-brand-600 transition-colors">
                Understanding ACCA Manual J Standards
              </h4>
              <p className="text-sm text-gray-600 mt-2">
                Learn the fundamentals of ACCA-approved load calculations
              </p>
            </div>
          </Link>
          <Link href="/blog/hvac-sizing-mistakes" className="group">
            <div className="bg-gray-50 rounded-lg p-4 hover:shadow-lg transition-shadow">
              <h4 className="font-semibold text-gray-900 group-hover:text-brand-600 transition-colors">
                HVAC Sizing Mistakes to Avoid
              </h4>
              <p className="text-sm text-gray-600 mt-2">
                Common errors that cost contractors time and money
              </p>
            </div>
          </Link>
          <Link href="/blog/energy-efficiency-sizing" className="group">
            <div className="bg-gray-50 rounded-lg p-4 hover:shadow-lg transition-shadow">
              <h4 className="font-semibold text-gray-900 group-hover:text-brand-600 transition-colors">
                Energy Efficiency and Proper Sizing
              </h4>
              <p className="text-sm text-gray-600 mt-2">
                How right-sizing saves homeowners thousands
              </p>
            </div>
          </Link>
        </div>
      </div>
    </article>
  );
}

// Export CTA components for use in other places
export { FreeReportCTA, InlineCTA, TrustBadge };