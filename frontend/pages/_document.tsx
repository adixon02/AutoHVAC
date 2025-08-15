import { Html, Head, Main, NextScript } from 'next/document';
import { getOrganizationSchema, getWebsiteSchema } from '../lib/seo-schemas';

export default function Document() {
  // Global schemas that should appear on every page
  const globalSchemas = [
    getOrganizationSchema(),
    getWebsiteSchema()
  ];

  return (
    <Html lang="en">
      <Head>
        {/* Global SEO Meta Tags */}
        <meta charSet="utf-8" />
        <meta name="format-detection" content="telephone=no" />
        <meta name="msapplication-tap-highlight" content="no" />
        <meta name="msapplication-config" content="/browserconfig.xml" />
        
        {/* Global Structured Data */}
        {globalSchemas.map((schema, index) => (
          <script
            key={`global-schema-${index}`}
            type="application/ld+json"
            dangerouslySetInnerHTML={{
              __html: JSON.stringify(schema, null, 2)
            }}
          />
        ))}
        
        {/* Critical CSS for Above-the-Fold Content */}
        <style jsx>{`
          /* Critical styles for faster loading */
          html {
            scroll-behavior: smooth;
          }
          
          body {
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
          }
          
          /* Prevent flash of unstyled content */
          .blog-content img {
            max-width: 100%;
            height: auto;
          }
          
          /* Improve CLS for images */
          img[width][height] {
            height: auto;
          }
        `}</style>
        
        {/* Google Analytics - Replace with your GA4 ID */}
        <script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID" />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              gtag('js', new Date());
              gtag('config', 'GA_MEASUREMENT_ID', {
                page_title: document.title,
                page_location: window.location.href,
                anonymize_ip: true,
                allow_google_signals: false,
                allow_ad_personalization_signals: false
              });
            `
          }}
        />
        
        {/* Microsoft Clarity - Optional */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function(c,l,a,r,i,t,y){
                c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
                t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
                y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
              })(window, document, "clarity", "script", "CLARITY_PROJECT_ID");
            `
          }}
        />
      </Head>
      <body>
        <Main />
        <NextScript />
        
        {/* Schema.org for Organization - Fallback */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebSite",
              "name": "AutoHVAC",
              "url": "https://autohvac.ai",
              "potentialAction": {
                "@type": "SearchAction",
                "target": "https://autohvac.ai/search?q={search_term_string}",
                "query-input": "required name=search_term_string"
              }
            })
          }}
        />
      </body>
    </Html>
  );
}