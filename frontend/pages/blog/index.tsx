import React from 'react';
import Link from 'next/link';
import { Calendar, Clock, ArrowRight, BookOpen } from 'lucide-react';
import NavBar from '../../components/NavBar';
import SEOHead from '../../components/SEOHead';
import { getAllBlogPosts } from '../../lib/blog-content';

export default function BlogIndex() {
  const allPosts = getAllBlogPosts();
  
  // Mark the AC tonnage calculator as featured (our new dominant article)
  const featuredPost = allPosts.find(post => post.slug === 'ac-tonnage-calculator') || allPosts[0];
  const recentPosts = allPosts.filter(post => post.slug !== featuredPost?.slug);

  // SEO data for blog index page
  const seoData = {
    title: "HVAC Blog - Expert Load Calculation Guides & Manual J Resources",
    description: "Expert insights on HVAC load calculations, Manual J standards, AC tonnage sizing, and industry best practices. Free guides from AutoHVAC professionals.",
    canonicalUrl: "https://autohvac.ai/blog",
    image: "https://autohvac.ai/blog-og-image.png",
    tags: ["HVAC blog", "Manual J guides", "load calculation", "AC sizing", "HVAC professionals", "air conditioning"],
    breadcrumbs: [
      { name: "Home", url: "https://autohvac.ai" },
      { name: "Blog", url: "https://autohvac.ai/blog" }
    ],
    faqs: [
      {
        question: "What topics does the AutoHVAC blog cover?",
        answer: "Our blog covers HVAC load calculations, Manual J procedures, AC tonnage sizing, equipment selection, energy efficiency, and industry best practices for HVAC professionals."
      },
      {
        question: "Are the HVAC guides suitable for contractors?",
        answer: "Yes, our guides are written for HVAC professionals, contractors, and engineers who need accurate, practical information about load calculations and system sizing."
      },
      {
        question: "How often is new content published?",
        answer: "We regularly publish new HVAC guides, calculation tutorials, and industry insights to help professionals stay current with best practices and standards."
      }
    ]
  };

  return (
    <>
      <SEOHead
        data={seoData}
        ogType="website"
      />
      <NavBar />
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white pt-16">
      {/* Header */}
      <div className="bg-gradient-to-r from-brand-600 to-brand-700 text-white">
        <div className="max-w-7xl mx-auto px-4 py-16">
          <h1 className="text-4xl md:text-5xl font-bold mb-4">AutoHVAC Blog</h1>
          <p className="text-xl opacity-95">
            Expert insights on HVAC load calculations, Manual J standards, and industry best practices
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-12">
        {/* Featured Post */}
        {featuredPost && (
          <div className="mb-16">
            <h2 className="text-2xl font-bold mb-8 text-gray-900">Featured Article</h2>
            <Link href={`/blog/${featuredPost.slug}`}>
              <div className="group bg-white rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden">
                <div className="md:flex">
                  <div className="md:w-1/2 bg-gradient-to-br from-brand-100 to-brand-200 p-8 flex items-center justify-center">
                    <BookOpen className="w-32 h-32 text-brand-600 opacity-50" />
                  </div>
                  <div className="md:w-1/2 p-8">
                    <div className="mb-4">
                      <span className="bg-brand-100 text-brand-800 text-sm font-medium px-3 py-1 rounded-full">
                        {featuredPost.category}
                      </span>
                    </div>
                    <h3 className="text-2xl font-bold mb-3 text-gray-900 group-hover:text-brand-600 transition-colors">
                      {featuredPost.title}
                    </h3>
                    <p className="text-gray-600 mb-4 line-clamp-2">
                      {featuredPost.meta_description}
                    </p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <div className="flex items-center">
                          <Calendar className="w-4 h-4 mr-1" />
                          {featuredPost.publishDate}
                        </div>
                        <div className="flex items-center">
                          <Clock className="w-4 h-4 mr-1" />
                          {featuredPost.readTime}
                        </div>
                      </div>
                      <div className="flex items-center text-brand-600 font-semibold group-hover:translate-x-2 transition-transform">
                        Read More
                        <ArrowRight className="w-4 h-4 ml-1" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          </div>
        )}

        {/* Recent Posts */}
        <div>
          <h2 className="text-2xl font-bold mb-8 text-gray-900">Recent Articles</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {recentPosts.map((post) => (
              <Link key={post.slug} href={`/blog/${post.slug}`}>
                <article className="group bg-white rounded-lg shadow hover:shadow-xl transition-all duration-300 h-full">
                  <div className="p-6">
                    <div className="mb-3">
                      <span className="bg-gray-100 text-gray-700 text-xs font-medium px-2 py-1 rounded">
                        {post.category}
                      </span>
                    </div>
                    <h3 className="text-xl font-bold mb-3 text-gray-900 group-hover:text-brand-600 transition-colors line-clamp-2">
                      {post.title}
                    </h3>
                    <p className="text-gray-600 mb-4 line-clamp-3">
                      {post.meta_description}
                    </p>
                    <div className="flex items-center justify-between text-sm text-gray-500">
                      <div className="flex items-center space-x-3">
                        <div className="flex items-center">
                          <Calendar className="w-3 h-3 mr-1" />
                          {post.publishDate}
                        </div>
                        <div className="flex items-center">
                          <Clock className="w-3 h-3 mr-1" />
                          {post.readTime}
                        </div>
                      </div>
                    </div>
                  </div>
                </article>
              </Link>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-16 bg-gradient-to-r from-brand-600 to-brand-700 rounded-xl p-8 text-white text-center">
          <h2 className="text-3xl font-bold mb-4">
            Ready to Transform Your HVAC Business?
          </h2>
          <p className="text-xl mb-6 opacity-95">
            Join thousands of contractors using AutoHVAC for instant, accurate load calculations
          </p>
          <Link 
            href="/start-free"
            className="inline-flex items-center bg-white text-brand-700 px-8 py-4 rounded-lg font-bold text-lg hover:shadow-xl transition-all duration-300"
          >
            Get Your Free Report
            <ArrowRight className="ml-2 w-5 h-5" />
          </Link>
        </div>
      </div>
      </div>
    </>
  );
}