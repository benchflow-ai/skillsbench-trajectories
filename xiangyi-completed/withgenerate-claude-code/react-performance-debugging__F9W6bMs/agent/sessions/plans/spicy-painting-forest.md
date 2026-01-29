# Performance Optimization Plan for E-Commerce App

## Executive Summary
The "ShopSlow" e-commerce application has identified performance bottlenecks across three key areas:
1. **API Response Times**: Sequential API calls and redundant data fetching
2. **Component Re-rendering**: Missing memoization causing excessive renders
3. **Bundle Size**: Heavy libraries (lodash, mathjs) unnecessarily bundled

## Root Cause Analysis

### Issue 1: API Response Slowness
**Current Flow (homepage/products):**
- `page.tsx` makes 3 sequential API calls (user, products, reviews)
- User sees blank page until all 3 complete
- `ProductList.getReviewCount()` filters through all reviews for each product on every render

**Impact:**
- Adding to cart is slow because `setCart` triggers parent re-render
- Homepage load is slow due to sequential API calls
- Compare page loads slowly due to library imports

### Issue 2: Excessive Component Re-rendering
**Current Issues:**
- `ProductCard` is not memoized - re-renders every time parent state changes
- `ProductList.filteredProducts` computed on every render (no useMemo)
- `handleAddToCart` is recreated on every render (no useCallback)
- `getReviewCount()` is called on every render for every product

**Impact:** When cart updates, all ProductCards re-render even if their props haven't changed

### Issue 3: Bundle Size
**Current Issues:**
- `compare/page.tsx` imports entire lodash (70KB) for 5 simple operations
- `compare/page.tsx` imports entire mathjs (180KB) for basic statistical functions
- No dynamic imports for heavy libraries
- `page.tsx` has `force-dynamic` disabling all caching

## Implementation Plan

### Phase 1: Fix API Response Times (Highest Priority)
**Files to modify:** `src/services/api-client.ts`, `src/app/page.tsx`

**Changes:**
1. Create new batched API endpoint that returns user + products + reviews in one call
2. Update `page.tsx` to use parallel requests (Promise.all) instead of sequential
3. Replace `force-dynamic` with appropriate cache headers
4. Pre-compute review counts in the API response to eliminate `getReviewCount()` filtering

**Files:**
- `src/services/api-client.ts` - Add new `fetchProductsWithDataFromService()` function
- `src/app/page.tsx` - Use parallel fetching, remove `force-dynamic`
- `src/components/ProductList.tsx` - Accept pre-computed `reviewCounts` prop instead of filtering

### Phase 2: Fix Excessive Re-rendering (High Priority)
**Files to modify:** `src/components/ProductList.tsx`, `src/components/ProductCard.tsx`

**Changes:**
1. Memoize `ProductCard` with React.memo()
2. Wrap filter/sort logic in useMemo()
3. Wrap `handleAddToCart` in useCallback()
4. Pre-compute review counts in API so no filtering needed

**Files:**
- `src/components/ProductCard.tsx` - Wrap with React.memo()
- `src/components/ProductList.tsx` - Add useMemo for filtering/sorting, useCallback for handlers

### Phase 3: Reduce Bundle Size (Medium Priority)
**Files to modify:** `src/app/compare/page.tsx`

**Changes:**
1. Replace lodash with native JavaScript for simple operations
2. Implement lightweight statistical functions instead of mathjs
3. Add dynamic import for any remaining heavy libraries
4. Keep all data-testid attributes and `performance.mark()` calls

**Files:**
- `src/app/compare/page.tsx` - Remove lodash/mathjs imports, implement lightweight versions

## Detailed Implementation

### 1. API Response Optimization

Create new batched endpoint:
```typescript
// Add to src/services/api-client.ts
export async function fetchProductsWithDataFromService() {
  const res = await fetch(`${API_BASE}/api/products`, {
    next: { revalidate: 60 } // Cache for 60 seconds instead of force-dynamic
  });
  if (!res.ok) throw new Error('Failed to fetch products data');
  return res.json(); // Returns { user, products, reviews, reviewCounts }
}
```

Update homepage to use parallel fetching where possible but prefer the new batched endpoint.

### 2. React Component Optimization

**ProductCard.tsx:**
- Wrap component with React.memo()
- Add custom comparison function to check product.id and isInCart only
- Keep performance.mark() call intact

**ProductList.tsx:**
- Add useMemo for filteredProducts (filter + sort)
- Add useCallback for handleAddToCart
- Receive reviewCounts as pre-computed prop instead of filtering
- Wrap ProductCard with React.memo() on export

### 3. Bundle Size Reduction

**compare/page.tsx:**
- Remove `import { ... } from 'lodash'` - use native Array methods
- Remove `import { ... } from 'mathjs'` - implement simple statistical functions
- Keep identical functionality and rendering
- Preserve all data-testid and visual output

**Lightweight implementations needed:**
```typescript
// Simple statistics functions to replace mathjs
const calculateMean = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length;
const calculateMedian = (arr) => {
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
};
// ... similar for variance, std dev, quantiles
```

## Verification Plan

### 1. Functionality Tests
- [ ] Homepage loads with user greeting, product list, and cart counter
- [ ] Adding products to cart updates cart count and disables button
- [ ] Search filtering works
- [ ] Sort by price/rating works
- [ ] Compare page loads and displays Overview tab
- [ ] Compare page Advanced Analysis tab renders with data-testid="advanced-content"

### 2. Performance Verification
- [ ] Chrome DevTools Network tab shows fewer/faster requests
- [ ] Homepage loads faster (parallel requests vs sequential)
- [ ] Adding to cart is responsive (no page freezing)
- [ ] Compare page loads faster (no heavy library loading)
- [ ] performance.mark() calls present in ProductCard render

### 3. Code Quality
- [ ] No console errors or warnings
- [ ] All data-testid attributes remain intact
- [ ] No components using test-ids removed
- [ ] performance.mark() still present in ProductCard

## Files to Modify
1. `src/services/api-client.ts` - Add batched fetch function
2. `src/app/page.tsx` - Use parallel/batched requests, remove force-dynamic
3. `src/components/ProductList.tsx` - Add memoization, useMemo, useCallback
4. `src/components/ProductCard.tsx` - Wrap with React.memo()
5. `src/app/compare/page.tsx` - Remove heavy libraries, implement lightweight versions

## Expected Outcomes
- **API Response Times:** 2-3x faster (parallel requests)
- **Cart Operations:** Instant (memoized components prevent re-renders)
- **Compare Page Load:** 50-70% faster (removed 250KB of libraries)
- **Bundle Size:** Reduced by ~250KB
- **Overall UX:** Smoother, more responsive application
