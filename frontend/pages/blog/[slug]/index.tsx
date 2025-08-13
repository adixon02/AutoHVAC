import React from 'react';
import Link from 'next/link';
import { ArrowLeft, Calendar, Clock, CheckCircle, Star, ArrowRight } from 'lucide-react';
import { useRouter } from 'next/router';
import NavBar from '../../../components/NavBar';

// In production, this would parse your markdown files or fetch from CMS
import { blogContent } from '../content/manual-j-calculation-software';


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
  <div className="bg-gradient-to-r from-brand-50 to-brand-100 border-l-4 border-brand-600 p-6 my-8 rounded-lg">
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

export default function BlogPost() {
  const router = useRouter();
  const { slug } = router.query;
  // For demo, we're only showing the manual-j-calculation-software post
  if (slug && slug !== 'manual-j-calculation-software') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">Coming Soon</h1>
          <p className="text-gray-600 mb-8">This article is being written by our SEO team.</p>
          <Link href="/blog" className="text-purple-600 hover:underline">
            ← Back to Blog
          </Link>
        </div>
      </div>
    );
  }

  return (
    <>
      <NavBar />
      <article className="min-h-screen bg-white pt-16">
      {/* Navigation */}
      <div className="max-w-4xl mx-auto px-4 py-4">
        <Link 
          href="/blog" 
          className="inline-flex items-center text-gray-600 hover:text-brand-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Blog
        </Link>
      </div>

      {/* Article Header */}
      <header className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-4">
          <span className="bg-brand-100 text-brand-800 text-sm font-medium px-3 py-1 rounded-full">
            HVAC Software
          </span>
        </div>
        
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6 leading-tight">
          {blogContent.title}
        </h1>
        
        <div className="flex items-center space-x-6 text-gray-600">
          <span className="font-medium">AutoHVAC Team</span>
          <div className="flex items-center">
            <Calendar className="w-4 h-4 mr-2" />
            <span>January 20, 2025</span>
          </div>
          <div className="flex items-center">
            <Clock className="w-4 h-4 mr-2" />
            <span>12 min read</span>
          </div>
        </div>
      </header>

      {/* Trust Badge */}
      <div className="max-w-4xl mx-auto px-4">
        <TrustBadge />
      </div>

      {/* Article Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div 
          className="prose prose-lg max-w-none prose-headings:font-bold prose-h2:text-3xl prose-h2:mt-12 prose-h2:mb-6 prose-h3:text-2xl prose-h3:mt-8 prose-h3:mb-4 prose-p:text-gray-700 prose-p:leading-relaxed prose-li:text-gray-700 prose-strong:text-gray-900 prose-a:text-purple-600 prose-a:no-underline hover:prose-a:underline"
          dangerouslySetInnerHTML={{ __html: blogContent.content }}
        />
      </div>

      {/* Final CTA */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <FreeReportCTA />
      </div>

      {/* Related Articles */}
      <div className="max-w-4xl mx-auto px-4 py-12 border-t">
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
    </>
  );
}