/**
 * SEO Utility Functions for AutoHVAC
 * Helper functions for sitemap generation, robots.txt, and other SEO needs
 */

import { getAllBlogPosts } from './blog-content';

// Site configuration
const SITE_CONFIG = {
  domain: 'https://autohvac.ai',
  siteName: 'AutoHVAC',
  defaultDescription: 'AI-powered HVAC load calculation software for instant, accurate Manual J calculations',
  defaultImage: 'https://autohvac.ai/og-default.png',
  twitterHandle: '@autohvac',
  fbAppId: '',
  googleSiteVerification: '',
  bingSiteVerification: ''
};

// Page priorities for sitemap
const PAGE_PRIORITIES = {
  homepage: 1.0,
  calculator: 0.9,
  blog: 0.8,
  blogPost: 0.7,
  pricing: 0.6,
  about: 0.5,
  contact: 0.5,
  legal: 0.3
};

// Update frequencies
const UPDATE_FREQUENCIES = {
  homepage: 'weekly',
  calculator: 'weekly', 
  blog: 'weekly',
  blogPost: 'monthly',
  static: 'yearly'
};

// Core site pages
const CORE_PAGES = [
  {
    url: '/',
    priority: PAGE_PRIORITIES.homepage,
    changefreq: UPDATE_FREQUENCIES.homepage,
    lastmod: new Date().toISOString()
  },
  {
    url: '/calculator',
    priority: PAGE_PRIORITIES.calculator,
    changefreq: UPDATE_FREQUENCIES.calculator,
    lastmod: new Date().toISOString()
  },
  {
    url: '/blog',
    priority: PAGE_PRIORITIES.blog,
    changefreq: UPDATE_FREQUENCIES.blog,
    lastmod: new Date().toISOString()
  },
  {
    url: '/pricing',
    priority: PAGE_PRIORITIES.pricing,
    changefreq: UPDATE_FREQUENCIES.static,
    lastmod: new Date().toISOString()
  },
  {
    url: '/about',
    priority: PAGE_PRIORITIES.about,
    changefreq: UPDATE_FREQUENCIES.static,
    lastmod: new Date().toISOString()
  },
  {
    url: '/contact',
    priority: PAGE_PRIORITIES.contact,
    changefreq: UPDATE_FREQUENCIES.static,
    lastmod: new Date().toISOString()
  },
  {
    url: '/privacy',
    priority: PAGE_PRIORITIES.legal,
    changefreq: UPDATE_FREQUENCIES.static,
    lastmod: new Date().toISOString()
  },
  {
    url: '/terms',
    priority: PAGE_PRIORITIES.legal,
    changefreq: UPDATE_FREQUENCIES.static,
    lastmod: new Date().toISOString()
  }
];

