import { blogContent as hvacLoadCalculations } from './hvac-load-calculations';
import { blogContent as manualJCalculationSoftware } from './manual-j-calculation-software';
import { blogContent as manualJVsRuleOfThumb } from './manual-j-vs-rule-of-thumb';
import { blogContent as acTonnageCalculator } from './ac-tonnage-calculator';
import { blogContent as howManyBtus } from './how-many-btus';
import { blogContent as heatPumpSizing } from './heat-pump-sizing';
import { blogContent as furnaceSizing2000SqFt } from './furnace-sizing-2000-sq-ft';
import { blogContent as hvacSizingChart } from './hvac-sizing-chart';
import { blogContent as blueprintToHvacCalculation } from './blueprint-to-hvac-calculation';
import { blogContent as hvacCalculationMistakes } from './hvac-calculation-mistakes';
import { blogContent as freeManualJCalculatorVsPaid } from './free-manual-j-calculator-vs-paid';
import { blogContent as emergencyAcReplacement } from './emergency-ac-replacement';

export interface BlogPost {
  title: string;
  slug: string;
  meta_description: string;
  content: string;
  category?: string;
  author?: string;
  publishDate?: string;
  readTime?: string;
}

// Registry of all blog posts
export const blogPosts: { [slug: string]: BlogPost } = {
  'hvac-load-calculations': hvacLoadCalculations,
  'manual-j-calculation-software': manualJCalculationSoftware,
  'manual-j-vs-rule-of-thumb': manualJVsRuleOfThumb,
  'ac-tonnage-calculator': acTonnageCalculator,
  'how-many-btus': howManyBtus,
  'heat-pump-sizing': heatPumpSizing,
  'furnace-sizing-2000-sq-ft': furnaceSizing2000SqFt,
  'hvac-sizing-chart': hvacSizingChart,
  'blueprint-to-hvac-calculation': blueprintToHvacCalculation,
  'hvac-calculation-mistakes': hvacCalculationMistakes,
  'free-manual-j-calculator-vs-paid': freeManualJCalculatorVsPaid,
  'emergency-ac-replacement': emergencyAcReplacement,
};

// Get all blog posts as an array
export const getAllBlogPosts = (): (BlogPost & { slug: string })[] => {
  return Object.entries(blogPosts).map(([slug, post]) => ({
    ...post,
    slug,
    category: getPostCategory(slug),
    author: 'AutoHVAC Team',
    publishDate: getPublishDate(slug),
    readTime: getReadTime(post.content),
  }));
};

// Get a single blog post by slug
export const getBlogPost = (slug: string): (BlogPost & { slug: string }) | null => {
  const post = blogPosts[slug];
  if (!post) return null;
  
  return {
    ...post,
    slug,
    category: getPostCategory(slug),
    author: 'AutoHVAC Team',
    publishDate: getPublishDate(slug),
    readTime: getReadTime(post.content),
  };
};

// Helper function to determine category based on slug
function getPostCategory(slug: string): string {
  if (slug.includes('manual-j')) return 'Manual J Calculations';
  if (slug.includes('tonnage') || slug.includes('sizing')) return 'HVAC Sizing';
  if (slug.includes('calculator') || slug.includes('software')) return 'HVAC Tools';
  return 'HVAC Guides';
}

// Helper function to get publish date (in real app, this would come from CMS)
function getPublishDate(slug: string): string {
  const dates: { [key: string]: string } = {
    'hvac-load-calculations': 'January 15, 2025',
    'manual-j-calculation-software': 'January 18, 2025',
    'manual-j-vs-rule-of-thumb': 'January 20, 2025',
    'ac-tonnage-calculator': 'January 22, 2025',
  };
  return dates[slug] || 'January 2025';
}

// Helper function to estimate read time
function getReadTime(content: string): string {
  const wordsPerMinute = 200;
  const wordCount = content.split(/\s+/).length;
  const minutes = Math.ceil(wordCount / wordsPerMinute);
  return `${minutes} min read`;
}

// Get related posts based on category
export const getRelatedPosts = (currentSlug: string, limit: number = 3): (BlogPost & { slug: string })[] => {
  const currentPost = getBlogPost(currentSlug);
  if (!currentPost) return [];
  
  const allPosts = getAllBlogPosts();
  const relatedPosts = allPosts
    .filter(post => post.slug !== currentSlug && post.category === currentPost.category)
    .slice(0, limit);
  
  // If not enough related posts in same category, fill with other posts
  if (relatedPosts.length < limit) {
    const otherPosts = allPosts
      .filter(post => post.slug !== currentSlug && post.category !== currentPost.category)
      .slice(0, limit - relatedPosts.length);
    relatedPosts.push(...otherPosts);
  }
  
  return relatedPosts;
};