import os
import streamlit as st
import plotly.graph_objects as go
import requests
from typing import Optional
from html import escape
from collections import Counter

# Color palette
BG_CARD = "#18181B"
ACCENT_CYAN = "#00E6F2"
ACCENT_BLUE = "#3B82F6"
SEV_CRITICAL = "#EF4444"
SEV_HIGH = "#F59E0B"
SEV_MEDIUM = "#EAB308"
TREND_UP = "#10B981"
TREND_FLAT = "#71717A"
TREND_DOWN = "#EF4444"
CHART_PAPER = "rgba(0,0,0,0)"
CHART_PLOT = "rgba(0,0,0,0)"
CHART_GRID = "#27272A"
CHART_FONT = "#A1A1AA"

BACKEND = os.environ.get("BACKEND_URL", "http://alpha-q-backend:8000")

# Page config
st.set_page_config(
    page_title="Alpha-Q | Fundamental Quant Dashboard",
    page_icon="[A]",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
}

.aq-number {
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: -0.02em;
}

.aq-card {
    background: linear-gradient(180deg, #18181B 0%, #121214 100%);
    border: 1px solid #27272A;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.aq-card:hover { transform: translateY(-2px); border-color: #3F3F46; }

.aq-card-critical { border-left: 4px solid #EF4444; background: linear-gradient(180deg, rgba(239,68,68,0.05) 0%, #121214 100%); }
.aq-card-high { border-left: 4px solid #F59E0B; background: linear-gradient(180deg, rgba(245,158,11,0.05) 0%, #121214 100%); }
.aq-card-medium { border-left: 4px solid #EAB308; background: linear-gradient(180deg, rgba(234,179,8,0.05) 0%, #121214 100%); }

.aq-badge {
    display: inline-block;
    background: #27272A;
    color: #D4D4D8;
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    padding: 2px 6px;
    border-radius: 4px;
    margin-right: 8px;
    border: 1px solid #3F3F46;
}

.aq-tag-new { background: rgba(16, 185, 129, 0.1); color: #10B981; padding: 2px 8px; border-radius: 4px; margin: 2px; display: inline-block; font-size: 11px; border: 1px solid rgba(16, 185, 129, 0.2); font-weight: 500; }
.aq-tag-dropped { background: rgba(239, 68, 68, 0.1); color: #EF4444; padding: 2px 8px; border-radius: 4px; margin: 2px; display: inline-block; font-size: 11px; text-decoration: line-through; border: 1px solid rgba(239, 68, 68, 0.2); }
.aq-tag-current { background: #27272A; color: #A1A1AA; padding: 2px 8px; border-radius: 4px; margin: 2px; display: inline-block; font-size: 11px; border: 1px solid #3F3F46; }

.aq-ticker-meta {
    background: radial-gradient(circle at top left, #27272A 0%, #18181B 100%);
    border: 1px solid #3F3F46;
    border-radius: 6px;
    padding: 12px 14px;
    margin-top: 10px;
    font-size: 13px;
    color: #E4E4E7;
}
.aq-ticker-meta b { font-size: 16px; color: #FAFAFA; font-family: 'JetBrains Mono', monospace; }
.aq-ticker-meta code { background: rgba(255,255,255,0.05); padding: 2px 4px; border-radius: 3px; color: #60A5FA; }
</style>
""", unsafe_allow_html=True)


# API client functions
@st.cache_data(ttl=300)
def fetch_tickers():
    try:
        r = requests.get(f"{BACKEND}/api/v1/tickers", timeout=10)
        r.raise_for_status()
        return r.json()["tickers"]
    except Exception as e:
        st.error(f"Failed to fetch tickers: {e}")
        return []


@st.cache_data(ttl=300)
def fetch_quant(symbol: str):
    try:
        r = requests.get(f"{BACKEND}/api/v1/ticker/{symbol}/quant_scores", timeout=10)
        r.raise_for_status()
        return r.json()["series"]
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            st.error(f"No data found for {symbol}")
        else:
            st.error(f"API error: {e}")
        return []
    except Exception as e:
        st.error(f"Connection error: {e}")
        return []


@st.cache_data(ttl=300)
def fetch_nlp(symbol: str):
    try:
        r = requests.get(f"{BACKEND}/api/v1/ticker/{symbol}/nlp_diff", timeout=10)
        r.raise_for_status()
        return r.json()["series"]
    except Exception:
        return []


@st.cache_data(ttl=300)
def fetch_flags(symbol: str):
    try:
        r = requests.get(f"{BACKEND}/api/v1/ticker/{symbol}/red_flags", timeout=10)
        r.raise_for_status()
        return r.json()["flags"]
    except Exception:
        return []


# Sidebar
with st.sidebar:
    st.markdown("## Alpha-Q")
    st.markdown("*Fundamental Quant Dashboard*")
    st.divider()

    all_meta = fetch_tickers()
    all_symbols = [m["ticker"] for m in all_meta]

    search = st.text_input("Search ticker", placeholder="NVDA, MSFT...")
    filtered = [s for s in all_symbols if search.upper() in s] if search else all_symbols

    if filtered:
        selected = st.selectbox("Select ticker", filtered)
        meta = next((m for m in all_meta if m["ticker"] == selected), None)
        if meta:
            st.markdown(f"""
            <div class="aq-ticker-meta">
                <b>{meta['ticker']}</b><br>
                Tier: <code>{meta.get('tier') or 'N/A'}</code><br>
                Years available: <code>{meta['years_available']}</code>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No tickers match your search")
        selected = None


# Main body
if selected:
    with st.spinner(f"Loading {selected}..."):
        quant_data = fetch_quant(selected)
        nlp_data = fetch_nlp(selected)
        flags_data = fetch_flags(selected)

    col_m1, col_m3, col_m2 = st.columns([2, 1.5, 1.5])

    # M1: Hard Numbers
    with col_m1:
        st.markdown("### M1: Hard Numbers")

        if quant_data:
            years = [d["fiscal_year"] for d in quant_data]
            f_scores = [d.get("f_score") for d in quant_data]
            z_scores = [d.get("z_score") for d in quant_data]
            z_types = [d.get("z_score_type") for d in quant_data]

            if not years:
                st.warning("No valid year data")
            else:
                # F-Score bar chart
                colors = []
                for score in f_scores:
                    if score is None:
                        colors.append(CHART_FONT)
                    elif score <= 2:
                        colors.append(SEV_CRITICAL)
                    elif score <= 5:
                        colors.append(SEV_MEDIUM)
                    else:
                        colors.append(TREND_UP)

                fig_f = go.Figure()
                fig_f.add_trace(go.Bar(x=years, y=f_scores, marker_color=colors))
                fig_f.add_shape(type="line", x0=years[0], x1=years[-1], y0=3, y1=3,
                               line=dict(color=SEV_CRITICAL, dash="dot", width=1))
                fig_f.add_shape(type="line", x0=years[0], x1=years[-1], y0=6, y1=6,
                               line=dict(color=TREND_UP, dash="dot", width=1))
                fig_f.update_layout(
                    title="Piotroski F-Score",
                    paper_bgcolor=CHART_PAPER,
                    plot_bgcolor=CHART_PLOT,
                    font=dict(color=CHART_FONT, family="Inter, sans-serif", size=11),
                    xaxis=dict(gridcolor=CHART_GRID, tickfont=dict(family="JetBrains Mono, monospace")),
                    yaxis=dict(gridcolor=CHART_GRID, range=[0, 9], tickfont=dict(family="JetBrains Mono, monospace")),
                    margin=dict(l=8, r=8, t=32, b=8),
                    showlegend=False,
                )
                st.plotly_chart(fig_f, use_container_width=True)

                # Z-Score line chart
                type_counts = Counter([t for t in z_types if t])
                most_common_type = type_counts.most_common(1)[0][0] if type_counts else "standard"
                threshold = 1.23 if most_common_type == "prime" else 1.81
                fig_z = go.Figure()
                fig_z.add_trace(go.Scatter(
                    x=years, y=z_scores,
                    mode="lines+markers",
                    line=dict(color=ACCENT_BLUE, width=2),
                    marker=dict(size=6, color=ACCENT_BLUE),
                ))
                fig_z.add_shape(type="line", x0=years[0], x1=years[-1], y0=threshold, y1=threshold,
                               line=dict(color=SEV_CRITICAL, dash="dash", width=1.5))
                fig_z.update_layout(
                    title=f"Altman Z-Score (threshold={threshold})",
                    paper_bgcolor=CHART_PAPER,
                    plot_bgcolor=CHART_PLOT,
                    font=dict(color=CHART_FONT, family="Inter, sans-serif", size=11),
                    xaxis=dict(gridcolor=CHART_GRID, tickfont=dict(family="JetBrains Mono, monospace")),
                    yaxis=dict(gridcolor=CHART_GRID, tickfont=dict(family="JetBrains Mono, monospace")),
                    margin=dict(l=8, r=8, t=32, b=8),
                    showlegend=False,
                )
                st.plotly_chart(fig_z, use_container_width=True)

                # DuPont ROE decomposition
                roes = [d.get("roe") for d in quant_data]
                margins = [d.get("net_margin") for d in quant_data]
                turnovers = [d.get("asset_turnover") for d in quant_data]
                multipliers = [d.get("equity_multiplier") for d in quant_data]

                fig_roe = go.Figure()
                fig_roe.add_trace(go.Bar(
                    y=years, x=margins, name="Net Margin",
                    orientation="h", marker_color="#A78BFA"
                ))
                fig_roe.add_trace(go.Bar(
                    y=years, x=turnovers, name="Asset Turnover",
                    orientation="h", marker_color=ACCENT_CYAN
                ))
                fig_roe.add_trace(go.Bar(
                    y=years, x=multipliers, name="Equity Multiplier",
                    orientation="h", marker_color=ACCENT_BLUE
                ))
                fig_roe.update_layout(
                    title="DuPont ROE Decomposition",
                    barmode="stack",
                    paper_bgcolor=CHART_PAPER,
                    plot_bgcolor=CHART_PLOT,
                    font=dict(color=CHART_FONT, family="Inter, sans-serif", size=11),
                    xaxis=dict(gridcolor=CHART_GRID, tickfont=dict(family="JetBrains Mono, monospace")),
                    yaxis=dict(gridcolor=CHART_GRID, tickfont=dict(family="JetBrains Mono, monospace")),
                    margin=dict(l=8, r=8, t=32, b=8),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_roe, use_container_width=True)
        else:
            st.info("No quant data available")

    # M3: Red Flags
    with col_m3:
        st.markdown("### M3: Red Flags")

        if flags_data:
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
            sorted_flags = sorted(flags_data, key=lambda f: (severity_order.get(f["severity"], 3), -f["fiscal_year"]))

            for flag in sorted_flags:
                sev = flag["severity"]
                sev_class = f"aq-card-{sev.lower()}"
                sev_color = {"CRITICAL": SEV_CRITICAL, "HIGH": SEV_HIGH, "MEDIUM": SEV_MEDIUM}.get(sev, CHART_FONT)

                st.markdown(f"""
                <div class="aq-card {sev_class}">
                  <div style="margin-bottom:6px;">
                    <span class="aq-badge">{escape(flag['rule_id'])}</span>
                    <span style="color:{sev_color}; font-size:11px; font-weight:700;">
                      {escape(sev)}
                    </span>
                    <span style="color:#A1A1AA; font-size:11px; float:right;" class="aq-number">
                      FY{flag['fiscal_year']}
                    </span>
                  </div>
                  <div style="color:#FAFAFA; font-size:13px; font-weight:600; margin-bottom:4px; letter-spacing:-0.01em;">
                    {escape(flag['title'])}
                  </div>
                  <div style="color:#A1A1AA; font-size:12px; line-height:1.6;">
                    {escape(flag['detail'])}
                  </div>
                </div>
                """, unsafe_allow_html=True)

            with st.expander("Rule definitions"):
                st.markdown("""
                - **RF-001**: Low F-Score + Negative MDA tone
                - **RF-002**: Sharp F-Score deterioration (>= 3pt drop YoY)
                - **RF-003**: Z-Score distress zone + liquidity concern in text
                - **RF-004**: Earnings-tone divergence (negative margin, positive tone)
                - **RF-005**: Operational emergency (ROE < -10%, efficiency signal)
                """)
        else:
            st.markdown("""
            <div class="aq-card" style="border-left: 4px solid #10B981; background: linear-gradient(180deg, rgba(16,185,129,0.05) 0%, #121214 100%);">
              <div style="color:#10B981; font-size:14px; font-weight:600; letter-spacing:-0.01em;">
                No red flags triggered for this ticker
              </div>
            </div>
            """, unsafe_allow_html=True)

    # M2: Soft Tone
    with col_m2:
        st.markdown("### M2: Soft Tone")

        if nlp_data:
            years_nlp = [d["fiscal_year"] for d in nlp_data]
            sentiments = [d.get("mda_sentiment_score") for d in nlp_data]
            trends = [d.get("sentiment_trend") for d in nlp_data]

            if not years_nlp:
                st.warning("No valid NLP year data")
            else:
                # Sentiment timeline
                fig_sent = go.Figure()
                fig_sent.add_trace(go.Scatter(
                    x=years_nlp, y=sentiments,
                    mode="lines+markers",
                    line=dict(color=ACCENT_CYAN, width=2),
                    marker=dict(size=6, color=ACCENT_CYAN),
                ))
                fig_sent.add_shape(type="line", x0=years_nlp[0], x1=years_nlp[-1], y0=5, y1=5,
                                  line=dict(color=CHART_FONT, dash="dot", width=1))
                fig_sent.update_layout(
                    title="MDA Sentiment Score",
                    paper_bgcolor=CHART_PAPER,
                    plot_bgcolor=CHART_PLOT,
                    font=dict(color=CHART_FONT, family="Inter, sans-serif", size=11),
                    xaxis=dict(gridcolor=CHART_GRID, tickfont=dict(family="JetBrains Mono, monospace")),
                    yaxis=dict(gridcolor=CHART_GRID, range=[1, 10], tickfont=dict(family="JetBrains Mono, monospace")),
                    margin=dict(l=8, r=8, t=32, b=8),
                    showlegend=False,
                )
                st.plotly_chart(fig_sent, use_container_width=True)

                # Latest delta indicator
                latest = nlp_data[-1]
                delta = latest.get("sentiment_delta")
                trend = latest.get("sentiment_trend")
                trend_color = {"improving": TREND_UP, "stable": TREND_FLAT, "deteriorating": TREND_DOWN}.get(trend, CHART_FONT)

                if delta is not None:
                    delta_symbol = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
                    delta_class = "up" if delta > 0 else ("down" if delta < 0 else "flat")
                    st.markdown(f"""
                    <div class="aq-card" style="padding:12px 16px;">
                      <span style="color:#71717A; font-size:11px; text-transform:uppercase; letter-spacing:0.05em;">Latest: FY{latest['fiscal_year']}</span>
                      <span style="color:{trend_color}; float:right; font-weight:600; font-size:14px;" class="aq-number">
                        {delta_symbol} {abs(delta)}
                      </span>
                      <br>
                      <span style="color:{trend_color}; font-size:12px; font-weight:500;">{escape((trend or 'N/A').capitalize())}</span>
                    </div>
                    """, unsafe_allow_html=True)

                # Macro concerns timeline
                st.markdown("**Macro Concerns**")
                for entry in reversed(nlp_data):
                    tags_html = f"<b style='color:#71717A; font-family: \"JetBrains Mono\", monospace;'>FY{entry['fiscal_year']}</b> "
                    concerns = entry.get("macro_concerns", [])
                    new_concerns = entry.get("new_macro_concerns", [])
                    dropped_concerns = entry.get("dropped_macro_concerns", [])

                    for concern in concerns:
                        if concern:
                            cls = "aq-tag-new" if concern in new_concerns else "aq-tag-current"
                            tags_html += f'<span class="{cls}">{escape(concern)}</span> '
                    for concern in dropped_concerns:
                        tags_html += f'<span class="aq-tag-dropped">{escape(concern)}</span> '

                    st.markdown(f'<div style="margin-bottom:6px;">{tags_html}</div>', unsafe_allow_html=True)

                # CapEx tone badge
                capex_tone = latest.get("capex_guidance_tone")
                capex_changed = latest.get("capex_tone_changed")
                badge_color = SEV_HIGH if capex_changed else "#D4D4D8"
                changed_indicator = "<span style='color:#F59E0B; font-size:11px; margin-left:8px;'>[TONE CHANGED]</span>" if capex_changed else ""

                st.markdown(f"""
                <div class="aq-card" style="padding:10px 14px;">
                  <span style="color:#71717A; font-size:11px; text-transform:uppercase; letter-spacing:0.05em;">CapEx Guidance</span>
                  <br>
                  <span style="color:{badge_color}; font-size:13px; font-weight:600; letter-spacing:-0.01em;">
                    {escape(capex_tone or 'N/A')}
                  </span>
                  {changed_indicator}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No NLP data available")
else:
    st.info("Select a ticker from the sidebar to begin analysis")

