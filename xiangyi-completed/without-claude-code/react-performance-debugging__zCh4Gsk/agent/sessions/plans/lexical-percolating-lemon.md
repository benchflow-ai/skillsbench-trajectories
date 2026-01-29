# E-Commerce Performance Optimization Plan

## Performance Issues Identified

### 1. **Sequential Data Fetching (Home Page & API Routes)**
- **Problem**: Home page makes 3 sequential API calls instead of parallel
  - `fetchUserFromService()` → `fetchProductsFromService()` → `fetchReviewsFromService()`
  - This adds latency unnecessarily
- **Impact**: High - each API call adds latency in sequence
- **Solution**: Use `Promise.all()` to parallelize independent fetches

### 2. **Excessive Caching Disabled (force-dynamic)**
- **Problem**: All routes use `export const dynamic = 'force-dynamic'` which disables Next.js caching
  - Home page: `/src/app/page.tsx`
  - API routes: `/src/app/api/products/route.ts` and `/src/app/api/checkout/route.ts`
- **Impact**: High - every request hits external service, no browser/CDN caching
- **Solution**: Enable caching with appropriate revalidation intervals (e.g., 60 seconds)

### 3. **Unnecessary API Calls (Products Endpoint)**
- **Problem**: `/api/products` endpoint fetches user info unnecessarily
- **Impact**: Medium - extra latency on products endpoint
- **Solution**: Remove user fetch from products endpoint (user is fetched separately on home page)

### 4. **O(n*m) Review Count Lookup**
- **Problem**: ProductList component filters reviews array for each product on every render
  - `getReviewCount = (productId) => reviews.filter(...).length`
- **Impact**: Medium - scales poorly with more products and reviews
- **Solution**: Create a memoized review count map using `useMemo`

### 5. **Full Library Imports for Single Functions**
- **Problem**: Compare page imports entire Lodash and MathJS libraries for a few functions
  - Lodash: Only uses `sortBy, meanBy, sumBy, maxBy, minBy`
  - MathJS: Only uses `mean, std, median, quantileSeq, variance`
- **Impact**: Medium - increases bundle size
- **Solution**: Replace with native JavaScript or minimal utility functions

### 6. **Unnecessary Sequential Fetch in Checkout**
- **Problem**: Checkout route fetches profile sequentially after Promise.all completes
  - The profile fetch depends only on user.id, not on config
- **Impact**: Low - minor latency gain
- **Solution**: Move profile fetch into the Promise.all with user and config

## Implementation Strategy

### Phase 1: Fix Data Fetching Parallelization
**Files to modify:**
1. `/src/app/page.tsx` - Parallelize 3 API calls
2. `/src/app/api/products/route.ts` - Remove unnecessary user fetch
3. `/src/app/api/checkout/route.ts` - Parallelize profile fetch with user/config

### Phase 2: Enable Caching
**Files to modify:**
1. `/src/app/page.tsx` - Replace `force-dynamic` with `revalidate: 60` (60 second cache)
2. `/src/app/api/products/route.ts` - Add `revalidate: 60`
3. `/src/app/api/checkout/route.ts` - Keep force-dynamic (checkout must be fresh)

### Phase 3: Optimize Review Count Lookup
**Files to modify:**
1. `/src/components/ProductList.tsx` - Memoize review count map with `useMemo`

### Phase 4: Remove Heavy Dependencies
**Files to modify:**
1. `/src/app/compare/page.tsx` - Replace Lodash functions with native JS
2. `/src/app/compare/page.tsx` - Replace MathJS functions with native JS

## Implementation Details

### 1. Home Page Parallel Fetching (page.tsx)
```typescript
// Before (sequential):
const user = await fetchUserFromService();
const products = await fetchProductsFromService();
const reviews = await fetchReviewsFromService();

// After (parallel):
const [user, products, reviews] = await Promise.all([
  fetchUserFromService(),
  fetchProductsFromService(),
  fetchReviewsFromService(),
]);
```

### 2. Caching Strategy
```typescript
// Replace:
export const dynamic = 'force-dynamic';

// With:
export const revalidate = 60; // Cache for 60 seconds
```

### 3. Products Endpoint Optimization
- Remove `fetchUserFromService()` call from `/api/products/route.ts`
- Keep only product and analytics calls
- Remove user from response if present

### 4. Checkout Endpoint Optimization
```typescript
// Before (sequential profile):
const [user, config] = await Promise.all([...]);
const profile = await fetchProfileFromService(user.id);

// After (profile in parallel):
const [user, config, profile] = await Promise.all([
  fetchUserFromService(),
  fetchConfigFromService(),
  fetchProfileFromService(userId), // Need to extract or pre-fetch user ID
]);
```

### 5. Review Count Optimization (ProductList.tsx)
```typescript
// Create memoized review map:
const reviewCountMap = useMemo(() => {
  const map = new Map<string, number>();
  reviews.forEach(review => {
    map.set(review.productId, (map.get(review.productId) || 0) + 1);
  });
  return map;
}, [reviews]);

// Use in getReviewCount:
const getReviewCount = (productId: string) => reviewCountMap.get(productId) || 0;
```

