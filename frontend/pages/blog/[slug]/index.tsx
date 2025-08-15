import React from 'react';
import Link from 'next/link';
import { ArrowLeft, Calendar, Clock, CheckCircle, Star, ArrowRight } from 'lucide-react';
import { useRouter } from 'next/router';
import NavBar from '../../../components/NavBar';
import SEOHead from '../../../components/SEOHead';
import { getBlogPost, getRelatedPosts } from '../../../lib/blog-content';
import { blogPostToSEOData, getPredefinedFAQs } from '../../../lib/blog-seo-utils';


// CTA Component for Free Report
const FreeReportCTA = () => (
  <div className="bg-gradient-to-r from-brand-600 to-brand-700 rounded-xl p-6 md:p-8 my-8 md:my-12 text-white">
    <div className="max-w-4xl mx-auto text-center">
      <h2 className="text-2xl md:text-3xl font-bold mb-4">
        🎯 Get Your Free HVAC Load Report Today
      </h2>
      <p className="text-lg md:text-xl mb-6 opacity-95 px-2">
        Join thousands of HVAC professionals saving time and winning more jobs with AI-powered calculations.
      </p>
      
      <div className="bg-white/10 backdrop-blur rounded-lg p-4 md:p-6 mb-6">
        <h3 className="text-lg md:text-xl font-semibold mb-4">Your First Report Includes:</h3>
        <div className="grid md:grid-cols-2 gap-2 md:gap-3 text-left max-w-2xl mx-auto text-sm md:text-base">
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
        className="inline-flex items-center bg-white text-brand-700 px-6 md:px-8 py-3 md:py-4 rounded-lg font-bold text-base md:text-lg hover:shadow-xl transition-all duration-300 hover:scale-105"
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
  <div className="bg-gradient-to-r from-brand-50 to-brand-100 border-l-4 border-brand-600 p-4 md:p-6 my-6 md:my-8 rounded-lg">
    <h3 className="text-lg md:text-xl font-bold text-gray-900 mb-2">{title}</h3>
    <p className="text-sm md:text-base text-gray-700 mb-4">{description}</p>
    <Link 
      href={buttonLink}
      className="inline-flex items-center bg-brand-600 text-white px-4 md:px-6 py-2 md:py-3 rounded-lg font-semibold text-sm md:text-base hover:bg-brand-700 transition-colors"
    >
      {buttonText}
      <ArrowRight className="ml-2 w-4 h-4" />
    </Link>
  </div>
);

// Trust Badge Component
const TrustBadge = () => (
  <div className="bg-gray-50 rounded-lg p-4 md:p-6 my-6 md:my-8">
    <div className="flex items-center justify-center space-x-4 md:space-x-8 flex-wrap gap-y-3">
      <div className="flex items-center space-x-2">
        <CheckCircle className="w-5 h-5 md:w-6 md:h-6 text-green-600" />
        <span className="font-semibold text-sm md:text-base">ACCA Compliant</span>
      </div>
      <div className="flex items-center space-x-2">
        <Star className="w-5 h-5 md:w-6 md:h-6 text-yellow-500" />
        <span className="font-semibold text-sm md:text-base">4.8/5 Rating</span>
      </div>
      <div className="flex items-center space-x-2">
        <Clock className="w-5 h-5 md:w-6 md:h-6 text-blue-600" />
        <span className="font-semibold text-sm md:text-base">60-Second Results</span>
      </div>
    </div>
  </div>
);

