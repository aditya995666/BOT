# utils/agent_dashboard.py

import matplotlib.pyplot as plt

class AgentDashboard:
    """
    Dashboard to visualize agent performance metrics
    """

    @staticmethod
    def plot_performance(performance_metrics):
        agents = performance_metrics.get("agent_performance", {})
        if not agents:
            print("No agent data to display.")
            return

        names = list(agents.keys())
        success_rates = [agents[a]["successful_calls"] / max(agents[a]["total_calls"], 1) * 100 for a in names]
        avg_response_times = [agents[a]["avg_response_time"] for a in names]

        fig, ax1 = plt.subplots(figsize=(10,5))

        ax1.bar(names, success_rates, color='skyblue', label='Success Rate %')
        ax1.set_ylabel("Success Rate (%)")
        ax1.set_ylim(0, 100)
        ax1.set_xticklabels(names, rotation=30)

        ax2 = ax1.twinx()
        ax2.plot(names, avg_response_times, color='red', marker='o', label='Avg Response Time')
        ax2.set_ylabel("Response Time (s)")

        fig.legend(loc="upper right")
        plt.title("Agent Performance Dashboard")
        plt.tight_layout()
        plt.show()