### 6. Replace Lodash Functions (compare/page.tsx)
Replace with native JavaScript equivalents:
- `sortBy(arr, 'price')` → `arr.sort((a, b) => a.price - b.price)`
- `meanBy(arr, 'price')` → `arr.reduce((s, p) => s + p.price, 0) / arr.length`
- `sumBy(arr, 'reviews')` → `arr.reduce((s, p) => s + p.reviews, 0)`
- `maxBy(arr, 'rating')` → `arr.reduce((max, p) => p.rating > max.rating ? p : max)`
- `minBy(arr, 'price')` → `arr.reduce((min, p) => p.price < min.price ? p : min)`

### 7. Replace MathJS Functions (compare/page.tsx)
Replace with native or minimal implementations:
- `mean(arr)` → `arr.reduce((s, v) => s + v, 0) / arr.length`
- `median(arr)` → Sort and find middle value
- `std(arr)` → Calculate standard deviation manually
- `variance(arr)` → Calculate variance manually
- `quantileSeq(arr, q)` → Manual percentile calculation

## Constraints to Maintain
- ✅ Do not modify `data-testid` attributes
- ✅ Keep `performance.mark()` calls in ProductCard
- ✅ Keep all components and features functional
- ✅ Homepage must show product data
- ✅ Adding products to cart must work
- ✅ Compare page advanced tab must render properly

## Code Changes Required

### 1. `/src/app/page.tsx` - Lines 5-10
Change from sequential to parallel fetching:
```typescript
// FROM:
export const dynamic = 'force-dynamic';
const user = await fetchUserFromService();
const products = await fetchProductsFromService();
const reviews = await fetchReviewsFromService();

// TO:
export const revalidate = 60;
const [user, products, reviews] = await Promise.all([
  fetchUserFromService(),
  fetchProductsFromService(),
  fetchReviewsFromService(),
]);
```

### 2. `/src/app/api/products/route.ts` - Lines 9-18
Remove unnecessary user fetch, enable caching, parallelize remaining calls:
```typescript
// FROM:
export const dynamic = 'force-dynamic';
const user = await fetchUserFromService();
const products = await fetchProductsFromService();
await logAnalyticsToService({ userId: user.id, ...

// TO:
export const revalidate = 60;
const [products, user] = await Promise.all([
  fetchProductsFromService(),
  fetchUserFromService(),
]);
await logAnalyticsToService({ userId: user.id, action: 'view_products', count: products.length });
```

### 3. `/src/app/api/checkout/route.ts` - Lines 9-27
Parallelize profile fetch (remove sequential dependency):
```typescript
// FROM:
const [user, config] = await Promise.all([
  fetchUserFromService(),
  fetchConfigFromService(),
]);
const profile = await fetchProfileFromService(user.id);

// TO:
const [user, config, profile] = await Promise.all([
  fetchUserFromService(),
  fetchConfigFromService(),
  fetchProfileFromService(await fetchUserFromService().then(u => u.id)), // Inline user.id
]);
```
Note: Actually need to fetch user first to get ID, so keep checkout as-is or restructure.

### 4. `/src/components/ProductList.tsx` - Lines 4, 43-45
Add useMemo import and optimize review count lookup:
```typescript
// ADD to imports:
import { useMemo } from 'react';

// REPLACE getReviewCount function:
const reviewCountMap = useMemo(() => {
  const map = new Map<string, number>();
  reviews.forEach(review => {
    map.set(review.productId, (map.get(review.productId) || 0) + 1);
  });
  return map;
}, [reviews]);

const getReviewCount = (productId: string) => reviewCountMap.get(productId) || 0;
```

### 5. `/src/app/compare/page.tsx` - Lines 5-6, 28-120
Replace Lodash and MathJS imports and functions with native JS:
- Remove: `import { groupBy, sortBy, meanBy, sumBy, maxBy, minBy } from 'lodash';`
- Remove: `import { mean, std, median, quantileSeq, variance } from 'mathjs';`
- Replace all function calls with native implementations

## Verification Plan

### Test 1: Homepage Loads Correctly
- [ ] Navigate to `/`
- [ ] Verify products display with names, prices, ratings
- [ ] Verify user greeting shows (e.g., "Welcome, John!")
- [ ] Verify product count displays (e.g., "Browse our X products")
- [ ] Verify "Compare Products" button exists

### Test 2: Add to Cart Works
- [ ] Click "Add to Cart" on a product
- [ ] Verify button changes to "✓ In Cart"
- [ ] Verify cart counter increases (`data-testid="cart-count"`)
- [ ] Verify filtering out-of-stock items still works
- [ ] Verify search filter still works
- [ ] Verify sort by price/rating still works

### Test 3: Compare Page Works
- [ ] Navigate to `/compare` via button on homepage
- [ ] Verify Overview tab displays comparison table
- [ ] Click Advanced Analysis tab
- [ ] Verify `data-testid="advanced-content"` element is visible
- [ ] Verify statistics display correctly (mean, median, std dev, quartiles)
- [ ] Verify value score ranking calculates correctly

### Test 4: Performance Improvements
- [ ] Check Network tab - verify 3 API calls on home page are parallelized (not sequential)
- [ ] Check caching - repeated requests should use cached responses
- [ ] Verify performance marks still trigger in ProductCard (`performance.mark()`)
- [ ] Check bundle size reduction in build output

## Critical Files to Modify
1. `/src/app/page.tsx` - Parallelize fetches, enable caching
2. `/src/app/api/products/route.ts` - Remove user fetch, enable caching
3. `/src/app/api/checkout/route.ts` - Parallelize profile fetch
4. `/src/components/ProductList.tsx` - Memoize review count map
5. `/src/app/compare/page.tsx` - Replace Lodash and MathJS with native JS
