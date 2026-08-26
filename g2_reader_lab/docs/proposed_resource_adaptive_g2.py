"""Educational, runnable pseudocode for the proposed resource-adaptive G².

Run:

    python proposed_resource_adaptive_g2.py

The fast 8B Content Graph remains an offline index.  Lightweight scientific
artifacts (OCR, table structure, figure regions, legend/axis candidates, and
multiresolution crops) are also prepared and cached during ingestion.  Query
time primarily selects from this cache; it does not routinely perform expensive
visual interpretation.  A strong VLM is only a low-confidence fallback.

The research change is at query time: the original binary Evidence Checker is
replaced by a controller that selects the next evidence/reasoning action under
a hard latency budget.

This toy controller uses transparent scoring rules.  In the research system,
the scores would be learned from failure-audit trajectories containing the
state, selected action, measured cost, and downstream accuracy/support change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import math
import re


def heading(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


@dataclass
class ContentNode:
    """A provenance-preserving paragraph, figure, table, or equation node."""

    node_id: str
    paper_id: str
    page_number: int
    position: int
    element_type: str
    bounding_box: tuple[int, int, int, int]
    raw_content: str
    caption: str = ""
    summary: str = ""
    keywords: list[str] = field(default_factory=list)
    embedding: list[float] = field(default_factory=list)
    links: set[str] = field(default_factory=set)
    cached_artifacts: dict[str, object] = field(default_factory=dict)

    @property
    def source_location(self) -> str:
        return (
            f"{self.paper_id}:page={self.page_number}:"
            f"bbox={self.bounding_box}:node={self.node_id}"
        )


@dataclass
class ContentGraph:
    nodes: dict[str, ContentNode]

    def connect(self, left: str, right: str) -> None:
        self.nodes[left].links.add(right)
        self.nodes[right].links.add(left)

    def neighbors(self, node_id: str) -> list[ContentNode]:
        return [self.nodes[n] for n in sorted(self.nodes[node_id].links)]


@dataclass
class EvidenceRequirement:
    """A fact that must be resolved before the answer is trustworthy."""

    requirement_id: str
    description: str
    preferred_modality: str
    operation: str
    resolved: bool = False


@dataclass
class Claim:
    text: str
    source_locations: list[str]
    support_score: float = 0.0
    verified: bool = False


@dataclass
class ResourceBudget:
    """One common cost unit can represent seconds, tokens, or GPU-seconds."""

    remaining: float
    strong_model_calls: int


@dataclass
class AgentState:
    question: str
    requirements: list[EvidenceRequirement]
    budget: ResourceBudget
    evidence: list[ContentNode] = field(default_factory=list)
    discoveries: dict[str, object] = field(default_factory=dict)
    claims: list[Claim] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


class Action(str, Enum):
    RETRIEVE_NODE = "RETRIEVE_NODE"
    EXPAND_GRAPH = "EXPAND_GRAPH"
    READ_CACHED_LEGEND = "READ_CACHED_LEGEND"
    READ_CACHED_FIGURE_VALUES = "READ_CACHED_FIGURE_VALUES"
    READ_CACHED_TABLE = "READ_CACHED_TABLE"
    READ_CACHED_EQUATION = "READ_CACHED_EQUATION"
    COMPUTE_COMPARISON = "COMPUTE_COMPARISON"
    VERIFY_CLAIM = "VERIFY_CLAIM"
    USE_STRONG_MODEL = "USE_STRONG_MODEL"
    REVISE_PLAN = "REVISE_PLAN"
    ANSWER = "ANSWER"
    ABSTAIN = "ABSTAIN"


ACTION_COST: dict[Action, float] = {
    Action.RETRIEVE_NODE: 2.0,
    Action.EXPAND_GRAPH: 2.0,
    Action.READ_CACHED_LEGEND: 0.2,
    Action.READ_CACHED_FIGURE_VALUES: 0.5,
    Action.READ_CACHED_TABLE: 0.5,
    Action.READ_CACHED_EQUATION: 0.5,
    Action.COMPUTE_COMPARISON: 0.2,
    Action.VERIFY_CLAIM: 0.5,
    Action.USE_STRONG_MODEL: 20.0,
    Action.REVISE_PLAN: 8.0,
    Action.ANSWER: 0.5,
    Action.ABSTAIN: 0.1,
}


def encode(text: str, dimension: int = 64) -> list[float]:
    """Deterministic stand-in for h_i = Encoder(s_i ⊕ k_i)."""

    vector = [0.0] * dimension
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimension
        vector[bucket] += 1.0 if digest[4] % 2 == 0 else -1.0
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def parse_with_mineru(documents: list[str]) -> list[ContentNode]:
    """Return toy MinerU elements with explicit paper/page/region provenance."""

    del documents
    return [
        ContentNode(
            "v1", "paper_A.pdf", 6, 11, "paragraph", (90, 160, 930, 230),
            "Figure 3 compares AUC under different training-set sizes.",
        ),
        ContentNode(
            "v2", "paper_A.pdf", 6, 12, "figure", (100, 240, 940, 790),
            "Figure pixels encode: blue=DMRNet, orange=ESMM, gray=Other; "
            "at 20 percent training DMRNet=0.84, ESMM=0.81, Other=0.77.",
            "AUC under different training-set sizes",
        ),
        ContentNode(
            "v3", "paper_A.pdf", 6, 13, "paragraph", (90, 800, 930, 900),
            "DMRNet performs consistently well when training data are limited.",
        ),
        ContentNode(
            "v4", "paper_B.pdf", 3, 7, "table", (80, 300, 950, 760),
            "Model X=0.72 and Model Y=0.69 on an unrelated benchmark.",
            "Accuracy on another benchmark",
        ),
        ContentNode(
            "v5", "paper_C.pdf", 4, 4, "figure", (110, 200, 920, 720),
            "A bar chart reporting runtime rather than AUC.",
            "Runtime comparison",
        ),
    ]


def qwen8b_initialize(node: ContentNode) -> tuple[str, list[str]]:
    """Cheap per-element description used to build the general index."""

    if node.element_type == "figure" and "AUC under" in node.caption:
        return (
            "Figure comparing model AUC across training-set sizes.",
            ["AUC", "model", "training size", "figure"],
        )
    if node.element_type == "table":
        return ("Table of model results.", ["table", "model", "results"])
    tokens = re.findall(r"[A-Za-z0-9]+", node.raw_content)
    return (" ".join(tokens[:14]) + ".", sorted(set(tokens[:6])))


def precompute_scientific_artifacts(node: ContentNode) -> None:
    """Prepare cheap reusable evidence artifacts during ingestion.

    Production implementations can run OCR, layout detection, table parsers,
    chart-region detectors, and crop-pyramid generation in parallel.  These
    artifacts are cached by document/content hash and amortized across queries.

    Extracted interpretations are candidates with confidence values, not
    automatically trusted facts.  Low-confidence candidates can later trigger
    the strong-model fallback, subject to the online latency budget.
    """

    node.cached_artifacts["ocr_text"] = node.raw_content
    node.cached_artifacts["crop_pyramid"] = {
        "page": f"cache/{node.node_id}/page.png",
        "element": f"cache/{node.node_id}/element.png",
        "high_resolution": f"cache/{node.node_id}/element_2x.png",
    }

    if node.element_type == "figure" and "AUC under" in node.caption:
        node.cached_artifacts["legend_candidates"] = {
            "value": {
                "blue": "DMRNet",
                "orange": "ESMM",
                "gray": "Other",
            },
            "confidence": 0.94,
            "region": "legend_bbox=(690,250,920,390)",
        }
        node.cached_artifacts["axis_candidates"] = {
            "value": {"x": "training percentage", "y": "AUC"},
            "confidence": 0.92,
            "region": "plot_bbox=(150,300,850,730)",
        }
        node.cached_artifacts["series_candidates"] = {
            "value": {
                "20%": {"DMRNet": 0.84, "ESMM": 0.81, "Other": 0.77}
            },
            "confidence": 0.91,
            "region": "x=20%-vertical-slice",
        }

    if node.element_type == "table":
        node.cached_artifacts["table_structure"] = {
            "headers": ["Method", "Score"],
            "rows": [["Model X", 0.72], ["Model Y", 0.69]],
            "confidence": 0.95,
        }


def build_fast_content_graph(documents: list[str], evolution_rounds: int = 1) -> ContentGraph:
    """Build a reusable 8B Content Graph.

    This provides a cheap broad index plus cached scientific artifacts.  Heavy
    interpretation is not simply shifted to query time: most online actions
    select already-prepared data.  Only ambiguous cases can request a strong
    VLM, if the remaining latency budget permits it.
    """

    heading("1. PARSE DOCUMENTS INTO PROVENANCE-PRESERVING V")
    nodes = parse_with_mineru(documents)
    for node in nodes:
        print(f"{node.node_id}: {node.source_location}; type={node.element_type}")

    heading("2. INITIALIZE ALL NODES WITH QWEN-8B")
    for node in nodes:
        node.summary, node.keywords = qwen8b_initialize(node)
        node.embedding = encode(node.summary + " " + " ".join(node.keywords))
        print(f"{node.node_id}: s_i={node.summary}; k_i={node.keywords}")

    heading("3. PRECOMPUTE AND CACHE LIGHTWEIGHT SCIENTIFIC ARTIFACTS")
    for node in nodes:
        precompute_scientific_artifacts(node)
        print(f"{node.node_id}: cached={sorted(node.cached_artifacts)}")

    graph = ContentGraph({node.node_id: node for node in nodes})

    # Initial local reading-order structure.
    ordered = sorted(
        [node for node in nodes if node.paper_id == "paper_A.pdf"],
        key=lambda node: node.position,
    )
    for left, right in zip(ordered, ordered[1:]):
        graph.connect(left.node_id, right.node_id)

    heading("4. INEXPENSIVE 8B GRAPH EVOLUTION")
    for round_index in range(evolution_rounds):
        proposed_links: set[tuple[str, str]] = set()
        for target in nodes:
            ranked = sorted(
                [node for node in nodes if node.node_id != target.node_id],
                key=lambda node: cosine(target.embedding, node.embedding),
                reverse=True,
            )
            semantic_neighbor = ranked[0]
            proposed_links.add(tuple(sorted((target.node_id, semantic_neighbor.node_id))))
            print(
                f"round={round_index + 1}: {target.node_id} "
                f"semantic candidate={semantic_neighbor.node_id}"
            )
        for left, right in proposed_links:
            graph.connect(left, right)

    return graph


def graph_retrieve(graph: ContentGraph, query: str, budget: int = 3) -> list[ContentNode]:
    """Retrieve summary-matching nodes, then include graph neighbors."""

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


def make_evidence_requirements(question: str) -> list[EvidenceRequirement]:
    """The initial planner turns Q into explicit unresolved information slots."""

    del question
    return [
        EvidenceRequirement("r1", "Map legend colors to method names", "figure", "legend"),
        EvidenceRequirement("r2", "Locate the 20% x-axis position", "figure", "axis"),
        EvidenceRequirement("r3", "Read each method's AUC at 20%", "figure", "values"),
        EvidenceRequirement("r4", "Select the maximum AUC", "symbolic", "argmax"),
    ]


def relevant_figure(state: AgentState) -> ContentNode | None:
    """Return the retrieved AUC figure, if it is present."""

    return next(
        (
            node
            for node in state.evidence
            if node.element_type == "figure" and "AUC under" in node.caption
        ),
        None,
    )


def has_confident_cache(
    state: AgentState, artifact_name: str, threshold: float = 0.80
) -> bool:
    """Check whether the relevant node has a sufficiently reliable artifact."""

    figure = relevant_figure(state)
    if figure is None:
        return False
    artifact = figure.cached_artifacts.get(artifact_name)
    return bool(
        isinstance(artifact, dict)
        and float(artifact.get("confidence", 0.0)) >= threshold
    )


def valid_actions(state: AgentState) -> list[Action]:
    """Return actions that make sense in the current evidence state."""

    actions: list[Action] = [Action.ABSTAIN]
    if not state.evidence:
        actions += [Action.RETRIEVE_NODE, Action.USE_STRONG_MODEL]
        return actions

    if "legend" not in state.discoveries:
        if has_confident_cache(state, "legend_candidates"):
            actions.append(Action.READ_CACHED_LEGEND)
        actions += [Action.EXPAND_GRAPH, Action.USE_STRONG_MODEL]
    elif "values" not in state.discoveries:
        if has_confident_cache(state, "series_candidates"):
            actions.append(Action.READ_CACHED_FIGURE_VALUES)
        actions += [Action.EXPAND_GRAPH, Action.USE_STRONG_MODEL]
    elif not state.claims:
        actions += [Action.COMPUTE_COMPARISON, Action.USE_STRONG_MODEL]
    elif not all(claim.verified for claim in state.claims):
        actions += [Action.VERIFY_CLAIM, Action.USE_STRONG_MODEL]
    else:
        actions += [Action.ANSWER]
    return actions


def predicted_gain(state: AgentState, action: Action) -> float:
    """Transparent stand-in for a learned expected downstream improvement."""

    gains = {
        Action.RETRIEVE_NODE: 0.65,
        Action.EXPAND_GRAPH: 0.08,
        Action.READ_CACHED_LEGEND: 0.45,
        Action.READ_CACHED_FIGURE_VALUES: 0.55,
        Action.READ_CACHED_TABLE: 0.45,
        Action.READ_CACHED_EQUATION: 0.45,
        Action.COMPUTE_COMPARISON: 0.35,
        Action.VERIFY_CLAIM: 0.45,
        Action.USE_STRONG_MODEL: 0.60,
        Action.REVISE_PLAN: 0.15,
        Action.ANSWER: 1.00 if all(c.verified for c in state.claims) else 0.01,
        Action.ABSTAIN: 0.01,
    }
    return gains[action]


def choose_action(state: AgentState) -> Action:
    """Select a* = argmax_a predicted_gain(s,a) / predicted_cost(s,a).

    This call replaces the original binary sufficiency check.  It should be a
    lightweight learned policy or an extended checker output, not another
    expensive VLM layered on top of G².
    """

    candidates = [
        action
        for action in valid_actions(state)
        if ACTION_COST[action] <= state.budget.remaining
        and not (
            action == Action.USE_STRONG_MODEL
            and state.budget.strong_model_calls <= 0
        )
    ]
    if not candidates:
        return Action.ABSTAIN

    heading("CONTROLLER: EXPECTED BENEFIT PER COST")
    for action in candidates:
        utility = predicted_gain(state, action) / ACTION_COST[action]
        print(
            f"{action.value:22s} gain={predicted_gain(state, action):.2f} "
            f"cost={ACTION_COST[action]:4.1f} utility={utility:.3f}"
        )
    return max(
        candidates,
        key=lambda action: predicted_gain(state, action) / ACTION_COST[action],
    )


def mark_requirement(state: AgentState, requirement_id: str) -> None:
    for requirement in state.requirements:
        if requirement.requirement_id == requirement_id:
            requirement.resolved = True


def execute_action(action: Action, state: AgentState, graph: ContentGraph) -> str | None:
    """Execute one targeted operation and update the shared agent state."""

    if action == Action.RETRIEVE_NODE:
        state.evidence = graph_retrieve(graph, state.question, budget=3)
        return f"Retrieved nodes {[node.node_id for node in state.evidence]}"

    if action == Action.EXPAND_GRAPH:
        expanded = {node.node_id: node for node in state.evidence}
        for node in list(state.evidence):
            for neighbor in graph.neighbors(node.node_id):
                expanded[neighbor.node_id] = neighbor
        state.evidence = list(expanded.values())
        return f"Expanded to nodes {[node.node_id for node in state.evidence]}"

    if action == Action.READ_CACHED_LEGEND:
        figure = relevant_figure(state)
        assert figure is not None
        artifact = figure.cached_artifacts["legend_candidates"]
        state.discoveries["legend"] = artifact["value"]
        state.discoveries["legend_source"] = (
            f"{figure.source_location}:{artifact['region']}"
        )
        mark_requirement(state, "r1")
        return (
            f"Cached legend={state.discoveries['legend']}; "
            f"confidence={artifact['confidence']}"
        )

    if action == Action.READ_CACHED_FIGURE_VALUES:
        figure = relevant_figure(state)
        assert figure is not None
        artifact = figure.cached_artifacts["series_candidates"]
        axis_artifact = figure.cached_artifacts["axis_candidates"]
        state.discoveries["x_position"] = "20%"
        state.discoveries["values"] = artifact["value"]["20%"]
        state.discoveries["values_source"] = (
            f"{figure.source_location}:{artifact['region']}"
        )
        mark_requirement(state, "r2")
        mark_requirement(state, "r3")
        return (
            f"Cached axes={axis_artifact['value']}; "
            f"cached values={state.discoveries['values']}; "
            f"confidence={artifact['confidence']}"
        )

    if action == Action.READ_CACHED_TABLE:
        table = next(node for node in state.evidence if node.element_type == "table")
        state.discoveries["table"] = table.cached_artifacts["table_structure"]
        return f"Cached table={state.discoveries['table']}"

    if action == Action.READ_CACHED_EQUATION:
        return "Cached equation structure selected."

    if action == Action.COMPUTE_COMPARISON:
        values = state.discoveries["values"]
        best_method = max(values, key=values.get)
        figure = next(
            node
            for node in state.evidence
            if node.element_type == "figure" and "AUC under" in node.caption
        )
        state.claims.append(
            Claim(
                text=f"{best_method} has the highest AUC at 20% training.",
                source_locations=[figure.source_location],
            )
        )
        mark_requirement(state, "r4")
        return state.claims[-1].text

    if action == Action.VERIFY_CLAIM:
        # Real implementation: multimodal entailment over claim and exact crop.
        for claim in state.claims:
            source_text = " ".join(node.raw_content for node in state.evidence)
            claim.support_score = 0.96 if "DMRNet=0.84" in source_text else 0.20
            claim.verified = claim.support_score >= 0.80
        return f"Claim support={[c.support_score for c in state.claims]}"

    if action == Action.USE_STRONG_MODEL:
        state.budget.strong_model_calls -= 1
        state.discoveries["legend"] = {
            "blue": "DMRNet", "orange": "ESMM", "gray": "Other"
        }
        state.discoveries["values"] = {
            "DMRNet": 0.84, "ESMM": 0.81, "Other": 0.77
        }
        for requirement in state.requirements:
            requirement.resolved = True
        state.claims = [
            Claim(
                "DMRNet has the highest AUC at 20% training.",
                [graph.nodes["v2"].source_location],
                support_score=0.96,
                verified=True,
            )
        ]
        return "Strong model resolved and verified all remaining requirements."

    if action == Action.ANSWER:
        supported = [claim.text for claim in state.claims if claim.verified]
        return supported[-1] if supported else "Insufficient supported evidence."

    if action == Action.ABSTAIN:
        return "Insufficient supported evidence within the resource budget."

    return f"Toy executor has no implementation for {action.value}."


def update_budget_and_trace(state: AgentState, action: Action, result: str | None) -> None:
    state.budget.remaining -= ACTION_COST[action]
    state.trace.append(f"{action.value}: {result}")
    print(f"Selected action: {action.value}")
    print(f"Result: {result}")
    print(f"Remaining budget: {state.budget.remaining:.1f}")


def run_resource_adaptive_g2() -> None:
    documents = [f"paper_{letter}.pdf" for letter in "ABCDE"]
    question = "Which method has the highest AUC at 20% training in Figure 3?"
    graph = build_fast_content_graph(documents, evolution_rounds=1)

    heading("5. INITIAL PLANNING STATE AND EVIDENCE REQUIREMENTS")
    state = AgentState(
        question=question,
        requirements=make_evidence_requirements(question),
        # Hard online latency budget.  Actions that cannot fit are unavailable.
        budget=ResourceBudget(remaining=10.0, strong_model_calls=1),
    )
    for requirement in state.requirements:
        print(
            f"{requirement.requirement_id}: {requirement.description}; "
            f"modality={requirement.preferred_modality}; "
            f"operation={requirement.operation}"
        )

    heading("6. RESOURCE-ADAPTIVE ACTION LOOP")
    final_answer: str | None = None
    while state.budget.remaining > 0:
        action = choose_action(state)
        result = execute_action(action, state, graph)
        update_budget_and_trace(state, action, result)

        if action in {Action.ANSWER, Action.ABSTAIN}:
            final_answer = result
            break

    heading("7. FINAL OUTPUT AND TRACE")
    print("Final answer:", final_answer)
    print("Action trace:")
    for step_number, trace_line in enumerate(state.trace, start=1):
        print(f"  {step_number}. {trace_line}")
    print("Verified claims:")
    for claim in state.claims:
        print(
            f"  claim={claim.text}\n"
            f"  sources={claim.source_locations}\n"
            f"  support={claim.support_score:.2f}; verified={claim.verified}"
        )


if __name__ == "__main__":
    run_resource_adaptive_g2()
