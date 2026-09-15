"""
main.py
Milestone 4: HP Extreme Weather RAG
Modern Himalayan Scientific Local Interface

Thin presentation layer over the validated backend (Milestone 1, 2A, 2B, 3).
Strictly delegates all retrieval, evidence pack compilation, generation,
and answer validation to app/rag_engine.py.
"""

import os
import sys
import streamlit as st

# Ensure project root is on sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import app.rag_engine as rag_engine
import app.components as components
from app.examples import get_example_queries


# -------------------------------------------------------------
# Page Configuration
# -------------------------------------------------------------
st.set_page_config(
    page_title="HP Extreme Weather RAG",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# -------------------------------------------------------------
# Main Application Entry Point
# -------------------------------------------------------------
def main() -> None:
    # 1. Inject Modern Himalayan Visual Styling
    components.inject_custom_theme()

    # 2. Render Hero Header (clean typography, no emoji)
    components.render_hero_header()

    # 4. Session State Initialization
    if "current_query" not in st.session_state:
        st.session_state["current_query"] = ""
    if "execute_trigger" not in st.session_state:
        st.session_state["execute_trigger"] = False

    # 5. Curated Example Demonstration Cards
    st.markdown("##### 💡 Curated Demonstration Inquiries")
    examples = get_example_queries()

    col_a, col_b, col_c = st.columns(3)
    cols = [col_a, col_b, col_c]

    for idx, ex in enumerate(examples):
        with cols[idx % 3]:
            btn_label = f"**{ex['category']}**\n\n{ex['query']}"
            if st.button(
                btn_label,
                key=f"btn_ex_{ex['id']}",
                use_container_width=True,
                help=ex["description"]
            ):
                st.session_state["current_query"] = ex["query"]
                st.session_state["execute_trigger"] = True
                st.rerun()

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 6. Main Query Area
    with st.container():
        st.markdown("""
        <div style="margin-bottom: 4px; font-weight: 700; color: #f8fafc; font-size: 1.05rem;">
            🔍 Ask about Himachal Pradesh extreme weather
        </div>
        """, unsafe_allow_html=True)

        with st.form("query_submission_form", clear_on_submit=False):
            user_query = st.text_input(
                label="Query input:",
                value=st.session_state["current_query"],
                placeholder="e.g., What was the maximum rainfall in Kangra in 2023?",
                label_visibility="collapsed",
                help="Inquire about rainfall metrics, cloudburst events, disaster impacts, or PDNA reconstruction guidelines."
            )

            col_btn, col_empty = st.columns([1, 4])
            with col_btn:
                submitted = st.form_submit_button("🔍 Run Query", type="primary", use_container_width=True)

    # 7. Query Execution Pipeline
    should_run = submitted or st.session_state["execute_trigger"]

    if should_run:
        st.session_state["execute_trigger"] = False
        active_query = user_query.strip() if submitted else st.session_state["current_query"].strip()

        if not active_query:
            st.warning("Please enter a question or click an example above.")
            return

        # Execute end-to-end RAG pipeline via facade
        with st.spinner("Executing hybrid retrieval, evidence pack compilation, and grounded validation..."):
            response = rag_engine.execute_query(active_query)

        st.divider()

        # 8. Render Response Area
        if response.is_rejected:
            components.render_rejection_panel(response)
        else:
            components.render_2026_warning(response)
            components.render_answer_card(response)
            components.render_citations(response.citations, response.evidence_pack)

        components.render_evidence_pack_inspector(response.evidence_pack)
        components.render_validation_audit(response)

    # 9. Academic Unobtrusive Footer
    components.render_footer()


if __name__ == "__main__":
    main()
