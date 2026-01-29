# Parallel TF-IDF Implementation Plan

## Objective
Parallelize TF-IDF index building and batch search to achieve:
- 1.5x speedup on index building
- 2x speedup on batch search with 4 workers
- Identical results to sequential version

## Implementation Strategy

### 1. Parallel Index Building (`build_tfidf_index_parallel`)

**Challenge**: The 5-step process has data dependencies:
- Step 1 → Step 2 (vocabulary dependency)
- Step 2 → Step 3 (DF dependency)
- But Steps 4 and 5 are independent once Step 3 completes

**Approach - Two-Phase Strategy**:

**Phase A: Sequential Vocabulary Building (Steps 1-3)**
- Can't parallelize effectively due to data dependencies
- Use same sequential logic to build vocabulary and IDF
- Time cost: ~20-30% of total indexing time

**Phase B: Parallel Document Processing (Steps 4-5)**
- Step 4: Build inverted index per term (parallel over terms)
- Step 5: Build document vectors and norms (parallel over documents)
- Time cost: ~60-70% of total indexing time → Target: 1.5x speedup

**Parallel Architecture**:
- Use `multiprocessing.Pool` (process-based, avoids GIL)
- Chunk documents/terms for balanced work distribution
- Default: `num_workers=None` → CPU count

**Implementation Details**:
1. Sequential phase:
   - Loop through documents: tokenize, compute TF
   - Build vocabulary and document frequencies
   - Compute IDF scores

2. Parallel phase - Inverted Index:
   - Create tasks: one per term
   - Worker function: `_build_inverted_index_chunk(term, doc_term_freqs, idf)`
   - Returns: `{term: [(doc_id, tfidf), ...]}`
   - Main process: Merge results into single index

3. Parallel phase - Document Vectors:
   - Create tasks: chunks of documents (chunk_size=500)
   - Worker function: `_build_doc_vectors_chunk(doc_ids, doc_term_freqs, idf)`
   - Returns: `{doc_id: {vector}, doc_norms}`
   - Main process: Merge into doc_vectors and doc_norms

**Return Type**: Create `ParallelIndexingResult` dataclass with same TFIDFIndex structure

### 2. Parallel Batch Search (`batch_search_parallel`)

**Approach - Query-Level Parallelism**:
- Each query search is fully independent
- No shared state during search phase
- Use `multiprocessing.Pool` for query distribution
- Default: `num_workers=None` → CPU count

**Implementation Details**:
1. Prepare read-only search index (already immutable after building)
2. Create worker function: `_search_worker(query, index, top_k, doc_titles_dict)`
3. Use `pool.map()` or `pool.imap_unordered()` to parallelize queries
4. Collect results in original query order
5. Measure and return elapsed_time

**Optimization**:
- Pre-compute document title dictionary for workers
- Use IPC-friendly data types (avoid large object copies)
- Return only SearchResult objects (lightweight)

### 3. Data Structures

**ParallelIndexingResult** (new):
```python
@dataclass
class ParallelIndexingResult:
    index: TFIDFIndex  # Same structure as sequential
    elapsed_time: float
    num_documents: int
    vocabulary_size: int
```

### 4. Worker Functions

**`_build_inverted_index_chunk(term, doc_term_freqs, idf)`**:
- Input: Single term, all doc TF dicts, IDF dict
- Output: `(term, [(doc_id, tfidf), ...])` sorted by score desc
- Logic: Iterate docs, compute TF-IDF, sort

**`_build_doc_vectors_chunk(doc_ids, doc_term_freqs, idf)`**:
- Input: List of doc_ids, TF dicts, IDF dict
- Output: `({doc_vectors}, {doc_norms})`
- Logic: Build dense vectors, compute L2 norms

**`_search_worker(query, index, top_k, doc_titles_dict)`**:
- Input: Single query string, index, top_k, titles
- Output: `List[SearchResult]`
- Logic: Reuse sequential search logic

### 5. Key Implementation Details

**Correctness Guarantees**:
- Phase A (vocabulary building): Identical to sequential
- Phase B (parallel phases): Results merged deterministically
  - Inverted index: Simple dict merge by term
  - Document vectors: Dict merge by doc_id
  - Sorting: Posting lists sorted identically
- Batch search: Results returned in same query order

**GIL Consideration**:
- Use `multiprocessing.Pool` (process-based) for CPU-bound work
- Not `threading.Pool` (thread-based, affected by GIL)

**Memory Efficiency**:
- Chunk documents into `chunk_size=500` batches to control memory
- Workers serialize/deserialize minimal data
- Avoid copying full index; use shared memory via pickling

**Load Balancing**:
- Index building: Terms vary in size (some have many docs, some few)
  - Solution: Let OS scheduler handle work distribution
- Batch search: Queries vary in complexity (different # candidates)
  - Solution: Use `pool.imap_unordered()` + dynamic scheduling

### 6. Testing Strategy

**Correctness**:
1. Generate small corpus (100 docs)
2. Build index sequentially and in parallel
3. Compare all index fields: vocabulary, IDF, inverted_index, doc_vectors, doc_norms
4. Verify they're byte-identical

**Search Results**:
1. Run same batch of queries on both implementations
2. Compare SearchResult lists (doc_id, score, title)
3. Use tolerance for float comparisons (exact match expected since same computation path)

**Performance**:
1. Measure speedup with 4 workers
2. Target: 1.5x for indexing, 2x for searching

## Files to Modify

- **Create**: `/root/workspace/parallel_solution.py`
  - Import from `sequential.py`: STOP_WORDS, TOKEN_PATTERN, tokenize, compute_term_frequencies, TFIDFIndex, SearchResult
  - Implement: ParallelIndexingResult, build_tfidf_index_parallel, batch_search_parallel
  - Implement: Worker functions (_build_inverted_index_chunk, _build_doc_vectors_chunk, _search_worker)

## Verification

### End-to-End Test
```bash
python /root/workspace/parallel_solution.py --corpus <corpus.json> --num-workers 4 --query "machine learning"
```

1. Load corpus
2. Build index in parallel
3. Run batch search in parallel
4. Compare with sequential version (timing and correctness)
