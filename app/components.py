"""
components.py
Milestone 4: Modern Himalayan Scientific UI Components for Streamlit

Implements atmospheric styling, glassmorphism, and responsive research components:
- Full-page Himalayan weather wallpaper background with atmospheric dark overlay
- Frosted glass cards with high contrast and legible typography
- Hero Header with Status Badge (● DEMO READY)
- Prominent Grounded Answer Card with clear separation of Answer, Badges, and Citations
- Canonical Evidence-Type Badges (OBSERVED, CALCULATED, REPORTED, INFERRED, MIXED, INSUFFICIENT)
- Partitioned Hybrid Panels (Rainfall vs Reported Impacts)
- Sleek Provenance & Citation Cards (100% authentic; zero fake URLs)
- Expandable Evidence Pack Inspector (🔎 Inspect Evidence Pack)
- Subtle 2026 Telemetry Advisory Banner
- Streamlined Epistemic Sidebar (Zero secret exposure)
- Clean Academic Footer
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from app.rag_engine import RAGResponse, CANONICAL_EVIDENCE_TYPES

# Direct image resolved from https://wallpapersafari.com/w/VzScKv
WALLPAPER_URL = "https://cdn.wallpapersafari.com/13/97/VzScKv.jpg"

# -------------------------------------------------------------
# Canonical Badge Styling Tokens (High Contrast Glass Palette)
# -------------------------------------------------------------
BADGE_STYLES = {
    "OBSERVED": {
        "bg": "rgba(2, 132, 199, 0.20)", "text": "#38bdf8", "border": "#38bdf8",
        "label": "OBSERVED",
        "description": "Direct weather station or gauge telemetry observation"
    },
    "CALCULATED": {
        "bg": "rgba(13, 148, 136, 0.22)", "text": "#2dd4bf", "border": "#2dd4bf",
        "label": "CALCULATED",
        "description": "IMD 0.25° gridded spatial aggregate or deterministic SQL calculation"
    },
    "REPORTED": {
        "bg": "rgba(147, 51, 234, 0.22)", "text": "#c084fc", "border": "#c084fc",
        "label": "REPORTED",
        "description": "Official government memorandum, PDNA report, or GSI study"
    },
    "MIXED": {
        "bg": "rgba(217, 119, 6, 0.25)", "text": "#fbbf24", "border": "#fbbf24",
        "label": "MIXED",
        "description": "Combined quantitative rainfall calculation + qualitative disaster impact narrative"
    },
    "INFERRED": {
        "bg": "rgba(100, 116, 139, 0.25)", "text": "#94a3b8", "border": "#94a3b8",
        "label": "INFERRED",
        "description": "Strict logical deduction derived directly from supplied evidence"
    },
    "INSUFFICIENT": {
        "bg": "rgba(220, 38, 38, 0.25)", "text": "#f87171", "border": "#f87171",
        "label": "INSUFFICIENT",
        "description": "Insufficient authoritative evidence in knowledge base to answer reliably"
    }
}


def inject_custom_theme() -> None:
    """
    Injects custom CSS styling embodying the 'Modern Himalayan Extreme Weather /
    Scientific Research' design system:
    - Full-page background with vibrant, visible Himalayan mountain landscape
    - High-contrast frosted glass cards and responsive typography
    - Hidden sidebar for clean, full-width focus
    - Sleek inputs, buttons, and badges
    """
    custom_css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}

    /* Himalayan Wallpaper Background with Light Overlay for Maximum Mountain Visibility */
    [data-testid="stAppViewContainer"] {{
        background-color: #0b1329;
        background-image: 
            linear-gradient(180deg, rgba(11, 19, 43, 0.22) 0%, rgba(15, 23, 42, 0.48) 100%),
            url('{WALLPAPER_URL}');
        background-size: cover;
        background-position: center top;
        background-attachment: fixed;
    }}

    [data-testid="stHeader"] {{
        background: transparent !important;
    }}

    /* Completely hide sidebar and expander controls */
    [data-testid="stSidebar"], 
    section[data-testid="stSidebar"], 
    [data-testid="collapsedControl"],
    button[data-testid="stSidebarCollapseButton"] {{
        display: none !important;
    }}

    /* Main container frame */
    .block-container {{
        max-width: 1200px !important;
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
    }}

    /* Typography & Contrast Enhancements */
    h1, h2, h3, h4, h5, h6 {{
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.8) !important;
    }}

    p, span, label, li {{
        color: #f1f5f9;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.7);
    }}

    /* Frosted Glass Container Cards (High Legibility over Background) */
    .glass-panel {{
        background: rgba(15, 23, 42, 0.80);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.16);
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.45);
    }}

    .glass-card-subtle {{
        background: rgba(15, 23, 42, 0.78);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
    }}

    /* Form & Input Styling */
    div[data-baseweb="input"] {{
        background: rgba(15, 23, 42, 0.82) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 10px !important;
        backdrop-filter: blur(12px) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
    }}

    div[data-baseweb="input"]:focus-within {{
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.35) !important;
    }}

    div[data-baseweb="input"] input {{
        color: #ffffff !important;
        font-size: 1.05rem !important;
    }}

    /* Example Button Enhancements */
    div.stButton > button {{
        background: rgba(15, 23, 42, 0.78) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 10px !important;
        padding: 12px 18px !important;
        font-weight: 600 !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
    }}

    div.stButton > button:hover {{
        background: rgba(30, 41, 59, 0.92) !important;
        border-color: rgba(56, 189, 248, 0.7) !important;
        color: #ffffff !important;
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45) !important;
    }}

    /* Primary Submit Button */
    button[kind="primary"] {{
        background: linear-gradient(135deg, #0284c7 0%, #0d9488 100%) !important;
        border: none !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 18px rgba(2, 132, 199, 0.5) !important;
    }}

    button[kind="primary"]:hover {{
        background: linear-gradient(135deg, #0369a1 0%, #0f766e 100%) !important;
        box-shadow: 0 6px 24px rgba(2, 132, 199, 0.7) !important;
        transform: translateY(-2px);
    }}

    /* Streamlit Expander Styling */
    div[data-testid="stExpander"] {{
        background: rgba(15, 23, 42, 0.78) !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(12px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
    }}

    /* Subtle Dividers */
    hr {{
        border: 0 !important;
        border-top: 1px solid rgba(255, 255, 255, 0.15) !important;
        margin: 24px 0 !important;
    }}
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def render_hero_header() -> None:
    """
    Renders the modern research hero header with atmospheric title,
    subtitle, and the active status badge.
    Clean typography without the mountain emoji.
    """
    st.title("HP Extreme Weather RAG")
    header_html = """
    <div style="margin-top: -14px; margin-bottom: 24px;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 8px;">
            <p style="margin: 0; font-size: 1.08rem; color: #e2e8f0; line-height: 1.5; text-shadow: 0 1px 4px rgba(0,0,0,0.8);">
                Grounded retrieval and analysis of historical extreme-weather events in Himachal Pradesh
            </p>
            <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(16, 185, 129, 0.20); border: 1px solid rgba(16, 185, 129, 0.5); border-radius: 9999px; padding: 5px 16px; backdrop-filter: blur(8px); box-shadow: 0 2px 8px rgba(0,0,0,0.4);">
                <span style="height: 8px; width: 8px; background-color: #10b981; border-radius: 50%; box-shadow: 0 0 10px #10b981;"></span>
                <span style="color: #6ee7b7; font-size: 0.80rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;">
                    DEMO READY
                </span>
            </div>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px;">
            <span style="background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.16); padding: 4px 12px; border-radius: 6px; font-size: 0.80rem; color: #f1f5f9; text-shadow: 0 1px 2px rgba(0,0,0,0.7);">Kangra • Mandi • Shimla • Kullu</span>
            <span style="background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.16); padding: 4px 12px; border-radius: 6px; font-size: 0.80rem; color: #f1f5f9; text-shadow: 0 1px 2px rgba(0,0,0,0.7);">Rainfall • Cloudburst • Flash Flood</span>
            <span style="background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(8px); border: 1px solid rgba(255, 255, 255, 0.16); padding: 4px 12px; border-radius: 6px; font-size: 0.80rem; color: #f1f5f9; text-shadow: 0 1px 2px rgba(0,0,0,0.7);">2011–2026 Historical Telemetry</span>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