export default function BlogPost() {
  const router = useRouter();
  const { slug } = router.query;
  
  // Get the blog post content
  const blogContent = getBlogPost(slug as string);
  const relatedPosts = getRelatedPosts(slug as string, 3);
  
  if (!blogContent) {
    return (
      <>
        <SEOHead
          data={{
            title: "Article Not Found - AutoHVAC",
            description: "The article you're looking for doesn't exist or has been moved. Browse our HVAC guides and Manual J resources.",
            canonicalUrl: `https://autohvac.ai/blog/${slug}`
          }}
          noIndex={true}
        />
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-4xl font-bold mb-4">Article Not Found</h1>
            <p className="text-gray-600 mb-8">The article you're looking for doesn't exist or has been moved.</p>
            <Link href="/blog" className="text-brand-600 hover:underline">
              ← Back to Blog
            </Link>
          </div>
        </div>
      </>
    );
  }

  // Generate SEO data for the blog post
  const seoData = blogPostToSEOData(blogContent);
  
  // Add predefined FAQs if available
  const predefinedFAQs = getPredefinedFAQs(slug as string);
  if (predefinedFAQs.length > 0) {
    seoData.faqs = [...(seoData.faqs || []), ...predefinedFAQs];
  }

  return (
    <>
      <SEOHead
        data={seoData}
        ogType="article"
        twitterCard="summary_large_image"
      />
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
      <header className="max-w-4xl mx-auto px-4 py-6 md:py-8">
        <div className="mb-4">
          <span className="bg-brand-100 text-brand-800 text-sm font-medium px-3 py-1 rounded-full">
            {blogContent.category}
          </span>
        </div>
        
        <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-gray-900 mb-4 md:mb-6 leading-tight">
          {blogContent.title}
        </h1>
        
        <div className="flex flex-wrap items-center gap-x-4 md:gap-x-6 gap-y-2 text-gray-600 text-sm md:text-base">
          <span className="font-medium">{blogContent.author}</span>
          <div className="flex items-center">
            <Calendar className="w-4 h-4 mr-2" />
            <span>{blogContent.publishDate}</span>
          </div>
          <div className="flex items-center">
            <Clock className="w-4 h-4 mr-2" />
            <span>{blogContent.readTime}</span>
          </div>
        </div>
      </header>

      {/* Trust Badge */}
      <div className="max-w-4xl mx-auto px-4">
        <TrustBadge />
      </div>

      {/* Article Content */}
      <div className="max-w-4xl mx-auto px-4 py-6 md:py-8">
        <div 
          className="blog-content prose prose-base md:prose-lg max-w-none prose-headings:font-bold prose-h2:text-2xl md:prose-h2:text-3xl prose-h2:mt-8 md:prose-h2:mt-12 prose-h2:mb-4 md:prose-h2:mb-6 prose-h3:text-xl md:prose-h3:text-2xl prose-h3:mt-6 md:prose-h3:mt-8 prose-h3:mb-3 md:prose-h3:mb-4 prose-p:text-gray-700 prose-p:leading-relaxed prose-li:text-gray-700 prose-strong:text-gray-900 prose-a:text-brand-600 prose-a:no-underline hover:prose-a:underline prose-table:text-sm md:prose-table:text-base"
          dangerouslySetInnerHTML={{ __html: blogContent.content }}
        />
      </div>

      {/* Final CTA */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <FreeReportCTA />
      </div>

      {/* Related Articles */}
      <div className="max-w-4xl mx-auto px-4 py-8 md:py-12 border-t">
        <h3 className="text-xl md:text-2xl font-bold mb-4 md:mb-6">Related Articles</h3>
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-4 md:gap-6">
          {relatedPosts.map((post) => (
            <Link key={post.slug} href={`/blog/${post.slug}`} className="group">
              <div className="bg-gray-50 rounded-lg p-4 hover:shadow-lg transition-shadow">
                <div className="mb-2">
                  <span className="text-xs bg-brand-100 text-brand-700 px-2 py-1 rounded">
                    {post.category}
                  </span>
                </div>
                <h4 className="font-semibold text-gray-900 group-hover:text-brand-600 transition-colors line-clamp-2">
                  {post.title}
                </h4>
                <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                  {post.meta_description}
                </p>
                <div className="flex items-center mt-3 text-xs text-gray-500">
                  <Clock className="w-3 h-3 mr-1" />
                  <span>{post.readTime}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
      </article>
    </>
  );
}