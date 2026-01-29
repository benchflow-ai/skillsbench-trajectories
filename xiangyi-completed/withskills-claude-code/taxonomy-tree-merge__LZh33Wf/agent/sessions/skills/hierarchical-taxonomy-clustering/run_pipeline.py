import sys
sys.path.insert(0, '/logs/agent/sessions/skills/hierarchical-taxonomy-clustering/scripts')

import pandas as pd
from pathlib import Path
from step1_preprocessing_and_merge import standardize_and_filter_sources
from step2_weighted_embedding_generation import generate_embeddings
from step3_recursive_clustering_naming import recursive_taxonomy_clustering
from step4_result_assignments import apply_assignments, export_results, print_quality_metrics

# Load source data
source_dfs = [
    (pd.read_csv('/root/data/amazon_product_categories.csv'), 'amazon'),
    (pd.read_csv('/root/data/fb_product_categories.csv'), 'facebook'),
    (pd.read_csv('/root/data/google_shopping_product_categories.csv'), 'google')
]

# Run pipeline
output_dir = '/root/output'
Path(output_dir).mkdir(parents=True, exist_ok=True)

target_depth = 5
min_clusters_l1 = 10
max_clusters = 20
min_clusters_other = 3

print("=" * 80)
print("HIERARCHICAL TAXONOMY CLUSTERING PIPELINE")
print("=" * 80)

# Step 1
print("\n" + "=" * 80)
print("STEP 1: LOAD, STANDARDIZE, FILTER AND MERGE")
print("=" * 80)

df = standardize_and_filter_sources(source_dfs, target_depth=target_depth)
print(f"\nMerged data:")
print(f"  Records: {len(df)}")
print(f"  Depth distribution: {df['depth'].value_counts().sort_index().to_dict()}")

# Step 2
print("\n" + "=" * 80)
print("STEP 2: GENERATE WEIGHTED EMBEDDINGS")
print("=" * 80)

weights = {1: 1.0, 2: 0.6, 3: 0.36, 4: 0.216, 5: 0.1296}
embeddings = generate_embeddings(df, target_depth=target_depth, weights=weights)

# Step 3
print("\n" + "=" * 80)
print("STEP 3: RECURSIVE CLUSTERING WITH WORD-BASED NAMING")
print("=" * 80)

all_indices = list(range(len(df)))
assignments = recursive_taxonomy_clustering(
    df=df,
    embeddings=embeddings,
    indices=all_indices,
    current_level=1,
    max_level=target_depth,
    parent_words=set(),
    parent_label='ROOT',
    global_parent_categories=set(),
    min_clusters_l1=min_clusters_l1,
    max_clusters=max_clusters,
    min_clusters_other=min_clusters_other
)

print(f"\n✅ Clustering complete!")
print(f"   Assigned {len(assignments)} records")

# Step 4
print("\n" + "=" * 80)
print("STEP 4: APPLY ASSIGNMENTS AND EXPORT RESULTS")
print("=" * 80)

result_df = apply_assignments(df, assignments, max_level=target_depth)
full_df, hierarchy_df = export_results(result_df, output_dir, max_level=target_depth)

# Print quality metrics
print_quality_metrics(result_df, max_level=target_depth)

print("\n" + "=" * 80)
print("PIPELINE COMPLETE!")
print("=" * 80)
print(f"\nOutputs saved to: {output_dir}")
print(f"  1. unified_taxonomy_full.csv - Full mapping ({len(full_df)} records)")
print(f"  2. unified_taxonomy_hierarchy.csv - Taxonomy structure ({len(hierarchy_df)} paths)")
