# Blog Content Directory

## IMPORTANT: Content files MUST go here, NOT in pages/blog/content/

### Why?
Next.js treats ANY file in the `pages` directory as a page component that needs to export a React component. 
Putting blog content data files in `pages/blog/content/` will cause build failures.

### Correct Structure:
```
/lib/blog-content/          <- Content files go HERE
  - manual-j-calculation-software.ts
  - hvac-load-calculations.ts
  - manual-j-vs-rule-of-thumb.ts
  - [other-content-files].ts

/pages/blog/                <- Page components go here
  - index.tsx               <- Blog listing page
  - [slug]/index.tsx        <- Individual blog post page

/pages/blog/components/     <- Blog UI components go here
  - BlogPost.tsx            <- Reusable blog components
```

### How to Add New Blog Content:

1. Create your content file in `/lib/blog-content/`:
```typescript
// /lib/blog-content/my-new-post.ts
export const blogContent = {
  title: "Your Title",
  slug: "my-new-post",
  meta_description: "SEO description",
  content: `Your HTML content here`
};
```

2. Import it in the blog page component:
```typescript
// /pages/blog/[slug]/index.tsx
import { blogContent } from '../../../lib/blog-content/my-new-post';
```

### Never Do This:
- ❌ Don't put `.ts` or `.js` files in `/pages/blog/content/`
- ❌ Don't put data files anywhere under `/pages/`
- ❌ Don't put non-component files in the pages directory

### Always Do This:
- ✅ Put content data in `/lib/blog-content/`
- ✅ Put page components in `/pages/blog/`
- ✅ Put reusable UI components in `/pages/blog/components/` or `/components/`

## For SEO Team
If you're adding new blog content, always add it to `/lib/blog-content/`, never to `/pages/`. 
This will prevent frontend build failures on deployment.