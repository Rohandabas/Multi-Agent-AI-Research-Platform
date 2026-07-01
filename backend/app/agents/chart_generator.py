"""
ChartGeneratorAgent — creates Plotly charts from extracted structured facts.
Exports charts as PNG images for embedding in the report and PDF.
"""
from __future__ import annotations

import time
import asyncio
from pathlib import Path
from app.agents.base import BaseAgent
from app.schemas.response import AgentResult
from app.schemas.internal import ChartSpec, VerifiedFact
from app.schemas.request import ResearchConfig
from app.errors.agent import ChartException
from app.config.settings import settings


class ChartGeneratorAgent(BaseAgent):
    agent_name = "ChartGeneratorAgent"

    def __init__(self, config: ResearchConfig, job_manager=None):
        super().__init__(config, tools={}, job_manager=job_manager)
        self.charts_dir = Path(settings.OUTPUTS_PATH) / "charts"
        self.charts_dir.mkdir(parents=True, exist_ok=True)

    async def _execute(self, state: dict) -> AgentResult:
        start = time.time()

        plan = state.get("research_plan")
        chart_specs = plan.chart_suggestions if plan else []
        verified_data = state.get("verified_facts", {})
        verified_facts: list[VerifiedFact] = verified_data.get("verified", [])
        job_id = state.get("job_id", "unknown")

        # Auto-generate chart specs from extracted facts if none in plan
        if not chart_specs and verified_facts:
            chart_specs = self._auto_generate_specs(verified_facts)
        elif chart_specs and verified_facts:
            # Populate zero values from verified facts
            for spec in chart_specs:
                if all(v == 0.0 for v in spec.values):
                    new_values = []
                    for label in spec.labels:
                        found_val = 0.0
                        for vf in verified_facts:
                            subj = vf.fact.subject.lower()
                            lbl = label.lower()
                            if lbl in subj or subj in lbl:
                                title_lower = spec.title.lower()
                                attr_lower = vf.fact.attribute.lower()
                                is_revenue = "revenue" in title_lower and ("revenue" in attr_lower or "sales" in attr_lower or "financial" in attr_lower)
                                is_share = ("share" in title_lower or "distribution" in title_lower) and ("share" in attr_lower or "market" in attr_lower)
                                is_growth = "growth" in title_lower or "size" in title_lower
                                
                                if is_revenue or is_share or is_growth or not (("revenue" in title_lower and "share" in attr_lower) or ("share" in title_lower and "revenue" in attr_lower)):
                                    parsed = self._parse_number(vf.fact.value)
                                    if parsed > 0:
                                        found_val = parsed
                                        break
                        new_values.append(found_val)
                    if any(v > 0.0 for v in new_values):
                        max_val = max(new_values)
                        if max_val >= 1e9:
                            new_values = [v / 1e9 for v in new_values]
                            if "billion" not in spec.y_label.lower():
                                spec.y_label = f"{spec.y_label} (in Billions)"
                        elif max_val >= 1e6:
                            new_values = [v / 1e6 for v in new_values]
                            if "million" not in spec.y_label.lower():
                                spec.y_label = f"{spec.y_label} (in Millions)"
                        spec.values = new_values

        if not chart_specs:
            self.log_info("No chart specifications found")
            return AgentResult(
                success=True, agent=self.agent_name,
                data=[], duration_seconds=time.time() - start,
            )

        self.log_info(f"Generating {len(chart_specs)} charts")

        chart_paths = []
        loop = asyncio.get_event_loop()

        for i, spec in enumerate(chart_specs):
            try:
                filename = f"{job_id}_chart_{i+1}_{spec.chart_type}.png"
                output_path = self.charts_dir / filename

                path = await loop.run_in_executor(
                    None, self._render_chart, spec, str(output_path)
                )
                if path:
                    spec.filename = str(output_path)
                    chart_paths.append(str(output_path))
                    self.log_info(f"Chart {i+1}: {spec.title} → {filename}")

            except Exception as e:
                self.log_warning(f"Chart '{spec.title}' failed: {e}")

        return AgentResult(
            success=True,
            agent=self.agent_name,
            data=chart_paths,
            duration_seconds=time.time() - start,
        )

    def _render_chart(self, spec: ChartSpec, output_path: str) -> str | None:
        """Render a Plotly chart and save as PNG. Runs in thread pool."""
        try:
            import plotly.graph_objects as go
            import plotly.express as px

            colors = px.colors.qualitative.Set2

            if spec.chart_type == "bar":
                fig = go.Figure(go.Bar(
                    x=spec.labels,
                    y=spec.values,
                    marker_color=colors[:len(spec.labels)],
                    text=[f"{v:,.1f}" for v in spec.values],
                    textposition="auto",
                ))
            elif spec.chart_type == "pie":
                fig = go.Figure(go.Pie(
                    labels=spec.labels,
                    values=spec.values,
                    marker=dict(colors=colors[:len(spec.labels)]),
                    hole=0.3,
                ))
            elif spec.chart_type == "line":
                fig = go.Figure(go.Scatter(
                    x=spec.labels,
                    y=spec.values,
                    mode="lines+markers",
                    line=dict(color="#6366f1", width=2),
                    marker=dict(size=8),
                ))
            else:
                fig = go.Figure(go.Bar(x=spec.labels, y=spec.values))

            fig.update_layout(
                title=dict(text=spec.title, font=dict(size=16, family="Inter")),
                xaxis_title=spec.x_label,
                yaxis_title=spec.y_label,
                template="plotly_white",
                font=dict(family="Inter, sans-serif", size=12),
                paper_bgcolor="white",
                plot_bgcolor="white",
                margin=dict(l=60, r=40, t=60, b=60),
                width=900,
                height=500,
            )

            fig.write_image(output_path, scale=2, engine="kaleido")
            return output_path

        except Exception as e:
            raise ChartException(f"Plotly render failed: {e}")

    def _auto_generate_specs(self, verified_facts: list[VerifiedFact]) -> list[ChartSpec]:
        """Auto-generate chart specs from verified facts when none are planned."""
        specs = []

        # Group by category
        by_category: dict[str, list[VerifiedFact]] = {}
        for vf in verified_facts:
            cat = vf.fact.category
            by_category.setdefault(cat, []).append(vf)

        # Revenue chart
        revenue_facts = [
            vf for vf in by_category.get("revenue", [])
            if vf.fact.value and any(c.isdigit() for c in vf.fact.value)
        ][:8]
        if len(revenue_facts) >= 2:
            labels = [vf.fact.subject for vf in revenue_facts]
            values = [self._parse_number(vf.fact.value) for vf in revenue_facts]
            if any(v > 0 for v in values):
                specs.append(ChartSpec(
                    chart_type="bar",
                    title="Revenue Comparison",
                    labels=labels,
                    values=values,
                    y_label="Revenue (USD)",
                ))

        # Market share pie chart
        share_facts = [
            vf for vf in by_category.get("market_share", [])
            if vf.fact.value
        ][:8]
        if len(share_facts) >= 2:
            labels = [vf.fact.subject for vf in share_facts]
            values = [self._parse_number(vf.fact.value) for vf in share_facts]
            if any(v > 0 for v in values):
                specs.append(ChartSpec(
                    chart_type="pie",
                    title="Market Share Distribution",
                    labels=labels,
                    values=values,
                ))

        return specs

    def _parse_number(self, value_str: str) -> float:
        """Parse a value string like '$44.9B', '44.9 billion', or '24%' to float."""
        import re
        val_clean = value_str.lower().replace(",", "").replace("$", "").replace("%", "").strip()
        
        multipliers = {
            "trillion": 1e12, "t": 1e12,
            "billion": 1e9, "b": 1e9,
            "million": 1e6, "m": 1e6,
            "thousand": 1e3, "k": 1e3
        }
        
        for suffix, mult in multipliers.items():
            if val_clean.endswith(suffix):
                num_part = val_clean[:-len(suffix)].strip()
                try:
                    return float(num_part) * mult
                except ValueError:
                    pass
            elif suffix in val_clean:
                match = re.search(rf"([\d.]+)\s*{suffix}", val_clean)
                if match:
                    try:
                        return float(match.group(1)) * mult
                    except ValueError:
                        pass
                        
        match = re.search(r"[\d.]+", val_clean)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return 0.0
        return 0.0
