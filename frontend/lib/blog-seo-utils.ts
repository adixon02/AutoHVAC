import { BlogPost } from './blog-content';
import { SEOData } from './seo-schemas';

/**
 * Utility functions for extracting SEO data from blog content
 */

// Extract FAQ content from HTML
export const extractFAQs = (content: string): Array<{ question: string; answer: string }> => {
  const faqs: Array<{ question: string; answer: string }> = [];
  
  // Look for FAQ patterns in HTML content
  const faqPatterns = [
    // Pattern: <h3>Question</h3><p>Answer</p>
    /<h3[^>]*>([^<]+)<\/h3>\s*<p[^>]*>([^<]+)<\/p>/gi,
    // Pattern: <h4>Question</h4><p>Answer</p>
    /<h4[^>]*>([^<]+)<\/h4>\s*<p[^>]*>([^<]+)<\/p>/gi,
    // Pattern: Strong question followed by answer
    /<strong[^>]*>([^<]+\?[^<]*)<\/strong>[^<]*<p[^>]*>([^<]+)<\/p>/gi
  ];
  
  faqPatterns.forEach(pattern => {
    let match;
    while ((match = pattern.exec(content)) !== null) {
      const question = match[1].trim();
      const answer = match[2].trim();
      
      // Only add if it looks like a question
      if (question.includes('?') && answer.length > 20) {
        faqs.push({
          question: stripHTML(question),
          answer: stripHTML(answer)
        });
      }
    }
  });
  
  return faqs;
};

// Extract How-To steps from content
export const extractHowToSteps = (content: string, title: string): SEOData['howTo'] | undefined => {
  // Check if content contains step-by-step instructions
  const stepPatterns = [
    /step\s*(\d+)[^<]*<[^>]+>([^<]+)/gi,
    /<li[^>]*>\s*([^<]+step[^<]*)<\/li>/gi,
    /<h\d[^>]*>\s*step\s*(\d+)[^<]*([^<]+)<\/h\d>/gi
  ];
  
  const steps: Array<{ name: string; text: string }> = [];
  
  stepPatterns.forEach(pattern => {
    let match;
    while ((match = pattern.exec(content)) !== null) {
      const stepNumber = match[1] || steps.length + 1;
      const stepText = stripHTML(match[2] || match[1]).trim();
      
      if (stepText.length > 10) {
        steps.push({
          name: `Step ${stepNumber}`,
          text: stepText
        });
      }
    }
  });
  
  // Only return how-to data if we found actual steps
  if (steps.length >= 2) {
    return {
      name: title,
      description: `Step-by-step guide: ${title}`,
      steps
    };
  }
  
  return undefined;
};

// Generate SEO-friendly tags from content
export const generateTags = (title: string, content: string, category?: string): string[] => {
  const baseTags = ['HVAC', 'load calculation', 'Manual J', 'air conditioning'];
  
  // Add category-specific tags
  if (category) {
    if (category.toLowerCase().includes('tonnage')) {
      baseTags.push('AC tonnage', 'air conditioner sizing', 'BTU calculator');
    }
    if (category.toLowerCase().includes('manual j')) {
      baseTags.push('Manual J software', 'ACCA compliance', 'residential load calculation');
    }
    if (category.toLowerCase().includes('calculator')) {
      baseTags.push('HVAC calculator', 'load calculation software', 'cooling load');
    }
  }
  
  // Extract important keywords from title
  const titleWords = title.toLowerCase().split(/\s+/);
  const importantWords = titleWords.filter(word => 
    word.length > 3 && 
    !['the', 'and', 'for', 'with', 'your', 'this', 'that', 'what', 'how', 'why'].includes(word)
  );
  
  baseTags.push(...importantWords.slice(0, 5));
  
  // Extract key phrases from content (simple approach)
  const keyPhrases = [
    'ACCA Manual J',
    'cooling load',
    'heating load',
    'BTU per hour',
    'tons of cooling',
    'equipment sizing',
    'duct design',
    'energy efficiency'
  ];
  
  keyPhrases.forEach(phrase => {
    if (content.toLowerCase().includes(phrase.toLowerCase())) {
      baseTags.push(phrase);
    }
  });
  
  // Remove duplicates and limit to 15 tags
  return Array.from(new Set(baseTags)).slice(0, 15);
};

// Generate breadcrumbs for blog posts
export const generateBreadcrumbs = (slug: string, title: string): Array<{ name: string; url: string }> => {
  const breadcrumbs = [
    { name: 'Home', url: 'https://autohvac.ai' },
    { name: 'Blog', url: 'https://autohvac.ai/blog' }
  ];
  
  // Add category breadcrumb if applicable
  if (slug.includes('manual-j')) {
    breadcrumbs.push({ name: 'Manual J Guides', url: 'https://autohvac.ai/blog?category=manual-j' });
  } else if (slug.includes('calculator')) {
    breadcrumbs.push({ name: 'HVAC Calculators', url: 'https://autohvac.ai/blog?category=calculators' });
  } else if (slug.includes('tonnage') || slug.includes('sizing')) {
    breadcrumbs.push({ name: 'HVAC Sizing', url: 'https://autohvac.ai/blog?category=sizing' });
  }
  
  // Add current page
  breadcrumbs.push({ 
    name: truncateText(title, 50), 
    url: `https://autohvac.ai/blog/${slug}` 
  });
  
  return breadcrumbs;
};

