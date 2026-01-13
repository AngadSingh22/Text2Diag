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


def build_dependency_graph(labels, probs_map, mode="active", k=3, edge_threshold=0.15):
    """
    Builds a subgraph for the labels based on mode.
    Args:
        labels: List of all label names available to consider (or active ones if mode=active passed pre-filtered)
        probs_map: Dict of {label: prob}
        mode: "active" (use labels as is) or "topk" (use top k by prob)
        k: Number of nodes for topk
        edge_threshold: Min weight (not used for hardcoded binary edges, but good for future)
    Returns:
        Dict with {nodes: [], edges: [[src, tgt, weight], ...], is_acyclic: bool}
    """
    if mode == "topk":
        # Sort by prob
        sorted_items = sorted(probs_map.items(), key=lambda x: x[1], reverse=True)
        nodes = [x[0] for x in sorted_items[:k]]
    else:
        # active mode: assume labels is already the list of active labels
        nodes = list(labels)
        
    nodes = sorted(list(set(nodes)))
    edges = []
    
    # Add edges if both nodes are present
    for u, v in GRAPH_EDGES:
        if u in nodes and v in nodes:
            # Deterministic weight: average of probs? or fixed?
            # User req: "keep existing... but include weight field (float)"
            # Let's use avg prob as weight or just 1.0 if not specified.
            # "drop lowest-weight edge...". Let's use sum of endpoint probs
            w = (probs_map.get(u, 0) + probs_map.get(v, 0)) / 2.0
            edges.append([u, v, round(w, 4)])
            
    # Cycle detection (DFS)
    def has_cycle(current_edges):
        adj = {n: [] for n in nodes}
        for u, v, w in current_edges:
            adj[u].append(v)
            
        visited = set()
        stack = set()
        
        def visit(n):
            if n in stack: return True
            if n in visited: return False
            
            stack.add(n)
            visited.add(n)
            for neighbor in adj.get(n, []):
                if visit(neighbor): return True
            stack.remove(n)
            return False
            
        for n in nodes:
            if visit(n): return True
        return False
        
    # Break cycles
    while has_cycle(edges):
        # Drop lowest weight edge
        # Sort by weight (ascending), then deterministic edge name
        # edges is [u, v, w]
        edges.sort(key=lambda x: (x[2], x[0], x[1]))
        if not edges: break
        dropped = edges.pop(0)
            
    return {
        "nodes": nodes,
        "edges": edges,
        "is_acyclic": True
    }

