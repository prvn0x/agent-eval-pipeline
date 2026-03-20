import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

API = "https://agent-eval-pipeline.onrender.com"

st.set_page_config(
    page_title="Agent Eval Pipeline",
    page_icon="🔬",
    layout="wide",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("Agent Eval Pipeline")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Conversations & Evaluations", "Improvement Suggestions", "Meta-Evaluation"],
)

# ── Helpers ────────────────────────────────────────────────────────────────────
def get(path: str) -> dict | list | None:
    try:
        r = requests.get(f"{API}{path}", timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def post(path: str, body: dict) -> dict | None:
    try:
        r = requests.post(f"{API}{path}", json=body, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def score_color(score: float | None) -> str:
    if score is None:
        return "grey"
    if score >= 0.8:
        return "green"
    if score >= 0.6:
        return "orange"
    return "red"


def score_badge(score: float | None) -> str:
    color = score_color(score)
    label = f"{score:.2f}" if score is not None else "N/A"
    return f":{color}[{label}]"


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Overview
# ══════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    st.title("Overview")

    health = get("/health")
    if health:
        col1, col2, col3 = st.columns(3)
        col1.metric("Status", health.get("status", "unknown").upper())
        col2.metric("Version", health.get("version", "-"))
        col3.metric("LLM Enabled", "Yes" if health.get("llm_enabled") else "No (heuristic only)")

    st.divider()
    st.subheader("What this system does")
    st.markdown("""
- **Ingests** multi-turn agent conversations via REST API
- **Evaluates** each conversation across 4 dimensions:
  - Heuristic checks (empty responses, latency, mission completion)
  - LLM-as-Judge (quality, helpfulness, factuality via Ollama)
  - Tool call accuracy (parameter hallucination detection)
  - Multi-turn coherence (context retention, consistency)
- **Collects** human annotations with Cohen's Kappa inter-annotator agreement
- **Self-updates** by detecting recurring failure patterns → generates improvement suggestions
- **Meta-evaluates** evaluator calibration against human labels to surface blind spots
""")

    st.divider()
    st.subheader("Quick test — ingest a sample conversation")

    sample = {
        "conversation_id": "demo_001",
        "agent_version": "v1.0",
        "turns": [
            {"turn_id": 1, "role": "user", "content": "Book me a flight to Delhi next Monday",
             "timestamp": "2025-01-15T10:00:00Z"},
            {"turn_id": 2, "role": "assistant", "content": "I found 3 flights to Delhi on Monday. The cheapest is ₹4,200 on IndiGo departing at 06:00.",
             "timestamp": "2025-01-15T10:00:02Z",
             "tool_calls": [{"tool_name": "search_flights", "parameters": {"destination": "Delhi", "date": "2025-01-20"}}]},
            {"turn_id": 3, "role": "user", "content": "Book the IndiGo one", "timestamp": "2025-01-15T10:00:10Z"},
            {"turn_id": 4, "role": "assistant", "content": "Done! Your IndiGo flight to Delhi on Jan 20 is confirmed. Booking ref: IG-4821.",
             "timestamp": "2025-01-15T10:00:12Z"},
        ],
        "metadata": {"mission_completed": True, "total_latency_ms": 1200},
    }

    if st.button("Ingest sample conversation"):
        result = post("/conversations", sample)
        if result:
            st.success(f"Ingested: {result['conversation_id']} — {result['message']}")
            st.info("Evaluation runs synchronously. Fetch results in the Conversations tab.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Conversations & Evaluations
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Conversations & Evaluations":
    st.title("Conversations & Evaluations")

    conversation_id = st.text_input("Conversation ID", placeholder="e.g. demo_001")

    if conversation_id:
        data = get(f"/evaluations/{conversation_id}")
        if data:
            st.subheader(f"Evaluation — `{conversation_id}`")

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Overall", score_badge(data.get("overall_score")))
            col2.metric("Response Quality", score_badge(data.get("response_quality")))
            col3.metric("Tool Accuracy", score_badge(data.get("tool_accuracy")))
            col4.metric("Coherence", score_badge(data.get("coherence")))

            # Radar chart
            scores = {
                "Response Quality": data.get("response_quality") or 0,
                "Tool Accuracy": data.get("tool_accuracy") or 0,
                "Coherence": data.get("coherence") or 0,
            }
            if any(v > 0 for v in scores.values()):
                fig = go.Figure(go.Scatterpolar(
                    r=list(scores.values()),
                    theta=list(scores.keys()),
                    fill="toself",
                    line_color="#4F8BF9",
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                    showlegend=False,
                    height=300,
                    margin=dict(l=40, r=40, t=40, b=40),
                )
                st.plotly_chart(fig, use_container_width=True)

            # Per-evaluator scores
            evaluator_scores = data.get("evaluator_scores") or {}
            if evaluator_scores:
                st.subheader("Per-Evaluator Scores")
                ev_df = pd.DataFrame([
                    {"Evaluator": k, "Score": v if v is not None else "N/A"}
                    for k, v in evaluator_scores.items()
                ])
                st.dataframe(ev_df, use_container_width=True, hide_index=True)

            # Issues
            issues = data.get("issues_detected") or []
            if issues:
                st.subheader(f"Issues Detected ({len(issues)})")
                for issue in issues:
                    severity = issue.get("severity", "info")
                    icon = "🔴" if severity == "error" else "🟡"
                    st.markdown(f"{icon} **{issue.get('type')}** — {issue.get('description')}")

            # Tool evaluation
            tool_eval = data.get("tool_evaluation") or {}
            if tool_eval:
                st.subheader("Tool Evaluation")
                st.json(tool_eval)

    st.divider()
    st.subheader("Feedback & Agreement")

    agreement_id = st.text_input("Check agreement for conversation ID", placeholder="e.g. demo_001", key="agreement_input")
    if agreement_id:
        result = get(f"/feedback/agreement/{agreement_id}")
        if result:
            col1, col2, col3 = st.columns(3)
            kappa = result.get("cohen_kappa")
            col1.metric("Cohen's Kappa", f"{kappa:.3f}" if kappa is not None else "N/A")
            col2.metric("Agreement Level", result.get("agreement_level", "-").upper())
            col3.metric("Decision", result.get("routing_decision", "-"))

            dist = result.get("label_distribution") or {}
            if dist:
                st.bar_chart(dist)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Improvement Suggestions
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Improvement Suggestions":
    st.title("Improvement Suggestions")
    st.caption("Self-updater scans evaluations for recurring failure patterns and generates fixes.")

    col1, col2 = st.columns([2, 1])
    with col1:
        agent_version = st.text_input("Agent version", value="v1.0")
    with col2:
        st.write("")
        st.write("")
        if st.button("Run self-updater"):
            with st.spinner("Detecting patterns and generating suggestions..."):
                result = post("/suggestions/trigger", {"agent_version": agent_version})
            if result:
                st.success(f"Generated {result['suggestions_saved']} suggestion(s)")

    st.divider()

    data = get(f"/suggestions?agent_version={agent_version}" if agent_version else "/suggestions")
    if data and data.get("suggestions"):
        st.subheader(f"{data['total']} suggestion(s) for {data.get('agent_version') or 'all versions'}")

        category_colors = {"prompt": "🟦", "tool": "🟨", "training": "🟩"}

        for s in data["suggestions"]:
            with st.expander(f"{category_colors.get(s['category'], '⬜')} [{s['category'].upper()}] {s['pattern_type']} — {s['occurrence_count']}x occurrences"):
                st.markdown(f"**Suggestion:** {s['suggestion_text']}")
                if s.get("rationale"):
                    st.markdown(f"**Rationale:** {s['rationale']}")
                col1, col2 = st.columns(2)
                if s.get("confidence") is not None:
                    col1.metric("Confidence", f"{s['confidence']:.0%}")
                col2.metric("Occurrences", s["occurrence_count"])
                st.markdown(f"**Pattern summary:** {s['pattern_summary']}")
                st.caption(f"ID: {s['id']} · Generated: {s['created_at'][:10]}")
    elif data:
        st.info("No suggestions yet. Run the self-updater above.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Meta-Evaluation
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Meta-Evaluation":
    st.title("Meta-Evaluation")
    st.caption("Calibrates evaluators against human annotations and surfaces blind spots.")

    if st.button("Run meta-evaluation"):
        with st.spinner("Running calibration..."):
            result = post("/meta-eval/run", {})
        if result:
            st.success(f"Analyzed {result['conversations_analyzed']} conversation(s)")
            st.rerun()

    data = get("/meta-eval/latest")
    if data:
        st.subheader("Latest Report")
        col1, col2, col3 = st.columns(3)
        col1.metric("Conversations Analyzed", data["conversations_analyzed"])
        col2.metric("Overall Agreement", f"{data['overall_agreement']:.1%}")
        col3.metric("Run At", data["run_at"][:10])

        # Evaluator calibration table
        calibration = data.get("evaluator_calibration") or []
        if calibration:
            st.subheader("Evaluator Calibration")
            df = pd.DataFrame([{
                "Evaluator": c["evaluator"],
                "Samples": c["sample_count"],
                "Agreement": c["agreement_rate"],
                "Precision": c.get("precision"),
                "Recall": c.get("recall"),
                "F1": c.get("f1"),
                "FPR": c["false_positive_rate"],
                "FNR": c["false_negative_rate"],
            } for c in calibration])
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Bar chart
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Precision", x=df["Evaluator"], y=df["Precision"], marker_color="#4F8BF9"))
            fig.add_trace(go.Bar(name="Recall", x=df["Evaluator"], y=df["Recall"], marker_color="#51CF66"))
            fig.add_trace(go.Bar(name="F1", x=df["Evaluator"], y=df["F1"], marker_color="#FCC419"))
            fig.add_trace(go.Bar(name="FNR", x=df["Evaluator"], y=df["FNR"], marker_color="#FF6B6B"))
            fig.update_layout(barmode="group", height=320, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        # Blind spots
        blind_spots = data.get("blind_spots") or []
        if blind_spots:
            st.subheader(f"Blind Spots ({len(blind_spots)})")
            st.caption("Issue types humans flagged that evaluators missed.")
            bs_df = pd.DataFrame(blind_spots)
            bs_df.columns = ["Issue Type", "Human Flagged", "Evaluator Missed"]
            st.dataframe(bs_df, use_container_width=True, hide_index=True)
        else:
            st.success("No blind spots detected — evaluators align with human annotations.")
    else:
        st.info("No report yet. Run meta-evaluation above.")
