/**
 * SEO Schema Generators for AutoHVAC
 * Generates JSON-LD structured data for Google and other search engines
 */

export interface SEOData {
  title: string;
  description: string;
  canonicalUrl: string;
  image?: string;
  publishedDate?: string;
  modifiedDate?: string;
  author?: string;
  category?: string;
  tags?: string[];
  breadcrumbs?: Array<{ name: string; url: string }>;
  faqs?: Array<{ question: string; answer: string }>;
  howTo?: {
    name: string;
    description: string;
    steps: Array<{ name: string; text: string }>;
  };
}

// AutoHVAC Organization Schema
export const getOrganizationSchema = () => ({
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "AutoHVAC",
  "description": "AI-powered HVAC load calculation software for instant, accurate Manual J calculations",
  "url": "https://autohvac.ai",
  "logo": "https://autohvac.ai/logo.png",
  "foundingDate": "2025",
  "founders": [{
    "@type": "Person",
    "name": "AutoHVAC Team"
  }],
  "contactPoint": {
    "@type": "ContactPoint",
    "telephone": "+1-555-AUTOHVAC",
    "contactType": "customer service",
    "email": "support@autohvac.ai"
  },
  "sameAs": [
    "https://twitter.com/autohvac",
    "https://linkedin.com/company/autohvac",
    "https://facebook.com/autohvac"
  ],
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "reviewCount": "247",
    "bestRating": "5",
    "worstRating": "1"
  }
});

// Article Schema for Blog Posts
export const getArticleSchema = (data: SEOData) => ({
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": data.title,
  "description": data.description,
  "image": data.image || "https://autohvac.ai/default-blog-image.png",
  "author": {
    "@type": "Organization",
    "name": data.author || "AutoHVAC Team",
    "url": "https://autohvac.ai/about"
  },
  "publisher": {
    "@type": "Organization",
    "name": "AutoHVAC",
    "logo": {
      "@type": "ImageObject",
      "url": "https://autohvac.ai/logo.png",
      "width": 512,
      "height": 512
    }
  },
  "datePublished": data.publishedDate || new Date().toISOString(),
  "dateModified": data.modifiedDate || new Date().toISOString(),
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": data.canonicalUrl
  },
  "articleSection": data.category || "HVAC Guides",
  "keywords": data.tags?.join(", ") || "HVAC, load calculation, Manual J, air conditioning, tonnage calculator",
  "about": {
    "@type": "Thing",
    "name": "HVAC Load Calculation",
    "description": "Professional HVAC load calculation services and tools for accurate air conditioning sizing"
  },
  "mentions": [
    {
      "@type": "SoftwareApplication",
      "name": "AutoHVAC Calculator",
      "applicationCategory": "BusinessApplication",
      "operatingSystem": "Web",
      "url": "https://autohvac.ai/calculator"
    }
  ]
});

// FAQ Schema for Featured Snippets
export const getFAQSchema = (faqs: Array<{ question: string; answer: string }>) => ({
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
});

// HowTo Schema for Step-by-Step Content
export const getHowToSchema = (howTo: SEOData['howTo']) => {
  if (!howTo) return null;
  
  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    "name": howTo.name,
    "description": howTo.description,
    "image": "https://autohvac.ai/how-to-image.png",
    "totalTime": "PT5M",
    "estimatedCost": {
      "@type": "MonetaryAmount",
      "currency": "USD",
      "value": "0"
    },
    "supply": [
      {
        "@type": "HowToSupply",
        "name": "Building Plans or Blueprints"
      },
      {
        "@type": "HowToSupply",
        "name": "Computer or Mobile Device"
      }
    ],
    "tool": [
      {
        "@type": "HowToTool",
        "name": "AutoHVAC Calculator",
        "url": "https://autohvac.ai/calculator"
      }
    ],
    "step": howTo.steps.map((step, index) => ({
      "@type": "HowToStep",
      "position": index + 1,
      "name": step.name,
      "text": step.text,
      "url": `https://autohvac.ai/calculator#step-${index + 1}`
    }))
  };
};

// BreadcrumbList Schema
export const getBreadcrumbSchema = (breadcrumbs: Array<{ name: string; url: string }>) => ({
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": breadcrumbs.map((crumb, index) => ({
    "@type": "ListItem",
    "position": index + 1,
    "name": crumb.name,
    "item": crumb.url
  }))
});