// Generate sitemap XML
export const generateSitemap = (): string => {
  const blogPosts = getAllBlogPosts();
  
  // Blog post URLs
  const blogUrls = blogPosts.map(post => ({
    url: `/blog/${post.slug}`,
    priority: PAGE_PRIORITIES.blogPost,
    changefreq: UPDATE_FREQUENCIES.blogPost,
    lastmod: new Date(post.publishDate || '2025-01-01').toISOString()
  }));
  
  const allUrls = [...CORE_PAGES, ...blogUrls];
  
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${allUrls.map(page => `  <url>
    <loc>${SITE_CONFIG.domain}${page.url}</loc>
    <lastmod>${page.lastmod}</lastmod>
    <changefreq>${page.changefreq}</changefreq>
    <priority>${page.priority}</priority>
  </url>`).join('\n')}
</urlset>`;
  
  return sitemap;
};

// Generate robots.txt
export const generateRobotsTxt = (): string => {
  const robotsTxt = `# AutoHVAC Robots.txt
# Generated automatically - do not edit manually

User-agent: *
Allow: /

# Sitemaps
Sitemap: ${SITE_CONFIG.domain}/sitemap.xml

# Disallow admin and API routes
Disallow: /api/
Disallow: /admin/
Disallow: /_next/
Disallow: /auth/
Disallow: /dashboard/
Disallow: /account/
Disallow: /analyzing/
Disallow: /payment/

# Allow specific API endpoints
Allow: /api/og/

# Block common crawl waste
Disallow: /*?*
Disallow: /*.json$
Disallow: /*.xml$
Disallow: /*_buildManifest.js
Disallow: /*_ssgManifest.js

# Crawl delay for good behavior
Crawl-delay: 1`;
  
  return robotsTxt;
};

// Generate structured data for homepage
export const getHomepageStructuredData = () => {
  return [
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      "name": "AutoHVAC",
      "url": SITE_CONFIG.domain,
      "logo": `${SITE_CONFIG.domain}/logo.png`,
      "description": SITE_CONFIG.defaultDescription,
      "foundingDate": "2025",
      "contactPoint": {
        "@type": "ContactPoint",
        "telephone": "+1-555-AUTOHVAC",
        "contactType": "customer service",
        "availableLanguage": "English"
      },
      "sameAs": [
        "https://twitter.com/autohvac",
        "https://linkedin.com/company/autohvac"
      ]
    },
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "AutoHVAC Load Calculator",
      "applicationCategory": "BusinessApplication",
      "operatingSystem": "Web",
      "description": "AI-powered HVAC load calculation software that provides instant, accurate Manual J calculations for professional contractors and engineers.",
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD",
        "description": "Free first report, subscription plans available"
      },
      "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": "4.8",
        "reviewCount": "247",
        "bestRating": "5"
      },
      "featureList": [
        "ACCA Manual J Compliant",
        "60-Second Calculations",
        "Professional PDF Reports",
        "Room-by-Room Analysis",
        "Equipment Recommendations"
      ]
    }
  ];
};

// SEO meta tag generator
export const generateMetaTags = ({
  title,
  description,
  canonicalUrl,
  image = SITE_CONFIG.defaultImage,
  noIndex = false,
  noFollow = false
}: {
  title: string;
  description: string;
  canonicalUrl: string;
  image?: string;
  noIndex?: boolean;
  noFollow?: boolean;
}) => {
  const fullTitle = title.includes('AutoHVAC') ? title : `${title} | AutoHVAC`;
  const truncatedTitle = fullTitle.length > 60 ? title.substring(0, 57) + '...' : fullTitle;
  const truncatedDescription = description.length > 160 ? description.substring(0, 157) + '...' : description;
  
  const robots = [];
  if (noIndex) robots.push('noindex');
  if (noFollow) robots.push('nofollow');
  if (robots.length === 0) robots.push('index', 'follow');
  robots.push('max-image-preview:large', 'max-snippet:-1', 'max-video-preview:-1');
  
  return {
    title: truncatedTitle,
    description: truncatedDescription,
    canonical: canonicalUrl,
    robots: robots.join(', '),
    openGraph: {
      title: truncatedTitle,
      description: truncatedDescription,
      url: canonicalUrl,
      image,
      siteName: SITE_CONFIG.siteName,
      type: 'website'
    },
    twitter: {
      card: 'summary_large_image',
      site: SITE_CONFIG.twitterHandle,
      creator: SITE_CONFIG.twitterHandle,
      title: truncatedTitle,
      description: truncatedDescription,
      image
    }
  };
};

// Generate Open Graph image URL
export const generateOGImageUrl = (title: string, description?: string) => {
  const params = new URLSearchParams({
    title,
    ...(description && { description })
  });
  
  return `${SITE_CONFIG.domain}/api/og?${params.toString()}`;
};

// Validate SEO data
export const validateSEOData = (data: any) => {
  const errors: string[] = [];
  
  if (!data.title) errors.push('Title is required');
  if (!data.description) errors.push('Description is required');
  if (!data.canonicalUrl) errors.push('Canonical URL is required');
  
  if (data.title && data.title.length > 60) {
    errors.push('Title should be under 60 characters');
  }
  
  if (data.description && data.description.length > 160) {
    errors.push('Description should be under 160 characters');
  }
  
  if (data.canonicalUrl && !data.canonicalUrl.startsWith('http')) {
    errors.push('Canonical URL must be absolute');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};

// Get page type from URL
export const getPageType = (url: string): string => {
  if (url === '/' || url === '') return 'homepage';
  if (url.startsWith('/blog/') && url !== '/blog') return 'blogPost';
  if (url === '/blog') return 'blog';
  if (url === '/calculator') return 'calculator';
  if (url === '/pricing') return 'pricing';
  if (url.includes('privacy') || url.includes('terms')) return 'legal';
  return 'page';
};

// Generate breadcrumbs for any page
export const generateBreadcrumbs = (url: string, title?: string) => {
  const breadcrumbs = [{ name: 'Home', url: SITE_CONFIG.domain }];
  
  const pathSegments = url.split('/').filter(Boolean);
  let currentPath = '';
  
  pathSegments.forEach((segment, index) => {
    currentPath += '/' + segment;
    
    if (segment === 'blog') {
      breadcrumbs.push({ name: 'Blog', url: `${SITE_CONFIG.domain}/blog` });
    } else if (pathSegments[index - 1] === 'blog' && title) {
      breadcrumbs.push({ 
        name: title.length > 50 ? title.substring(0, 47) + '...' : title,
        url: `${SITE_CONFIG.domain}${currentPath}`
      });
    } else {
      const name = segment.charAt(0).toUpperCase() + segment.slice(1).replace('-', ' ');
      breadcrumbs.push({ name, url: `${SITE_CONFIG.domain}${currentPath}` });
    }
  });
  
  return breadcrumbs;
};

export { SITE_CONFIG, PAGE_PRIORITIES, UPDATE_FREQUENCIES };