// Convert blog post to SEO data
export const blogPostToSEOData = (post: BlogPost & { slug: string }): SEOData => {
  const faqs = extractFAQs(post.content);
  const howTo = extractHowToSteps(post.content, post.title);
  const tags = generateTags(post.title, post.content, post.category);
  const breadcrumbs = generateBreadcrumbs(post.slug, post.title);
  
  return {
    title: post.title,
    description: post.meta_description,
    canonicalUrl: `https://autohvac.ai/blog/${post.slug}`,
    image: `https://autohvac.ai/blog-images/${post.slug}-og.png`,
    publishedDate: parsePublishDate(post.publishDate),
    modifiedDate: new Date().toISOString(),
    author: post.author || 'AutoHVAC Team',
    category: post.category,
    tags,
    breadcrumbs,
    faqs: faqs.length > 0 ? faqs : undefined,
    howTo
  };
};

// Helper function to strip HTML tags
const stripHTML = (html: string): string => {
  return html.replace(/<[^>]*>/g, '').replace(/&[^;]+;/g, ' ').trim();
};

// Helper function to truncate text
const truncateText = (text: string, maxLength: number): string => {
  return text.length > maxLength ? text.substring(0, maxLength - 3) + '...' : text;
};

// Helper function to parse publish date
const parsePublishDate = (dateString?: string): string => {
  if (!dateString) return new Date().toISOString();
  
  try {
    // Convert "January 15, 2025" to ISO string
    const date = new Date(dateString);
    return date.toISOString();
  } catch {
    return new Date().toISOString();
  }
};

// Predefined FAQ sets for common topics
export const getPredefinedFAQs = (slug: string): Array<{ question: string; answer: string }> => {
  const faqSets: { [key: string]: Array<{ question: string; answer: string }> } = {
    'ac-tonnage-calculator': [
      {
        question: "How do I calculate AC tonnage for my home?",
        answer: "AC tonnage is calculated by determining your home's cooling load using ACCA Manual J procedures. This involves analyzing square footage, insulation levels, window types, climate zone, and 40+ other factors. Our AutoHVAC calculator provides instant, accurate tonnage calculations in 60 seconds."
      },
      {
        question: "What size AC do I need for a 2000 sq ft house?",
        answer: "A 2000 sq ft house typically needs 3-5 tons of cooling, but the exact size depends on insulation, windows, climate, and construction details. The rule of thumb of 1 ton per 400-600 sq ft is outdated. Use our free calculator for precise sizing based on ACCA Manual J standards."
      },
      {
        question: "Can I use square footage alone to size my AC?",
        answer: "No, square footage alone is insufficient for proper AC sizing. ACCA Manual J requires analyzing insulation R-values, window types, orientation, climate data, duct design, and many other factors. Using only square footage often results in oversized or undersized equipment."
      },
      {
        question: "What happens if my AC is oversized?",
        answer: "Oversized AC units cycle on and off frequently, leading to poor humidity control, increased energy costs, uneven temperatures, and shortened equipment life. Proper sizing using Manual J calculations ensures optimal comfort and efficiency."
      },
      {
        question: "Is AutoHVAC's calculator ACCA compliant?",
        answer: "Yes, AutoHVAC follows ACCA Manual J 8th Edition procedures for all load calculations. Our AI-powered calculator analyzes all required factors to provide compliant, accurate sizing recommendations that meet industry standards."
      }
    ],
    'manual-j-calculation-software': [
      {
        question: "What is Manual J calculation software?",
        answer: "Manual J calculation software automates the ACCA Manual J load calculation process, analyzing heating and cooling loads for residential buildings. Professional software like AutoHVAC ensures accurate, compliant calculations while saving significant time compared to manual methods."
      },
      {
        question: "Why do I need Manual J software instead of rules of thumb?",
        answer: "Manual J software provides accurate, site-specific calculations based on actual building characteristics, while rules of thumb often result in oversized or undersized equipment. Professional software ensures ACCA compliance and optimal system performance."
      },
      {
        question: "How accurate is AutoHVAC compared to other Manual J software?",
        answer: "AutoHVAC uses the same ACCA Manual J 8th Edition procedures as expensive desktop software but with AI-powered automation for faster results. Our calculations match professional-grade tools while delivering reports in 60 seconds instead of hours."
      }
    ]
  };
  
  return faqSets[slug] || [];
};