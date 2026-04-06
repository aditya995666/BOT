"""
Performance Tracker - Monitor and analyze agent performance
"""
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict
import statistics

class PerformanceTracker:
    def __init__(self):
        self.interactions = []
        self.agent_stats = defaultdict(lambda: {
            "total": 0,
            "success": 0,
            "total_time": 0,
            "errors": [],
            "last_used": None
        })
        
        # Performance thresholds
        self.thresholds = {
            "max_response_time": 10.0,  # seconds
            "min_success_rate": 0.7,
            "max_error_rate": 0.3
        }
        
    def track_interaction(self, interaction: Dict[str, Any]):
        """Track an agent interaction"""
        interaction["id"] = len(self.interactions) + 1
        interaction["tracked_at"] = datetime.now()
        
        self.interactions.append(interaction)
        
        # Update agent stats
        agent = interaction.get("agent", "unknown")
        stats = self.agent_stats[agent]
        
        stats["total"] += 1
        stats["last_used"] = datetime.now()
        
        if interaction.get("success", False):
            stats["success"] += 1
        else:
            stats["errors"].append({
                "error": interaction.get("error", "unknown"),
                "timestamp": datetime.now(),
                "query": interaction.get("query", "")[:100]
            })
        
        stats["total_time"] += interaction.get("response_time", 0)
        
        # Keep only recent errors
        stats["errors"] = stats["errors"][-50:]
        
        # Prune old interactions
        self._prune_old_data()
    
    def get_agent_performance(self, agent_name: str) -> Dict[str, Any]:
        """Get performance metrics for specific agent"""
        if agent_name not in self.agent_stats:
            return {"error": "Agent not found"}
        
        stats = self.agent_stats[agent_name]
        
        if stats["total"] == 0:
            return {
                "agent": agent_name,
                "total_interactions": 0,
                "success_rate": 0,
                "avg_response_time": 0,
                "error_rate": 0,
                "health": "unknown"
            }
        
        success_rate = stats["success"] / stats["total"]
        avg_time = stats["total_time"] / stats["total"] if stats["total"] > 0 else 0
        error_rate = len(stats["errors"]) / max(stats["total"], 1)
        
        # Determine health
        health = "healthy"
        if success_rate < self.thresholds["min_success_rate"]:
            health = "needs_attention"
        if error_rate > self.thresholds["max_error_rate"]:
            health = "critical"
        if avg_time > self.thresholds["max_response_time"]:
            health = "slow"
        
        return {
            "agent": agent_name,
            "total_interactions": stats["total"],
            "success_rate": round(success_rate, 3),
            "avg_response_time": round(avg_time, 3),
            "error_rate": round(error_rate, 3),
            "recent_errors": stats["errors"][-5:],
            "last_used": stats["last_used"].isoformat() if stats["last_used"] else None,
            "health": health,
            "suggestions": self._generate_suggestions(agent_name, stats)
        }
    
    def get_performance_report(self, days: int = 7) -> Dict[str, Any]:
        """Get overall performance report"""
        recent_interactions = [
            i for i in self.interactions
            if datetime.now() - i.get("tracked_at", datetime.now()) < timedelta(days=days)
        ]
        
        if not recent_interactions:
            return {
                "period": f"last_{days}_days",
                "total_interactions": 0,
                "message": "No recent interactions"
            }
        
        total = len(recent_interactions)
        successful = sum(1 for i in recent_interactions if i.get("success", False))
        response_times = [i.get("response_time", 0) for i in recent_interactions]
        
        success_rate = successful / total if total > 0 else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else avg_response_time
        
        # Agent distribution
        agent_distribution = {}
        for i in recent_interactions:
            agent = i.get("agent", "unknown")
            agent_distribution[agent] = agent_distribution.get(agent, 0) + 1
        
        # Health check
        health = "good"
        if success_rate < 0.6:
            health = "poor"
        elif avg_response_time > 5.0:
            health = "slow"
        
        return {
            "period": f"last_{days}_days",
            "total_interactions": total,
            "successful_interactions": successful,
            "success_rate": round(success_rate, 3),
            "avg_response_time": round(avg_response_time, 3),
            "p95_response_time": round(p95_response_time, 3),
            "agent_distribution": agent_distribution,
            "health": health,
            "top_agents": sorted(
                agent_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "recommendations": self._generate_recommendations(recent_interactions)
        }
    
    def _generate_suggestions(self, agent_name: str, stats: Dict) -> List[str]:
        """Generate suggestions for improving agent performance"""
        suggestions = []
        
        success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
        avg_time = stats["total_time"] / stats["total"] if stats["total"] > 0 else 0
        
        if success_rate < 0.7:
            suggestions.append(f"Improve success rate (currently {success_rate:.1%})")
        
        if avg_time > 5.0:
            suggestions.append(f"Optimize response time (currently {avg_time:.1f}s)")
        
        if len(stats["errors"]) > stats["total"] * 0.3:
            suggestions.append("Address frequent errors")
        
        if stats["last_used"] and (datetime.now() - stats["last_used"]).days > 7:
            suggestions.append("Agent rarely used - consider merging with another")
        
        return suggestions
    
    def _generate_recommendations(self, interactions: List[Dict]) -> List[str]:
        """Generate system-wide recommendations"""
        recommendations = []
        
        # Analyze response times
        slow_agents = defaultdict(list)
        for i in interactions:
            if i.get("response_time", 0) > 5.0:
                agent = i.get("agent", "unknown")
                slow_agents[agent].append(i["response_time"])
        
        for agent, times in slow_agents.items():
            if len(times) > 3:
                avg = statistics.mean(times)
                recommendations.append(f"Optimize {agent} - average slow response: {avg:.1f}s")
        
        # Analyze errors
        error_prone_agents = defaultdict(int)
        for i in interactions:
            if not i.get("success", False):
                agent = i.get("agent", "unknown")
                error_prone_agents[agent] += 1
        
        for agent, errors in error_prone_agents.items():
            if errors > 5:
                recommendations.append(f"Fix {agent} - {errors} recent errors")
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _prune_old_data(self):
        """Remove old data to prevent memory issues"""
        cutoff = datetime.now() - timedelta(days=30)
        self.interactions = [
            i for i in self.interactions
            if i.get("tracked_at", datetime.now()) > cutoff
        ]
        
        # Also prune agent stats errors
        for agent in self.agent_stats:
            self.agent_stats[agent]["errors"] = [
                e for e in self.agent_stats[agent]["errors"]
                if datetime.now() - e.get("timestamp", datetime.now()) < timedelta(days=7)
            ]
    
    def export_data(self, filepath: str):
        """Export performance data to file"""
        data = {
            "exported_at": datetime.now().isoformat(),
            "interactions": self.interactions,
            "agent_stats": dict(self.agent_stats),
            "thresholds": self.thresholds
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, default=str, indent=2)
    
    def import_data(self, filepath: str):
        """Import performance data from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.interactions = data.get("interactions", [])
            self.agent_stats = defaultdict(lambda: {
                "total": 0,
                "success": 0,
                "total_time": 0,
                "errors": [],
                "last_used": None
            }, data.get("agent_stats", {}))
            
            print(f"Imported {len(self.interactions)} interactions")
            
        except Exception as e:
            print(f"Import error: {e}")


# Singleton instance
performance_tracker = PerformanceTracker()