"""
Dependency Graph Generation (Week 5).
Generates a deterministic co-occurrence graph for labels.
"""

# Hardcoded clinical/co-occurrence priors (DAG)
# A -> B implies A often leads to B or B depends on A context? 
# "Dependency graph" in contract usually means "Explanation X depends on Label Y".
# But user said "co-occurrence graph".
# Let's assume directional: Primary -> comorbidity.
# e.g. PTSD -> Depression, ADHD -> Anxiety.
GRAPH_EDGES = [
    ("ptsd", "depression"),
    ("ptsd", "anxiety"),
    ("adhd", "anxiety"),
    ("adhd", "depression"),
    ("depression", "anxiety"),
    ("depression", "suicidewatch"), # if we had it
    ("bipolar", "depression"),
    ("bipolar", "mania"),
    ("ocd", "anxiety")
]

def build_dependency_graph(active_labels):
    """
    Builds a subgraph for the active labels.
    Args:
        active_labels: List of label names (decision=1)
    Returns:
        Dict with {nodes: [], edges: [[src, tgt], ...]}
    """
    nodes = sorted(list(set(active_labels)))
    edges = []
    
    # Add edges if both nodes are present
    for u, v in GRAPH_EDGES:
        if u in nodes and v in nodes:
            edges.append([u, v])
            
    return {
        "nodes": nodes,
        "edges": edges,
        "is_acyclic": True # Hardcoded edges are acyclic
    }
