import React from 'react';
import Link from 'next/link';
import { Calendar, Clock, ArrowRight, BookOpen } from 'lucide-react';

// Mock blog posts data - in production, this would come from your CMS or markdown files
const blogPosts = [
  {
    slug: 'manual-j-calculation-software',
    title: 'Manual J Calculation Software: AI-Powered HVAC Load Calculator (2025)',
    description: 'Get ACCA Manual J calculations in 60 seconds with AutoHVAC\'s AI-powered software. Upload blueprints, get permit-ready reports at $99/month.',
    author: 'AutoHVAC Team',
    date: '2025-01-20',
    readTime: 12,
    category: 'HVAC Software',
    featured: true,
    image: '/images/blog/manual-j-software-hero.webp'
  },
  {
    slug: 'hvac-sizing-mistakes',
    title: 'Top 10 HVAC Sizing Mistakes That Cost You Money',
    description: 'Learn the most common HVAC sizing errors and how to avoid them. Save thousands on energy bills with proper load calculations.',
    author: 'AutoHVAC Team',
    date: '2025-01-18',
    readTime: 8,
    category: 'Best Practices',
    featured: false
  },
  {
    slug: 'acca-manual-j-guide',
    title: 'Understanding ACCA Manual J Standards: Complete Guide',
    description: 'Everything you need to know about ACCA Manual J standards for residential load calculations. Industry requirements explained.',
    author: 'AutoHVAC Team',
    date: '2025-01-15',
    readTime: 10,
    category: 'Education',
    featured: false
  }
];

import NavBar from '../../components/NavBar';

export default function BlogIndex() {
  const featuredPost = blogPosts.find(post => post.featured);
  const recentPosts = blogPosts.filter(post => !post.featured);

  return (
    <>
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
                      {featuredPost.description}
                    </p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <div className="flex items-center">
                          <Calendar className="w-4 h-4 mr-1" />
                          {new Date(featuredPost.date).toLocaleDateString()}
                        </div>
                        <div className="flex items-center">
                          <Clock className="w-4 h-4 mr-1" />
                          {featuredPost.readTime} min read
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
                      {post.description}
                    </p>
                    <div className="flex items-center justify-between text-sm text-gray-500">
                      <div className="flex items-center space-x-3">
                        <div className="flex items-center">
                          <Calendar className="w-3 h-3 mr-1" />
                          {new Date(post.date).toLocaleDateString()}
                        </div>
                        <div className="flex items-center">
                          <Clock className="w-3 h-3 mr-1" />
                          {post.readTime} min
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