import Head from 'next/head';
import { SEOData, generatePageSchemas } from '../lib/seo-schemas';

interface SEOHeadProps {
  data: SEOData;
  noIndex?: boolean;
  noFollow?: boolean;
  ogType?: 'website' | 'article' | 'product';
  twitterCard?: 'summary' | 'summary_large_image';
  locale?: string;
  alternateLanguages?: Array<{ hreflang: string; href: string }>;
}

export default function SEOHead({
  data,
  noIndex = false,
  noFollow = false,
  ogType = 'website',
  twitterCard = 'summary_large_image',
  locale = 'en_US',
  alternateLanguages = []
}: SEOHeadProps) {
  const {
    title,
    description,
    canonicalUrl,
    image = 'https://autohvac.ai/og-default.png',
    publishedDate,
    modifiedDate,
    author,
    category,
    tags
  } = data;

  // Generate JSON-LD schemas
  const schemas = generatePageSchemas(data);
  
  // Create robots meta content
  const robotsContent = [];
  if (noIndex) robotsContent.push('noindex');
  if (noFollow) robotsContent.push('nofollow');
  if (robotsContent.length === 0) {
    robotsContent.push('index', 'follow');
  }
  robotsContent.push('max-image-preview:large', 'max-snippet:-1', 'max-video-preview:-1');
  
  // Ensure title includes brand and is under 60 characters
  const fullTitle = title.includes('AutoHVAC') ? title : `${title} | AutoHVAC`;
  const truncatedTitle = fullTitle.length > 60 ? `${title} | AutoHVAC` : fullTitle;
  
  // Ensure description is under 160 characters
  const truncatedDescription = description.length > 160 
    ? description.substring(0, 157) + '...' 
    : description;

  return (
    <Head>
      {/* Basic Meta Tags */}
      <title>{truncatedTitle}</title>
      <meta name="description" content={truncatedDescription} />
      <meta name="robots" content={robotsContent.join(', ')} />
      <link rel="canonical" href={canonicalUrl} />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      
      {/* Article-specific meta tags */}
      {publishedDate && (
        <meta property="article:published_time" content={publishedDate} />
      )}
      {modifiedDate && (
        <meta property="article:modified_time" content={modifiedDate} />
      )}
      {author && <meta name="author" content={author} />}
      {category && <meta property="article:section" content={category} />}
      {tags && tags.length > 0 && (
        <meta name="keywords" content={tags.join(', ')} />
      )}
      
      {/* Open Graph Tags */}
      <meta property="og:type" content={ogType} />
      <meta property="og:title" content={truncatedTitle} />
      <meta property="og:description" content={truncatedDescription} />
      <meta property="og:url" content={canonicalUrl} />
      <meta property="og:image" content={image} />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />
      <meta property="og:image:alt" content={truncatedTitle} />
      <meta property="og:site_name" content="AutoHVAC" />
      <meta property="og:locale" content={locale} />
      
      {/* Article Open Graph Tags */}
      {ogType === 'article' && (
        <>
          {publishedDate && (
            <meta property="article:published_time" content={publishedDate} />
          )}
          {modifiedDate && (
            <meta property="article:modified_time" content={modifiedDate} />
          )}
          {author && <meta property="article:author" content={author} />}
          {category && <meta property="article:section" content={category} />}
          {tags && tags.map(tag => (
            <meta key={tag} property="article:tag" content={tag} />
          ))}
        </>
      )}
      
      {/* Twitter Card Tags */}
      <meta name="twitter:card" content={twitterCard} />
      <meta name="twitter:site" content="@autohvac" />
      <meta name="twitter:creator" content="@autohvac" />
      <meta name="twitter:title" content={truncatedTitle} />
      <meta name="twitter:description" content={truncatedDescription} />
      <meta name="twitter:image" content={image} />
      <meta name="twitter:image:alt" content={truncatedTitle} />
      
      {/* Additional Twitter Tags for Large Image Cards */}
      {twitterCard === 'summary_large_image' && (
        <>
          <meta name="twitter:image:width" content="1200" />
          <meta name="twitter:image:height" content="630" />
        </>
      )}
      
      {/* Alternate Language Links */}
      {alternateLanguages.map(({ hreflang, href }) => (
        <link key={hreflang} rel="alternate" hrefLang={hreflang} href={href} />
      ))}
      
      {/* Additional SEO Meta Tags */}
      <meta name="theme-color" content="#2563EB" />
      <meta name="msapplication-TileColor" content="#2563EB" />
      <meta name="application-name" content="AutoHVAC" />
      <meta name="apple-mobile-web-app-title" content="AutoHVAC" />
      <meta name="apple-mobile-web-app-capable" content="yes" />
      <meta name="apple-mobile-web-app-status-bar-style" content="default" />
      
      {/* Favicon and Touch Icons */}
      <link rel="icon" type="image/x-icon" href="/favicon.ico" />
      <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
      <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
      <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
      <link rel="icon" type="image/png" sizes="192x192" href="/android-chrome-192x192.png" />
      <link rel="icon" type="image/png" sizes="512x512" href="/android-chrome-512x512.png" />
      
      {/* DNS Prefetch for Performance */}
      <link rel="dns-prefetch" href="//fonts.googleapis.com" />
      <link rel="dns-prefetch" href="//www.google-analytics.com" />
      <link rel="dns-prefetch" href="//connect.facebook.net" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      
      {/* JSON-LD Structured Data */}
      {schemas.map((schema, index) => (
        <script
          key={`schema-${index}`}
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify(schema, null, 2)
          }}
        />
      ))}
      
      {/* Preload Critical Resources */}
      <link rel="preload" href="/fonts/inter-var.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
      
      {/* Security Headers */}
      <meta httpEquiv="X-Content-Type-Options" content="nosniff" />
      <meta httpEquiv="X-Frame-Options" content="DENY" />
      <meta httpEquiv="X-XSS-Protection" content="1; mode=block" />
      <meta httpEquiv="Referrer-Policy" content="strict-origin-when-cross-origin" />
      
      {/* Additional Meta for Blog Articles */}
      {ogType === 'article' && (
        <>
          <meta name="news_keywords" content={tags?.join(', ') || 'HVAC, load calculation, Manual J'} />
          <meta name="syndication-source" content={canonicalUrl} />
          <meta name="original-source" content={canonicalUrl} />
        </>
      )}
    </Head>
  );
}