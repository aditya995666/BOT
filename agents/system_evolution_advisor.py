from datetime import datetime
import inspect
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch


class SystemEvolutionAdvisor:

    def __init__(self, router, llm_client=None, research_agent=None):
        self.router = router
        self.llm_client = llm_client
        self.research_agent = research_agent

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        BASE_DIR = os.path.dirname(BASE_DIR)
        self.history_file = os.path.join(BASE_DIR, "evolution_history.json")
        self.report_dir = os.path.join(BASE_DIR, "evolution_reports")
        os.makedirs(self.report_dir, exist_ok=True)

    # 🔍 SYSTEM SCAN
    def _scan_agents(self):
        agents_info = {}

        for name, fn in self.router.agents.items():
            try:
                source = inspect.getsource(fn)

                agents_info[name] = {
                    "lines_of_code": len(source.split("\n")),
                    "has_error_handling": "except" in source,
                    "complexity": source.count("if "),
                    "async_support": "async " in source,
                    "logging_present": "print(" in source or "logger" in source
                }
            except Exception:
                agents_info[name] = {
                    "lines_of_code": 0,
                    "has_error_handling": False,
                    "complexity": 0,
                    "async_support": False,
                    "logging_present": False
                }

        return agents_info

    # 🌍 GEMINI WEB TREND RESEARCH
    def _research_ai_trends(self):
        if not self.llm_client:
            return self._default_trends()

        prompt = """
        Search the web for the latest AI agent architecture trends (2025-2026).
        Focus on:
        - Multi-agent systems
        - Autonomous AI architectures
        - AI memory systems
        - Tool integration frameworks
        - Self-improving AI loops

        Return ONLY a valid JSON list of short feature keywords.
        Example:
        ["multi_agent_collaboration", "vector_memory"]
        """

        response = self.llm_client.generate(prompt)

        try:
            parsed = json.loads(response)
            if isinstance(parsed, list):
                return parsed
        except:
            pass

        return self._default_trends()

    def _default_trends(self):
        return [
            "multi_agent_collaboration",
            "vector_memory",
            "autonomous_goal_engine",
            "tool_auto_discovery",
            "self_reflection_loop",
            "performance_telemetry",
            "distributed_agents",
            "async_execution",
            "observability_stack"
        ]

    # 🧬 FEATURE EXTRACTION
    def _extract_current_features(self):
        features = []
        router_str = str(self.router.__dict__).lower()
        
        keywords = {
            "goal": "autonomous_goal_engine",
            "vector": "vector_memory",
            "multi": "multi_agent_collaboration",
            "telemetry": "performance_telemetry",
            "async": "async_execution",
            "reflection": "self_reflection_loop"
        }
        
        for key, val in keywords.items():
            if key in router_str:
                features.append(val)

        return features

    # ⚖ GAP ANALYSIS
    def _gap_analysis(self, current, trending):
        return [f for f in trending if f not in current]

    # 📊 SYSTEM SCORE
    def _calculate_system_score(self, agent_report, missing_features):
        base_score = 100

        structural_penalty = sum(
            4 for a in agent_report.values()
            if not a["has_error_handling"]
        )

        complexity_penalty = sum(
            1 for a in agent_report.values()
            if a["complexity"] > 25
        )

        feature_penalty = len(missing_features) * 3

        final = base_score - structural_penalty - complexity_penalty - feature_penalty
        return max(final, 0)

    # 📈 HISTORY STORAGE
    def _save_evolution_snapshot(self, snapshot):
        history = []

        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    history = json.load(f)
            except:
                history = []

        history.append(snapshot)

        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=4)

    # 📊 IMPACT MEASUREMENT
    def _measure_upgrade_impact(self, new_score):
        if not os.path.exists(self.history_file):
            return 0

        with open(self.history_file, "r") as f:
            history = json.load(f)

        if len(history) < 1:
            return 0

        previous_score = history[-1]["system_score"]
        return new_score - previous_score

    # 📉 SCORE GRAPH
    def _generate_score_graph(self):
        if not os.path.exists(self.history_file):
            return None

        with open(self.history_file, "r") as f:
            history = json.load(f)

        scores = [h["system_score"] for h in history]
        timestamps = list(range(len(scores)))

        plt.figure()
        plt.plot(timestamps, scores)
        plt.xlabel("Evolution Cycle")
        plt.ylabel("System Score")
        plt.title("System Evolution Score History")

        graph_path = os.path.join(self.report_dir, "score_history.png")
        plt.savefig(graph_path)
        plt.close()

        return graph_path

    # 📄 PDF REPORT
    def generate_pdf_report(self, analysis, roadmap):
        filename = f"evolution_{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.pdf"
        filepath = os.path.join(self.report_dir, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("<b>Autonomous Evolution Report</b>", styles["Title"]))
        elements.append(Spacer(1, 0.3 * inch))

        elements.append(Paragraph(f"System Score: {analysis['system_score']}", styles["Normal"]))
        elements.append(Paragraph(f"Score Change: {analysis.get('score_change_from_last_cycle', 0)}", styles["Normal"]))
        elements.append(Spacer(1, 0.3 * inch))

        elements.append(Paragraph("<b>Missing Features:</b>", styles["Heading2"]))
        elements.append(Spacer(1, 0.2 * inch))

        missing = analysis.get("missing_advanced_features", [])
        if missing:
            feature_list = [
                ListItem(Paragraph(f, styles["Normal"]))
                for f in missing
            ]
            elements.append(ListFlowable(feature_list))
        else:
            elements.append(Paragraph("No major feature gaps detected.", styles["Normal"]))

        elements.append(Spacer(1, 0.3 * inch))

        elements.append(Paragraph("<b>Roadmap:</b>", styles["Heading2"]))
        elements.append(Spacer(1, 0.2 * inch))

        for key, value in roadmap.items():
            elements.append(Paragraph(f"{key}: {value}", styles["Normal"]))
            elements.append(Spacer(1, 0.15 * inch))

        doc.build(elements)
        return filepath

    # 🧠 MAIN ANALYSIS
    def analyze_system(self):
        timestamp = datetime.now().isoformat()

        agent_report = self._scan_agents()
        trending_features = self._research_ai_trends()
        current_features = self._extract_current_features()
        missing_features = self._gap_analysis(current_features, trending_features)

        system_score = self._calculate_system_score(agent_report, missing_features)
        impact = self._measure_upgrade_impact(system_score)

        snapshot = {
            "timestamp": timestamp,
            "system_score": system_score,
            "missing_features": missing_features
        }

        self._save_evolution_snapshot(snapshot)

        return {
            "success": True,
            "timestamp": timestamp,
            "system_score": system_score,
            "score_change_from_last_cycle": impact,
            "agent_scan": agent_report,
            "current_features": current_features,
            "missing_advanced_features": missing_features,
            "next_evolution_priority": missing_features[:3]
        }

    # 🗺 ROADMAP
    def generate_autonomous_roadmap(self, analysis):
        roadmap = {}

        roadmap["Immediate Upgrade"] = analysis.get("next_evolution_priority", [])
        roadmap["System Score"] = analysis.get("system_score", 0)

        if analysis.get("system_score", 0) > 85:
            roadmap["Status"] = "Advanced AI System"
        elif analysis.get("system_score", 0) > 70:
            roadmap["Status"] = "Growing Intelligence"
        else:
            roadmap["Status"] = "Needs Major Evolution"

        return roadmap

    # 🔁 FULL AUTO CYCLE
    def run_full_evolution_cycle(self):
        analysis = self.analyze_system()
        roadmap = self.generate_autonomous_roadmap(analysis)
        graph = self._generate_score_graph()
        pdf = self.generate_pdf_report(analysis, roadmap)

        return {
            "analysis": analysis,
            "roadmap": roadmap,
            "graph_path": graph,
            "pdf_report": pdf
        }