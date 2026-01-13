"""
Explanation Graph V1 (Week 6+).
Generates a typed, auditable graph of the decision process.
"""
import hashlib

def build_explanation_graph(output_dict):
    """
    Constructs the explanation graph from the final output dictionary.
    
    Nodes:
    - Label (decision)
    - Span (evidence)
    - Rule (policy)
    - Faithfulness (verification)
    
    Edges:
    - Span -> Label (supports)
    - Rule -> Label (governs decision)
    - Faith -> Label (verifies)
    """
    nodes = []
    edges = []
    
    # 1. Rules Nodes (Static)
    rule_temp = {
        "id": "rule:temperature", 
        "type": "rule", 
        "method": "temperature_scaling",
        "value": output_dict.get("calibration", {}).get("temperature")
    }
    nodes.append(rule_temp)
    
    # 2. Process Labels
    labels = output_dict.get("labels", [])
    
    for lbl in labels:
        name = lbl["name"]
        lbl_id = f"label:{name}"
        
        # Label Node
        nodes.append({
            "id": lbl_id,
            "type": "label",
            "name": name,
            "prob": lbl["prob_calibrated"],
            "decision": lbl["decision"],
            "threshold": lbl["threshold_used"]
        })
        
        # Edge: Rule -> Label check? 
        # Actually easier to have explicit Trace node, but let's stick to simpler:
        # Label uses Rule(Threshold)
        thresh_src = lbl.get("threshold_source", "unknown")
        thresh_rule_id = f"rule:threshold:{thresh_src}"
        
        # Ensure threshold rule node exists
        if not any(n["id"] == thresh_rule_id for n in nodes):
             nodes.append({
                 "id": thresh_rule_id,
                 "type": "rule",
                 "method": "thresholding",
                 "source": thresh_src
             })
             
        edges.append({
            "src": thresh_rule_id,
            "dst": lbl_id,
            "type": "governs"
        })
        
        # Spans (Evidence)
        spans = lbl.get("evidence_spans", [])
        for span in spans:
            # Deterministic ID for span
            # hash(label + start + end)
            s_hash = hashlib.sha256(f"{name}:{span['start']}:{span['end']}".encode()).hexdigest()[:8]
            span_id = f"span:{s_hash}"
            
            nodes.append({
                "id": span_id,
                "type": "span",
                "text": span["snippet"], # Snippet might be masked
                "score": span["score"]
            })
            
            edges.append({
                "src": span_id,
                "dst": lbl_id,
                "type": "supports",
                "weight": span["score"]
            })
            
        # Faithfulness
        faith = lbl.get("faithfulness", {})
        if faith:
            f_id = f"faith:{name}"
            nodes.append({
                "id": f_id,
                "type": "faithfulness",
                "status": faith.get("faithfulness_status", "unknown"),
                "delta": faith.get("delta")
            })
            edges.append({
                "src": lbl_id,
                "dst": f_id,
                "type": "verified_by"
            })
            
    return {
        "version": "explanation_graph_v1",
        "nodes": nodes,
        "edges": edges,
        "is_acyclic": True 
    }
