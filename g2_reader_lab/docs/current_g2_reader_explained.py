
"""Educational, runnable pseudocode for the current G²-Reader algorithm.

This file does not call MinerU, an embedding server, or a VLM.  Small,
deterministic functions stand in for those systems so that every object and
transition can be inspected by running:

    python current_g2_reader_explained.py

The important distinction is preserved:

1. The Content Graph is constructed and evolved before question answering.
2. The Content Graph is frozen during inference.
3. The Planning Graph is created and possibly revised at query time.
4. The existing checker judges apparent sufficiency from intermediate answers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import math
import re
from typing import Iterable


def heading(title: str) -> None:
    """Print a visible stage boundary when the demonstration runs."""
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


@dataclass
class ContentNode:
    """One atomic document element: a paragraph, figure, or table.

    Paper notation:
        v_i = (c_i, attr_i, h_i)
        attr_i = (s_i, k_i)

    Here:
        raw_content = c_i
        summary     = s_i
        keywords    = k_i
        embedding   = h_i
    """

    node_id: str
    document: str
    position: int
    element_type: str
    raw_content: str
    caption: str = ""
    summary: str = ""
    keywords: list[str] = field(default_factory=list)
    embedding: list[float] = field(default_factory=list)
    links: set[str] = field(default_factory=set)

    def short(self) -> str:
        return f"{self.node_id} ({self.document}, {self.element_type}, pos={self.position})"


@dataclass
class PlanningTask:
    """One subquestion/node in the online Planning Graph."""

    task_id: str
    question: str
    dependencies: list[str] = field(default_factory=list)
    answer: str = ""
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class ContentGraph:
    nodes: dict[str, ContentNode]

    def add_undirected_edge(self, left: str, right: str) -> None:
        self.nodes[left].links.add(right)
        self.nodes[right].links.add(left)

    def neighbors(self, node_id: str) -> list[ContentNode]:
        return [self.nodes[n] for n in sorted(self.nodes[node_id].links)]


def parse_with_mineru(documents: list[str]) -> list[ContentNode]:
    """Stand-in for MinerU document parsing.

    Real output is produced from PDF text blocks and extracted images.  The
    returned list V is only a set of candidate nodes; edges, summaries,
    keywords, and embeddings have not been created yet.
    """

    del documents  # The toy collection below represents the five input PDFs.
    return [
        ContentNode(
            "v1", "paper_A.pdf", 11, "paragraph",
            "Figure 3 compares AUC under different training-set sizes.",
        ),
        ContentNode(
            "v2", "paper_A.pdf", 12, "figure",
            "Figure pixels encode: blue=DMRNet, orange=ESMM, gray=Other; "
            "at 20 percent training DMRNet=0.84, ESMM=0.81, Other=0.77.",
            "AUC under different training-set sizes",
        ),
        ContentNode(
            "v3", "paper_A.pdf", 13, "paragraph",
            "DMRNet performs consistently well when training data are limited.",
        ),
        ContentNode(
            "v4", "paper_B.pdf", 7, "table",
            "Table values: Model X=0.72 and Model Y=0.69 on another task.",
            "Accuracy on a different benchmark",
        ),
        ContentNode(
            "v5", "paper_C.pdf", 4, "figure",
            "A bar chart reporting runtime rather than AUC.",
            "Runtime comparison",
        ),
        ContentNode(
            "v6", "paper_D.pdf", 9, "paragraph",
            "Additional training data generally improve predictive performance.",
        ),
    ]


def encode(text: str, dimension: int = 64) -> list[float]:
    """Create a deterministic toy embedding from shared word features.

    In G² this is a pretrained embedding model.  The result h_i is a dense
    numerical vector used for cosine similarity; it is not readable text.
    """

    vector = [0.0] * dimension
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def vlm_initialize(node: ContentNode) -> tuple[str, list[str]]:
    """Stand-in for the per-node VLM initialization call.

    Text nodes are summarized from text; visual nodes are interpreted from the
    image.  G² embeds this generated description rather than raw image pixels.
    """

    if node.element_type == "figure" and "AUC under" in node.caption:
        return (
            "Line figure comparing model AUC across training-set sizes.",
            ["AUC", "models", "training size", "figure"],
        )
    if node.element_type == "table":
        return (
            f"Table containing model results. {node.caption}",
            ["table", "models", "results"],
        )
    words = re.findall(r"[A-Za-z0-9]+", node.raw_content)
    return (" ".join(words[:14]) + ".", sorted(set(words[:6])))


def initialize_nodes(nodes: Iterable[ContentNode]) -> None:
    """Compute (s_i, k_i) = VLM_init(c_i), then h_i = Encoder(s_i ⊕ k_i)."""

    heading("1. INITIAL V = PARSED DOCUMENT ELEMENTS")
    for node in nodes:
        print(f"{node.short()}: {node.raw_content[:72]}")

    heading("2. VLM INITIALIZATION AND EMBEDDING")
    for node in nodes:
        node.summary, node.keywords = vlm_initialize(node)
        node.embedding = encode(node.summary + " " + " ".join(node.keywords))
        print(f"{node.short()}")
        print(f"  s_i: {node.summary}")
        print(f"  k_i: {node.keywords}")
        print(f"  h_i[:6]: {[round(x, 3) for x in node.embedding[:6]]}")


def initialize_reading_order_edges(graph: ContentGraph, window: int = 1) -> None:
    """Create E⁰={(v_i,v_j): same document and positions are nearby}."""

    by_document: dict[str, list[ContentNode]] = {}
    for node in graph.nodes.values():
        by_document.setdefault(node.document, []).append(node)

    for document_nodes in by_document.values():
        ordered = sorted(document_nodes, key=lambda node: node.position)
        for index, node in enumerate(ordered):
            for neighbor in ordered[index + 1 : index + 1 + window]:
                graph.add_undirected_edge(node.node_id, neighbor.node_id)

    heading("3. INITIAL READING-ORDER EDGES E⁰")
    for node in graph.nodes.values():
        print(f"{node.node_id} -> {sorted(node.links)}")


def top_semantic_neighbors(
    graph: ContentGraph, target: ContentNode, count: int = 3
) -> list[ContentNode]:
    """Return TopK_j Sim(h_i, h_j), excluding the target node."""

    candidates = [node for node in graph.nodes.values() if node.node_id != target.node_id]
    return sorted(
        candidates,
        key=lambda node: cosine(target.embedding, node.embedding),
        reverse=True,
    )[:count]


def vlm_evolve(
    target: ContentNode, candidates: list[ContentNode]
) -> tuple[str, list[str], set[str]]:
    """Stand-in for one VLM-based joint attribute/topology update."""

    candidate_ids = [node.node_id for node in candidates[:2]]
    candidate_terms = [node.element_type for node in candidates[:2]]
    summary = f"{target.summary} Contextually related to {', '.join(candidate_ids)}."
    keywords = sorted(set(target.keywords + candidate_terms))
    return summary, keywords, set(candidate_ids)


def evolve_content_graph(graph: ContentGraph, rounds: int) -> None:
    """Apply G²'s joint node-attribute and topology evolution.

    C_i^t = TopK_j Sim(h_i^t,h_j^t) ∪ N^t(v_i)
    (s_i^{t+1}, k_i^{t+1}, N_i^{t+1}) = VLM(c_i,s_i^t,k_i^t,C_i^t)
    """

    for round_index in range(rounds):
        heading(f"4.{round_index + 1} CONTENT-GRAPH EVOLUTION ROUND {round_index + 1}")
        updates: dict[str, tuple[str, list[str], set[str]]] = {}

        for node in graph.nodes.values():
            semantic = top_semantic_neighbors(graph, node)
            existing = graph.neighbors(node.node_id)
            candidates = {candidate.node_id: candidate for candidate in semantic + existing}
            candidate_list = list(candidates.values())
            updates[node.node_id] = vlm_evolve(node, candidate_list)
            print(f"{node.node_id}: C_i={sorted(candidates)}")

        # Apply attributes from one consistent pre-evolution snapshot.
        for node_id, (summary, keywords, new_links) in updates.items():
            node = graph.nodes[node_id]
            node.summary = summary
            node.keywords = keywords
            node.embedding = encode(summary + " " + " ".join(keywords))
            node.links = set()

        # Reconstruct topology only after every old link set has been cleared.
        # Otherwise resetting a later node could erase an earlier undirected edge.
        for node_id, (_, _, new_links) in updates.items():
            for neighbor_id in new_links:
                graph.add_undirected_edge(node_id, neighbor_id)

    heading("5. FIXED CONTENT GRAPH AFTER INGESTION")
    for node in graph.nodes.values():
        print(f"{node.node_id}: links={sorted(node.links)}; summary={node.summary}")


def graph_retrieve(graph: ContentGraph, query: str, budget: int) -> list[ContentNode]:
    """G² structured subgraph readout.

    Rank nodes by cosine similarity.  For each seed, add the seed and its
    immediate graph neighbors until |V_out| >= k.
    """

    query_embedding = encode(query)
    ranked = sorted(
        graph.nodes.values(),
        key=lambda node: cosine(query_embedding, node.embedding),
        reverse=True,
    )
    selected: dict[str, ContentNode] = {}
    for seed in ranked:
        selected[seed.node_id] = seed
        for neighbor in graph.neighbors(seed.node_id):
            selected[neighbor.node_id] = neighbor
        if len(selected) >= budget:
            break
    return list(selected.values())


def decompose_question(question: str, probe: list[ContentNode]) -> list[PlanningTask]:
    """Stand-in for the initial Decomposer VLM call."""

    del question, probe
    return [
        PlanningTask("q1", "Identify the methods shown in Figure 3."),
        PlanningTask("q2", "Read every AUC value at 20% training.", ["q1"]),
        PlanningTask("q3", "Determine which AUC value is highest.", ["q2"]),
    ]


def worker(task: PlanningTask, evidence: list[ContentNode], tasks: list[PlanningTask]) -> str:
    """Stand-in for a Worker VLM call over local evidence and prior answers."""

    raw = " ".join(node.raw_content for node in evidence)
    dependency_text = " ".join(
        other.answer for other in tasks if other.task_id in task.dependencies
    )
    context = raw + " " + dependency_text

    if task.task_id == "q1" and "DMRNet" in context:
        return "The methods are DMRNet, ESMM, and Other."
    if task.task_id == "q2" and "DMRNet=0.84" in context:
        return "At 20%, DMRNet=0.84, ESMM=0.81, and Other=0.77."
    if task.task_id == "q3" and "0.84" in context:
        return "DMRNet has the highest AUC."
    return "The retrieved evidence is inconclusive."


def evidence_checker(question: str, tasks: list[PlanningTask]) -> tuple[bool, list[str]]:
    """Current G²-style sufficiency decision.

    Checker(Q, {(q_i,a_i)}) -> (sufficient, gaps)

    Notice that the decision below uses intermediate answer text.  It does not
    atomically test each claim against an exact figure region or table cell.
    """

    del question
    gaps = [task.task_id for task in tasks if "inconclusive" in task.answer]
    return (not gaps, gaps)


def reasoner(question: str, tasks: list[PlanningTask]) -> str:
    """Stand-in for final evidence-grounded answer synthesis."""

    del question
    conclusions = [task.answer for task in tasks if "highest" in task.answer]
    return conclusions[-1] if conclusions else "Unable to answer."


def run_current_g2() -> None:
    documents = [f"paper_{letter}.pdf" for letter in "ABCDE"]
    question = "Which method has the highest AUC at 20% training in Figure 3?"

    nodes = parse_with_mineru(documents)
    initialize_nodes(nodes)
    graph = ContentGraph({node.node_id: node for node in nodes})
    initialize_reading_order_edges(graph)
    evolve_content_graph(graph, rounds=3)

    heading("6. INITIAL PROBE AND PLANNING GRAPH")
    probe = graph_retrieve(graph, question, budget=5)
    print("Probe evidence:", [node.node_id for node in probe])
    tasks = decompose_question(question, probe)
    for task in tasks:
        print(f"{task.task_id}: {task.question}; depends on {task.dependencies}")

    heading("7. WORKER -> SUFFICIENCY CHECK -> POSSIBLE REPLAN")
    for planning_round in range(3):
        print(f"Planning round {planning_round}")
        for task in tasks:
            evidence = graph_retrieve(graph, task.question, budget=5)
            task.evidence_ids = [node.node_id for node in evidence]
            task.answer = worker(task, evidence, tasks)
            print(f"  {task.task_id} evidence={task.evidence_ids}")
            print(f"  {task.task_id} answer={task.answer}")

        sufficient, gaps = evidence_checker(question, tasks)
        print(f"Checker: sufficient={sufficient}, gaps={gaps}")
        if sufficient:
            break

        # The real system invokes the refinement Decomposer here.  This toy
        # keeps the same tasks so the control flow remains easy to inspect.
        print("Generic replanning would revise or add subquestions here.")

    heading("8. FINAL REASONER")
    print("Final answer:", reasoner(question, tasks))


if __name__ == "__main__":
    run_current_g2()
