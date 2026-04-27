"""
Self Improvement Engine - Continuously improves system performance
"""

import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import threading


def _safe_print(msg: str) -> None:
    """Avoid UnicodeEncodeError on Windows cp1252 consoles."""
    try:
        print(msg)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        print(msg.encode(enc, errors="replace").decode(enc, errors="replace"))


class SelfImprovementEngine:
    def __init__(self):
        _safe_print("Initializing Self-Improvement Engine...")
        
        # Improvement metrics
        self.improvement_history = []
        self.performance_metrics = {
            "response_times": [],
            "success_rates": [],
            "agent_performance": {},
            "error_patterns": []
        }
        
        # Learning parameters
        self.learning_interval = 60  # seconds
        self.min_interactions_for_learning = 10
        
        # Start background learning thread
        self.learning_active = True
        self.learning_thread = threading.Thread(target=self._background_learning, daemon=True)
        self.learning_thread.start()
        
        _safe_print("Self-Improvement Engine initialized")
    
    def analyze_agent_performance(self, agent_name: str, interaction_data: Dict[str, Any]):
        """Analyze performance of a specific agent"""
        try:
            if agent_name not in self.performance_metrics["agent_performance"]:
                self.performance_metrics["agent_performance"][agent_name] = {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "avg_response_time": 0,
                    "response_times": []
                }
            
            agent_stats = self.performance_metrics["agent_performance"][agent_name]
            agent_stats["total_calls"] += 1
            
            response = interaction_data.get("response", {})
            success = response.get("success", False)
            response_time = response.get("response_time", 0)
            
            if success:
                agent_stats["successful_calls"] += 1
            else:
                agent_stats["failed_calls"] += 1
                # Record error pattern
                error = response.get("error", "unknown")
                self.performance_metrics["error_patterns"].append({
                    "agent": agent_name,
                    "error": error[:100],
                    "timestamp": datetime.now().isoformat(),
                    "query": interaction_data.get("query", "")[:50]
                })
            
            # Update response time
            agent_stats["response_times"].append(response_time)
            if len(agent_stats["response_times"]) > 100:
                agent_stats["response_times"].pop(0)
            
            agent_stats["avg_response_time"] = sum(agent_stats["response_times"]) / len(agent_stats["response_times"])
            
        except Exception as e:
            _safe_print(f"Performance analysis error: {e}")
    
    def learning_cycle(self):
        """Run one learning cycle"""
        _safe_print("Running learning cycle...")
        
        try:
            # Analyze performance trends
            performance_report = self._analyze_performance_trends()
            
            # Identify improvement opportunities
            improvements = self._identify_improvements()
            
            # Generate learning insights
            insights = self._generate_insights()
            
            # Record improvement
            improvement_entry = {
                "timestamp": datetime.now().isoformat(),
                "performance_report": performance_report,
                "improvements_identified": improvements,
                "insights": insights,
                "cycle_number": len(self.improvement_history) + 1
            }
            
            self.improvement_history.append(improvement_entry)
            
            # Limit history size
            if len(self.improvement_history) > 100:
                self.improvement_history = self.improvement_history[-100:]
            
            _safe_print(f"Learning cycle completed. Found {len(improvements)} improvements")
            
            return improvement_entry
            
        except Exception as e:
            _safe_print(f"Learning cycle error: {e}")
            return {"error": str(e)}
    
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends"""
        report = {
            "overall_performance": {},
            "agent_performance": {},
            "issues_detected": []
        }
        
        # Calculate overall success rate
        total_calls = 0
        successful_calls = 0
        
        for agent_name, stats in self.performance_metrics["agent_performance"].items():
            total_calls += stats["total_calls"]
            successful_calls += stats["successful_calls"]
            
            # Agent performance
            success_rate = (stats["successful_calls"] / max(stats["total_calls"], 1)) * 100
            report["agent_performance"][agent_name] = {
                "success_rate": round(success_rate, 2),
                "avg_response_time": round(stats["avg_response_time"], 3),
                "total_calls": stats["total_calls"]
            }
            
            # Detect issues
            if success_rate < 70 and stats["total_calls"] > 5:
                report["issues_detected"].append({
                    "agent": agent_name,
                    "issue": f"Low success rate: {success_rate:.1f}%",
                    "severity": "high" if success_rate < 50 else "medium"
                })
        
        # Overall performance
        overall_success_rate = (successful_calls / max(total_calls, 1)) * 100
        report["overall_performance"] = {
            "success_rate": round(overall_success_rate, 2),
            "total_interactions": total_calls,
            "agents_monitored": len(self.performance_metrics["agent_performance"])
        }
        
        return report
    
    def _identify_improvements(self) -> List[Dict[str, Any]]:
        """Identify potential improvements"""
        improvements = []
        
        # Analyze error patterns
        recent_errors = self.performance_metrics["error_patterns"][-20:]
        error_counts = {}
        
        for error in recent_errors:
            error_key = f"{error['agent']}:{error['error'][:30]}"
            error_counts[error_key] = error_counts.get(error_key, 0) + 1
        
        # Suggest improvements for frequent errors
        for error_key, count in error_counts.items():
            if count >= 3:  # If error occurred 3+ times
                agent, error_msg = error_key.split(":", 1)
                improvements.append({
                    "type": "error_reduction",
                    "agent": agent,
                    "error_pattern": error_msg,
                    "occurrences": count,
                    "suggestion": f"Add error handling for: {error_msg}",
                    "priority": "high" if count >= 5 else "medium"
                })
        
        # Performance improvements
        for agent_name, stats in self.performance_metrics["agent_performance"].items():
            if stats["total_calls"] > 10 and stats["avg_response_time"] > 2.0:
                improvements.append({
                    "type": "performance",
                    "agent": agent_name,
                    "metric": "response_time",
                    "current_value": round(stats["avg_response_time"], 2),
                    "target_value": 1.5,
                    "suggestion": f"Optimize {agent_name} agent for faster responses",
                    "priority": "medium"
                })
        
        return improvements
    
    def _generate_insights(self) -> List[str]:
        """Generate learning insights"""
        insights = []
        
        # Success rate insights
        success_rates = []
        for agent_name, stats in self.performance_metrics["agent_performance"].items():
            if stats["total_calls"] > 5:
                rate = (stats["successful_calls"] / stats["total_calls"]) * 100
                success_rates.append((agent_name, rate))
        
        if success_rates:
            best_agent = max(success_rates, key=lambda x: x[1])
            worst_agent = min(success_rates, key=lambda x: x[1])
            
            insights.append(f"Best performing agent: {best_agent[0]} ({best_agent[1]:.1f}% success)")
            insights.append(f"Needs improvement: {worst_agent[0]} ({worst_agent[1]:.1f}% success)")
        
        # Error pattern insights
        if self.performance_metrics["error_patterns"]:
            recent_errors = self.performance_metrics["error_patterns"][-10:]
            common_error = max(set([e["error"][:20] for e in recent_errors]), 
                             key=[e["error"][:20] for e in recent_errors].count)
            insights.append(f"Most common error: {common_error}...")
        
        return insights
    
    def _background_learning(self):
        """Background learning thread"""
        while self.learning_active:
            time.sleep(self.learning_interval)
            
            # Check if enough data for learning
            total_interactions = sum(
                stats["total_calls"] 
                for stats in self.performance_metrics["agent_performance"].values()
            )
            
            if total_interactions >= self.min_interactions_for_learning:
                try:
                    self.learning_cycle()
                except Exception as e:
                    _safe_print(f"Background learning error: {e}")
    
    def get_improvement_report(self) -> Dict[str, Any]:
        """Get improvement report"""
        return {
            "total_learning_cycles": len(self.improvement_history),
            "recent_improvements": self.improvement_history[-5:] if self.improvement_history else [],
            "current_performance": self._analyze_performance_trends(),
            "system_health": self._get_system_health()
        }
    
    def _get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        health = {
            "status": "healthy",
            "issues": [],
            "recommendations": []
        }
        
        # Check agent health
        for agent_name, stats in self.performance_metrics["agent_performance"].items():
            if stats["total_calls"] > 5:
                success_rate = (stats["successful_calls"] / stats["total_calls"]) * 100
                
                if success_rate < 50:
                    health["status"] = "needs_attention"
                    health["issues"].append(f"{agent_name}: Very low success rate ({success_rate:.1f}%)")
                elif success_rate < 70:
                    health["status"] = "warning"
                    health["recommendations"].append(f"Improve {agent_name} success rate")
        
        return health
    
    def stop(self):
        """Stop the improvement engine"""
        self.learning_active = False
        if self.learning_thread.is_alive():
            self.learning_thread.join(timeout=2)
        _safe_print("Self-Improvement Engine stopped")


# Create global instance
self_improvement_engine = SelfImprovementEngine()