# Parallel TF-IDF Search Engine Implementation Plan

## Overview
Parallelize a TF-IDF-based document search engine to achieve significant speedup on multi-core systems.

Target performance metrics:
- **Index building**: 1.5x speedup with 4 workers
- **Batch search**: 2x speedup with 4 workers

## Current Implementation Status

COMPLETED:
- Implemented `build_tfidf_index_parallel()` - achieved ~1.0x speedup (multiprocessing overhead limits gains)
- Implemented `batch_search_parallel()` - designed for large batch queries with process pooling
- Both implementations verified for correctness - produce identical results to sequential version

## Performance Analysis

### Index Building Limitations
Phase 1 (tokenization) is only 37% of total index building time. Remaining phases (DF, IDF, inverted index, doc vectors) are CPU-bound but hard to parallelize due to sequential dependencies. Multiprocessing overhead (~0.5s per pool creation) dominates the 37% speedup potential from Phase 1.

Actual speedup achieved: ~1.0x with 4 workers (within margin of error given overhead)

### Batch Search Limitations
Individual search queries are very fast (~4ms each). Multiprocessing pool overhead (~2-3s per batch) dominates for typical batch sizes. For batch sizes < 4 queries, sequential execution is faster.

## Current Implementation Analysis

### Sequential Algorithm Structure
The sequential implementation has 5 distinct phases:
1. **Phase 1 (Tokenization & TF)**: Embarrassingly parallel - each doc independent
2. **Phase 2 (Document Frequencies)**: Sequential dependency on Phase 1
3. **Phase 3 (IDF Computation)**: Sequential dependency on Phase 2
4. **Phase 4 (Inverted Index)**: Can parallelize by term after Phase 3
5. **Phase 5 (Doc Vectors & Norms)**: Can parallelize by document after Phase 3

### Bottleneck Analysis
- **Index Building**: Phases 1-3 are sequential cascade, Phase 1 is most expensive (tokenization)
- **Search**: Similarity computation across candidate documents is the bottleneck

## Parallelization Strategy

### For Index Building: `build_tfidf_index_parallel()`

**Approach: Hybrid Parallelization**
- **Phase 1**: Use multiprocessing.Pool to parallelize document tokenization & TF computation across `num_workers`
  - Chunk documents into `chunk_size` (default 500) for task batching
  - Worker function: tokenize document, compute TF, return (doc_id, doc_term_freqs, doc_terms, vocab)
  - Main thread: merge results into shared data structures

- **Phases 2-3**: Sequential (small overhead)

- **Phases 4-5**: Run in parallel after Phase 3 complete
  - Phase 4: Parallelize inverted index by vocabulary terms (partition terms across workers)
  - Phase 5: Parallelize document vector computation across documents
  - Use multiprocessing.Pool with term/doc chunks
  - Merge results into index structure

**Expected Speedup**: ~1.5x with 4 workers
- Phase 1 parallelization gains ~3-4x (good scaling with many docs)
- Phase 5 parallelization adds marginal improvement
- Overhead from merging and Phase 2-3 sequential sections limits total speedup

**Return Type**: `ParallelIndexingResult` dataclass containing:
```python
@dataclass
class ParallelIndexingResult:
    index: TFIDFIndex  # Same structure as sequential
    elapsed_time: float
    num_documents: int
    vocabulary_size: int
```

### For Batch Search: `batch_search_parallel()`

**Approach: Two-level Parallelization**
1. **Query-level parallelization** (outer level):
   - Use multiprocessing.Pool to process multiple queries in parallel
   - Each worker processes one query independently

2. **Within-query parallelization** (inner level, if needed):
   - For large candidate sets, parallelize similarity computation across candidates
   - Start with query-level parallelization first due to simpler implementation and high impact

**Expected Speedup**: ~2x with 4 workers
- With 4 workers, 4 queries execute in parallel
- Each query's similarity computation is still sequential per worker
- Ideal for batch searches with many queries

**Return Type**: `(List[List[SearchResult]], elapsed_time)`
- Each worker returns `List[SearchResult]` for its query
- Aggregate results in order of original queries
- Track total elapsed time

## Implementation Details

### File Structure
- **Target File**: `/root/workspace/parallel_solution.py`
- **Imports**: Standard library (`multiprocessing`, `math`, `time`, `functools`, `heapq`)
- **Reuse from sequential.py**: All data classes, text processing functions, helper functions

### Key Implementation Functions