def render_evidence_badge(evidence_type: str) -> None:
    """
    Renders an authoritative, color-coded badge for canonical evidence types.
    Explicitly informs the user of the epistemic nature of the returned information.
    """
    ev_key = evidence_type.upper() if evidence_type else "INSUFFICIENT"
    style = BADGE_STYLES.get(ev_key, BADGE_STYLES["INSUFFICIENT"])

    badge_html = f"""
    <div style="display: inline-flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <span style="
            background: {style['bg']};
            color: {style['text']};
            border: 1px solid {style['border']};
            padding: 5px 14px;
            border-radius: 9999px;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        ">
            {style['label']}
        </span>
        <span style="font-size: 0.82rem; color: #94a3b8; font-style: italic;">
            — {style['description']}
        </span>
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)


def render_2026_warning(response: RAGResponse) -> None:
    """
    Displays an unmistakable advisory whenever the query or evidence touches 2026.
    Enforces the scientific invariant that 2026 is partial/interim telemetry.
    """
    if response.is_partial_2026:
        warning_html = """
        <div style="
            background: rgba(217, 119, 6, 0.15);
            border-left: 4px solid #f59e0b;
            border-radius: 0 8px 8px 0;
            padding: 12px 16px;
            margin-bottom: 18px;
        ">
            <div style="font-weight: 700; color: #fbbf24; font-size: 0.92rem; margin-bottom: 2px;">
                ⚠️ 2026 Data Advisory: Partial / Interim Telemetry
            </div>
            <div style="font-size: 0.88rem; color: #fde68a; line-height: 1.4;">
                2026 data is partial/current-year telemetry through September 2026. It should not be interpreted as a complete annual historical record.
            </div>
        </div>
        """
        st.markdown(warning_html, unsafe_allow_html=True)


def render_rejection_panel(response: RAGResponse) -> None:
    """
    Renders deterministic refusal explanation with clear scope boundaries.
    """
    category = response.rejection_category or "NO_SUPPORTED_EVIDENCE"
    reason = response.rejection_reason or response.answer

    rejection_html = f"""
    <div style="
        background: rgba(220, 38, 38, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.35);
        border-left: 5px solid #ef4444;
        border-radius: 10px;
        padding: 18px 20px;
        margin-bottom: 20px;
    ">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
            <span style="font-size: 1.2rem;">🛑</span>
            <span style="font-weight: 700; color: #f87171; font-size: 1.02rem; text-transform: uppercase; letter-spacing: 0.04em;">
                Query Rejected / Out of Scope ({category})
            </span>
        </div>
        <p style="margin: 0; color: #fca5a5; font-size: 0.96rem; line-height: 1.5;">
            {reason}
        </p>
    </div>
    """
    st.markdown(rejection_html, unsafe_allow_html=True)

    with st.expander("ℹ️ System Scope & Authorized Parameters", expanded=False):
        st.markdown("""
        The Himachal Pradesh Extreme Weather RAG System operates under strict epistemic boundaries:
        - **Authorized Districts (4):** Kangra, Mandi, Shimla, Kullu (and their mapped tehsils/stations).
        - **Authorized Parameters:** Daily Rainfall (IMD gridded & station), Cloudburst events, Flash Flood events.
        - **Temporal Coverage:** 2011 to 2026 (2026 is interim/partial telemetry only).
        - **Unsupported Inquiries:** Out-of-state geographies (e.g., Pune, Delhi), unrelated weather parameters
          (e.g., wind speed, temperature, humidity, snowfall depth), and non-weather hazards (earthquakes, avalanches).
        """)


def render_answer_card(response: RAGResponse) -> None:
    """
    Renders the primary grounded answer card with route metadata,
    evidence badge, and partitioned hybrid formatting.
    """
    st.markdown("### 💡 Grounded Response")

    # Header metadata strip
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        render_evidence_badge(response.evidence_type)
    with col2:
        conf_color = "#34d399" if response.confidence == "HIGH" else ("#fbbf24" if response.confidence == "MEDIUM" else "#f87171")
        st.markdown(f"**Confidence:** <span style='color: {conf_color}; font-weight: 700;'>{response.confidence}</span>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"**Route:** <code style='background: rgba(255,255,255,0.08); color: #38bdf8;'>{response.route}</code>", unsafe_allow_html=True)

    answer_text = response.answer

    # For HYBRID queries: cleanly partition Rainfall vs Reported Impacts
    if response.route == "HYBRID" and "Rainfall:" in answer_text and "Reported Impacts:" in answer_text:
        parts = answer_text.split("Reported Impacts:", 1)
        rain_section = parts[0].replace("Rainfall:", "").strip()
        impact_section = parts[1].strip() if len(parts) > 1 else ""

        hybrid_html = f"""
        <div class="glass-panel" style="margin-top: 14px; border: 1px solid rgba(255, 255, 255, 0.15);">
            <div style="background: rgba(13, 148, 136, 0.15); border-left: 4px solid #2dd4bf; border-radius: 0 8px 8px 0; padding: 14px 18px; margin-bottom: 16px;">
                <div style="font-weight: 700; color: #2dd4bf; font-size: 0.90rem; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 6px;">
                    📊 RAINFALL / STRUCTURED EVIDENCE (Calculated Spatial Grid)
                </div>
                <p style="margin: 0; font-size: 1.05rem; line-height: 1.6; color: #f8fafc;">
                    {rain_section}
                </p>
            </div>
            <div style="background: rgba(147, 51, 234, 0.15); border-left: 4px solid #c084fc; border-radius: 0 8px 8px 0; padding: 14px 18px;">
                <div style="font-weight: 700; color: #c084fc; font-size: 0.90rem; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 6px;">
                    📑 REPORTED IMPACTS / DOCUMENTARY EVIDENCE (Government & PDNA Reports)
                </div>
                <p style="margin: 0; font-size: 1.05rem; line-height: 1.6; color: #f8fafc;">
                    {impact_section}
                </p>
            </div>
        </div>
        """
        st.markdown(hybrid_html, unsafe_allow_html=True)
    else:
        answer_html = f"""
        <div class="glass-panel" style="margin-top: 14px; border: 1px solid rgba(255, 255, 255, 0.15);">
            <div style="font-size: 0.80rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px;">
                ANSWER
            </div>
            <p style="margin: 0; font-size: 1.15rem; line-height: 1.7; color: #f8fafc;">
                {answer_text}
            </p>
            <div style="margin-top: 14px; padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.82rem; color: #94a3b8;">
                Evidence: <strong style="color: #e2e8f0;">{response.evidence_type}</strong> • Verified grounded against authoritative records
            </div>
        </div>
        """
        st.markdown(answer_html, unsafe_allow_html=True)


def render_citations(citations: List[Dict[str, Any]], evidence_pack: Dict[str, Any]) -> None:
    """
    Renders authoritative citations with full provenance details in sleek glass cards.
    Guarantees zero fabricated URLs or non-existent document references.
    """
    if not citations:
        return

    st.markdown("#### 📚 Verified Citations & Provenance")

    evidence_items = evidence_pack.get("evidence_items", [])
    ev_map = {it.get("evidence_id"): it for it in evidence_items if it.get("evidence_id")}
    chunk_map = {it.get("chunk_id"): it for it in evidence_items if it.get("chunk_id")}

    for idx, cit in enumerate(citations, 1):
        ev_id = cit.get("evidence_id")
        src_id = cit.get("source_id", "UNKNOWN_SOURCE")
        doc_id = cit.get("document_id")
        chunk_id = cit.get("chunk_id")
        page = cit.get("page")

        matched_item = ev_map.get(ev_id) or chunk_map.get(chunk_id) or {}
        src_name = matched_item.get("source_name") or src_id
        ev_type = matched_item.get("evidence_type", "REPORTED")
        prov_text = matched_item.get("provenance", f"Source: {src_id}")

        page_str = f" • <strong>Page:</strong> {page}" if page else ""
        doc_str = f" • <strong>Doc ID:</strong> <code>{doc_id}</code>" if doc_id else ""
        chunk_str = f" • <strong>Chunk:</strong> <code>{chunk_id}</code>" if chunk_id else ""

        citation_html = f"""
        <div style="
            background: rgba(15, 23, 42, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-left: 4px solid #38bdf8;
            border-radius: 0 10px 10px 0;
            padding: 12px 18px;
            margin-bottom: 10px;
            backdrop-filter: blur(8px);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div style="font-weight: 700; font-size: 0.95rem; color: #ffffff;">
                    [{idx}] {src_name}
                </div>
                <span style="font-size: 0.76rem; background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.35); padding: 2px 8px; border-radius: 4px; font-weight: 600;">
                    {ev_type}
                </span>
            </div>
            <div style="font-size: 0.82rem; color: #94a3b8; margin-top: 4px;">
                <strong>Evidence ID:</strong> <code>{ev_id or 'N/A'}</code>{doc_str}{page_str}{chunk_str}
            </div>
            <div style="font-size: 0.78rem; color: #64748b; margin-top: 6px; font-family: monospace;">
                Provenance: {prov_text}
            </div>
        </div>
        """
        st.markdown(citation_html, unsafe_allow_html=True)


def render_evidence_pack_inspector(evidence_pack: Dict[str, Any]) -> None:
    """
    Renders an expandable technical inspector allowing users to examine
    the exact evidence items that entered generation.
    """
    items = evidence_pack.get("evidence_items", [])
    count = len(items)

    with st.expander(f"🔎 Inspect Evidence Pack ({count} Authoritative Item{'s' if count != 1 else ''})", expanded=False):
        if not items:
            st.write("No evidence items were retrieved for this query.")
            return

        st.caption("The Evidence Pack is the strict epistemic boundary between retrieval and generation. Only facts listed below were supplied to the synthesizer.")

        for idx, it in enumerate(items, 1):
            ev_id = it.get("evidence_id", f"ITEM_{idx}")
            ev_type = it.get("evidence_type", "REPORTED")
            src_name = it.get("source_name") or it.get("source_id", "Unknown")
            dist = it.get("district")
            year = it.get("year")
            dist_year = f" | District: **{dist}**" if dist else ""
            dist_year += f" | Year: **{year}**" if year else ""

            st.markdown(f"**Item {idx}: `{ev_id}`** — *{src_name}* (`{ev_type}`){dist_year}")

            if it.get("structured_value"):
                st.json(it["structured_value"])

            if it.get("text"):
                st.text_area(
                    label=f"Content ({ev_id})",
                    value=it["text"],
                    height=100,
                    disabled=True,
                    key=f"ev_text_{idx}_{ev_id}"
                )

            st.caption(f"Provenance: {it.get('provenance', 'N/A')}")
            st.divider()


def render_validation_audit(response: RAGResponse) -> None:
    """
    Displays grounding, citation integrity, and execution audit metrics in sleek cards.
    """
    with st.expander("🛡️ Grounding & Verification Audit", expanded=False):
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            val_color = "#34d399" if response.validation_status == "PASSED" else "#f87171"
            st.metric("Validation Status", response.validation_status)

        with col2:
            st.metric("Citation Integrity", f"{response.citation_integrity_pct:.1f}%")

        with col3:
            st.metric("Backend Latency", f"{response.latency_ms:.1f} ms")

        with col4:
            st.metric("Provider", response.provider or "featherless-ai")

        st.markdown(f"**Active Model:** `{response.model or 'Qwen/Qwen2.5-7B-Instruct-1M'}`")

        if response.validation_errors:
            st.error("Validation Violations:")
            for err in response.validation_errors:
                st.write(f"- {err}")

        if response.validation_warnings:
            st.warning("Validation Warnings:")
            for warn in response.validation_warnings:
                st.write(f"- {warn}")


def render_clean_sidebar() -> None:
    """
    Renders the compact, non-technical sidebar requested by the user.
    Avoids dumping technical details while maintaining zero secret exposure.
    """
    with st.sidebar:
        st.markdown("""
        <div style="padding: 10px 0 16px 0;">
            <div style="font-size: 1.4rem; font-weight: 800; color: #ffffff;">
                SYSTEM
            </div>
            <div style="font-size: 0.82rem; color: #94a3b8;">
                Academic RAG Application
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="glass-card-subtle" style="line-height: 1.8; font-size: 0.90rem;">
            <div>📅 <strong>Data:</strong> 2011–2026</div>
            <div>📍 <strong>Regions:</strong> Kangra, Mandi, Shimla, Kullu</div>
            <div>⛈️ <strong>Topics:</strong> Rainfall, Cloudburst, Flash Flood</div>
            <div>🔬 <strong>Mode:</strong> Grounded RAG</div>
            <div>🟢 <strong>Status:</strong> Demo Ready</div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        st.markdown("### 📖 Evidence Types")
        st.markdown("""
        - `OBSERVED`: Direct gauge telemetry
        - `CALCULATED`: Gridded spatial aggregate
        - `REPORTED`: Official disaster / PDNA
        - `MIXED`: Combined quantitative + narrative
        - `INFERRED`: Strictly bounded deduction
        - `INSUFFICIENT`: Inadequate evidence base
        """)


def render_footer() -> None:
    """
    Renders the small unobtrusive academic footer.
    """
    footer_html = """
    <div style="text-align: center; padding: 40px 0 20px 0; color: #64748b; font-size: 0.85rem; letter-spacing: 0.04em;">
        HP Extreme Weather RAG • Local Academic Demonstration
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)