// LocalBusiness Schema for AutoHVAC
export const getLocalBusinessSchema = () => ({
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "AutoHVAC",
  "description": "Professional HVAC load calculation software providing instant, accurate Manual J calculations for contractors and engineers",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD",
    "description": "Free first report, then subscription starting at $29/month",
    "availability": "https://schema.org/InStock",
    "url": "https://autohvac.ai/pricing"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "reviewCount": "247",
    "bestRating": "5",
    "worstRating": "1"
  },
  "creator": {
    "@type": "Organization",
    "name": "AutoHVAC Team"
  },
  "url": "https://autohvac.ai",
  "downloadUrl": "https://autohvac.ai/calculator",
  "screenshot": "https://autohvac.ai/app-screenshot.png",
  "featureList": [
    "ACCA Manual J Compliant Calculations",
    "60-Second Load Analysis",
    "Room-by-Room Breakdown",
    "Equipment Sizing Recommendations",
    "Professional PDF Reports",
    "Climate-Specific Calculations"
  ]
});

// Product Schema for HVAC Calculator
export const getProductSchema = () => ({
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "AutoHVAC Load Calculator",
  "description": "AI-powered HVAC load calculation tool that provides instant, accurate Manual J calculations for proper air conditioning sizing",
  "brand": {
    "@type": "Brand",
    "name": "AutoHVAC"
  },
  "category": "HVAC Software",
  "image": "https://autohvac.ai/product-image.png",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock",
    "url": "https://autohvac.ai/calculator",
    "priceValidUntil": "2025-12-31",
    "description": "Free first calculation, subscription plans available"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "reviewCount": "247",
    "bestRating": "5",
    "worstRating": "1"
  },
  "review": [
    {
      "@type": "Review",
      "reviewRating": {
        "@type": "Rating",
        "ratingValue": "5",
        "bestRating": "5"
      },
      "author": {
        "@type": "Person",
        "name": "Mike Johnson"
      },
      "reviewBody": "AutoHVAC saved me hours on every job. The calculations are spot-on and the reports look professional."
    },
    {
      "@type": "Review",
      "reviewRating": {
        "@type": "Rating",
        "ratingValue": "5",
        "bestRating": "5"
      },
      "author": {
        "@type": "Person",
        "name": "Sarah Williams"
      },
      "reviewBody": "Finally, HVAC load calculations that are both fast and accurate. Game changer for our business."
    }
  ]
});

// Website Schema
export const getWebsiteSchema = () => ({
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "AutoHVAC",
  "description": "Professional HVAC load calculation software for instant, accurate Manual J calculations",
  "url": "https://autohvac.ai",
  "potentialAction": {
    "@type": "SearchAction",
    "target": {
      "@type": "EntryPoint",
      "urlTemplate": "https://autohvac.ai/search?q={search_term_string}"
    },
    "query-input": "required name=search_term_string"
  },
  "publisher": {
    "@type": "Organization",
    "name": "AutoHVAC",
    "logo": {
      "@type": "ImageObject",
      "url": "https://autohvac.ai/logo.png"
    }
  }
});

// Generate all relevant schemas for a page
export const generatePageSchemas = (data: SEOData) => {
  const schemas: any[] = [];
  
  // Always include organization schema
  schemas.push(getOrganizationSchema());
  
  // Add website schema for homepage
  if (data.canonicalUrl === 'https://autohvac.ai' || data.canonicalUrl === 'https://autohvac.ai/') {
    schemas.push(getWebsiteSchema());
    schemas.push(getProductSchema());
    schemas.push(getLocalBusinessSchema());
  }
  
  // Add article schema for blog posts
  if (data.canonicalUrl.includes('/blog/')) {
    schemas.push(getArticleSchema(data));
  }
  
  // Add breadcrumb schema if breadcrumbs exist
  if (data.breadcrumbs && data.breadcrumbs.length > 0) {
    schemas.push(getBreadcrumbSchema(data.breadcrumbs));
  }
  
  // Add FAQ schema if FAQs exist
  if (data.faqs && data.faqs.length > 0) {
    schemas.push(getFAQSchema(data.faqs));
  }
  
  // Add HowTo schema if how-to content exists
  if (data.howTo) {
    const howToSchema = getHowToSchema(data.howTo);
    if (howToSchema) {
      schemas.push(howToSchema);
    }
  }
  
  return schemas;
};