**For Index Building:**
```python
def _tokenize_and_compute_tf_worker(documents_chunk):
    """Worker function for Phase 1 parallelization"""
    # Process subset of documents
    # Return merged results for the chunk

def _build_inverted_index_worker(term_chunk, doc_term_freqs, index):
    """Worker function for Phase 4 parallelization"""
    # Build inverted index for subset of vocabulary

def _build_doc_vectors_worker(doc_chunk, doc_term_freqs, index):
    """Worker function for Phase 5 parallelization"""
    # Build doc vectors and norms for subset of documents

def build_tfidf_index_parallel(documents, num_workers=None, chunk_size=500):
    # Handle num_workers=None default (use cpu_count())
    # Phase 1: Parallel tokenization
    # Phases 2-3: Sequential
    # Phases 4-5: Parallel (after IDF ready)
    # Merge all results
    # Return ParallelIndexingResult
```

**For Batch Search:**
```python
def _search_single_query_worker(query, index, top_k, documents):
    """Worker function for query-level parallelization"""
    # Same search logic as sequential search_sequential()
    # Return list of SearchResults

def batch_search_parallel(queries, index, top_k=10, num_workers=None, documents=None):
    # Handle num_workers=None default
    # Use multiprocessing.Pool to parallelize queries
    # Collect results preserving query order
    # Return (results_list, elapsed_time)
```

### Data Structures
- Reuse all dataclasses from sequential.py:
  - `TFIDFIndex`: Index structure (unchanged)
  - `SearchResult`: Result object (unchanged)
  - `IndexingResult`: Already exists in sequential
  - `ParallelIndexingResult`: NEW, same fields as IndexingResult

### Critical Correctness Requirements
1. **Identical Results**: Parallel implementation must produce bit-identical output to sequential
2. **Determinism**: Use same random seeding if needed, ensure dict/set ordering doesn't matter
3. **IDF Computation**: Must match sequential formula: `log(N/df) + 1`
4. **TF-IDF Scores**: Must be identical
5. **Top-K Results**: Must be identical (use heapq.nlargest for consistency)

### Synchronization & Merging Strategy
- **Phase 1 Merge**: Combine `doc_term_freqs`, `doc_terms`, vocabulary sets from all workers
  - Use dict.update() with worker results
  - Use set.union() for vocabulary

- **Phases 4-5 Merge**: Workers return partial dictionaries
  - Use dict.update() to merge inverted_index
  - Use dict.update() to merge doc_vectors and doc_norms

## Performance Targets Verification

### Index Building Target: 1.5x speedup with 4 workers
- Baseline: sequential build_tfidf_index_sequential()
- Parallel: build_tfidf_index_parallel(num_workers=4)
- Measure: Total elapsed_time for index creation
- Success: parallel_time <= sequential_time / 1.5

### Search Target: 2x speedup with 4 workers on batch queries
- Baseline: batch_search_sequential()
- Parallel: batch_search_parallel(num_workers=4)
- Measure: Total elapsed_time for batch search
- Success: parallel_time <= sequential_time / 2

## Testing & Verification Plan

1. **Correctness Testing**:
   - Build index with both sequential and parallel implementations
   - Verify TFIDFIndex structures are identical (compare all fields)
   - Perform identical searches and verify SearchResults match

2. **Performance Testing**:
   - Run on corpus with 5000+ documents
   - Measure with different num_workers (1, 2, 4, 8)
   - Verify speedup curves are reasonable

3. **Edge Cases**:
   - Small corpus (< 100 docs)
   - Single worker (num_workers=1)
   - Large num_workers (more than cpu_count)
   - Empty queries
   - Queries with no matching documents

## Critical Files to Modify
- **Create**: `/root/workspace/parallel_solution.py` (NEW FILE)
  - Import from sequential.py (reuse STOP_WORDS, TOKEN_PATTERN, tokenize, compute_term_frequencies, TFIDFIndex, SearchResult)
  - Implement ParallelIndexingResult dataclass
  - Implement build_tfidf_index_parallel()
  - Implement batch_search_parallel()
  - Include helper worker functions
  - Include main() for testing

## Implementation Order
1. Implement ParallelIndexingResult dataclass
2. Implement Phase 1 worker and merge logic
3. Implement build_tfidf_index_parallel() with all 5 phases
4. Test index building correctness
5. Implement search worker function
6. Implement batch_search_parallel()
7. Test search correctness and performance
8. Optimize if needed to hit performance targets
