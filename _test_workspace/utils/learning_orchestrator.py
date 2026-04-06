"""
Learning Orchestrator - Coordinates all learning activities
The maestro of self-improvement
"""
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
import schedule
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents.self_improvement_engine import self_improvement_engine
from utils.performance_tracker import performance_tracker
from memory.episodic_memory import episodic_memory
from brain.neural_engine import neural_engine

@dataclass
class LearningTask:
    """A learning task to be executed"""
    id: str
    name: str
    description: str
    task_type: str  # "analysis", "improvement", "optimization", "cleanup"
    priority: int  # 1-5, 5 being highest
    estimated_duration: int  # seconds
    dependencies: List[str]  # IDs of tasks this depends on
    status: str  # "pending", "running", "completed", "failed"
    result: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class LearningOrchestrator:
    """
    Orchestrates all learning activities across the system
    - Schedules learning tasks
    - Manages dependencies
    - Coordinates between different learning components
    - Ensures learning doesn't interfere with normal operation
    """
    
    def __init__(self):
        self.tasks: Dict[str, LearningTask] = {}
        self.task_queue = []
        self.running_tasks = set()
        self.completed_tasks = []
        self.failed_tasks = []
        
        # Execution pool
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        # Learning modules
        self.modules = {
            "performance_analysis": self._run_performance_analysis,
            "pattern_learning": self._run_pattern_learning,
            "agent_optimization": self._run_agent_optimization,
            "memory_cleanup": self._run_memory_cleanup,
            "neural_retraining": self._run_neural_retraining,
            "system_health_check": self._run_system_health_check
        }
        
        # Schedules
        self.schedules = {
            "hourly": ["performance_analysis", "system_health_check"],
            "daily": ["pattern_learning", "memory_cleanup"],
            "weekly": ["agent_optimization", "neural_retraining"]
        }
        
        # Statistics
        self.stats = {
            "total_tasks_created": 0,
            "total_tasks_completed": 0,
            "total_tasks_failed": 0,
            "avg_task_duration": 0,
            "last_learning_cycle": None,
            "learning_impact_score": 0.5  # 0-1, how much learning is helping
        }
        
        # Learning goals
        self.learning_goals = {
            "improve_success_rate": 0.85,  # Target success rate
            "reduce_response_time": 2.0,   # Target response time in seconds
            "increase_user_satisfaction": 0.8,  # Target user satisfaction
            "reduce_error_rate": 0.1       # Target error rate
        }
        
        # Start background scheduler
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        print("✅ Learning Orchestrator initialized")
    
    def create_task(self,
                   name: str,
                   description: str,
                   task_type: str,
                   priority: int = 3,
                   dependencies: Optional[List[str]] = None) -> str:
        """
        Create a new learning task
        Returns task ID
        """
        task_id = f"task_{int(time.time())}_{len(self.tasks)}"
        
        task = LearningTask(
            id=task_id,
            name=name,
            description=description,
            task_type=task_type,
            priority=priority,
            estimated_duration=self._estimate_duration(task_type),
            dependencies=dependencies or [],
            status="pending"
        )
        
        self.tasks[task_id] = task
        self.task_queue.append(task_id)
        
        # Sort queue by priority
        self.task_queue.sort(
            key=lambda tid: (self.tasks[tid].priority, 
                           self.tasks[tid].created_at),
            reverse=True
        )
        
        self.stats["total_tasks_created"] += 1
        
        # Log task creation
        self._log_event("task_created", {
            "task_id": task_id,
            "name": name,
            "type": task_type,
            "priority": priority
        })
        
        return task_id
    def process_interaction(self, interaction_data):
        """
    Compatibility wrapper for research agent auto-learning
    """

        try:
            intent = interaction_data.get("intent", "general")

        # Use existing targeted learning system
            created_tasks = self.run_targeted_learning(
            problem_area=intent,
            urgency="normal"
        )

            return {
            "status": "learning_started",
            "tasks_created": created_tasks
        }

        except Exception as e:
            print("❌ LearningOrchestrator process_interaction error:", e)
            return {
            "status": "error",
            "message": str(e)
        }
    
    def run_scheduled_learning(self, frequency: str = "hourly"):
        """
        Run scheduled learning tasks
        """
        if frequency not in self.schedules:
            print(f"❌ Unknown frequency: {frequency}")
            return
        
        tasks_to_run = self.schedules[frequency]
        
        print(f"🔄 Running {frequency} learning tasks: {tasks_to_run}")
        
        for task_name in tasks_to_run:
            if task_name in self.modules:
                task_id = self.create_task(
                    name=f"{frequency}_{task_name}",
                    description=f"Scheduled {frequency} {task_name}",
                    task_type=task_name,
                    priority=2  # Medium priority for scheduled tasks
                )
                print(f"  📋 Created task: {task_id}")
        
        # Process queue
        self._process_queue()
    
    def run_targeted_learning(self,
                             agent_name: Optional[str] = None,
                             problem_area: Optional[str] = None,
                             urgency: str = "normal") -> List[str]:
        """
        Run targeted learning for specific agent or problem
        Returns list of task IDs created
        """
        created_tasks = []
        
        if agent_name:
            # Create tasks for specific agent
            tasks = [
                self.create_task(
                    name=f"deep_analysis_{agent_name}",
                    description=f"Deep analysis of {agent_name} performance",
                    task_type="performance_analysis",
                    priority=4 if urgency == "high" else 3,
                    dependencies=[]
                ),
                self.create_task(
                    name=f"optimization_{agent_name}",
                    description=f"Optimization suggestions for {agent_name}",
                    task_type="agent_optimization",
                    priority=4 if urgency == "high" else 3,
                    dependencies=[f"deep_analysis_{agent_name}"]
                )
            ]
            created_tasks.extend(tasks)
        
        if problem_area:
            # Create task for specific problem
            task_id = self.create_task(
                name=f"investigate_{problem_area}",
                description=f"Investigate and fix {problem_area}",
                task_type="pattern_learning",
                priority=5 if urgency == "high" else 3,
                dependencies=[]
            )
            created_tasks.append(task_id)
        
        # Process queue
        if created_tasks:
            self._process_queue()
        
        return created_tasks
    
    def get_learning_progress(self) -> Dict[str, Any]:
        """Get current learning progress"""
        pending = sum(1 for t in self.tasks.values() if t.status == "pending")
        running = sum(1 for t in self.tasks.values() if t.status == "running")
        completed = len(self.completed_tasks)
        failed = len(self.failed_tasks)
        
        # Calculate progress towards goals
        goal_progress = {}
        current_perf = performance_tracker.get_performance_report(days=7)
        
        for goal, target in self.learning_goals.items():
            if goal == "improve_success_rate":
                current = current_perf.get("success_rate", 0)
                progress = min(1.0, current / target) if target > 0 else 0
                goal_progress[goal] = {
                    "current": current,
                    "target": target,
                    "progress": progress,
                    "needs_attention": current < target * 0.9
                }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "tasks": {
                "pending": pending,
                "running": running,
                "completed": completed,
                "failed": failed,
                "total_created": self.stats["total_tasks_created"]
            },
            "queue_size": len(self.task_queue),
            "stats": self.stats,
            "goal_progress": goal_progress,
            "recent_completed": [
                asdict(t) for t in self.completed_tasks[-5:]
            ] if self.completed_tasks else [],
            "recent_failed": [
                asdict(t) for t in self.failed_tasks[-3:]
            ] if self.failed_tasks else []
        }
    
    def stop_learning(self):
        """Stop all learning activities gracefully"""
        print("🛑 Stopping learning orchestrator...")
        
        # Stop accepting new tasks
        self.executor.shutdown(wait=False)
        
        # Mark running tasks as failed
        for task_id in list(self.running_tasks):
            task = self.tasks.get(task_id)
            if task:
                task.status = "failed"
                task.completed_at = datetime.now()
                self.failed_tasks.append(task)
                self.running_tasks.remove(task_id)
        
        print("✅ Learning orchestrator stopped")
    
    
    def _process_queue(self):
        """Process task queue"""
        if not self.task_queue:
            return
        
        # Check which tasks can run (dependencies satisfied)
        runnable_tasks = []
        for task_id in self.task_queue[:10]:  # Check first 10
            task = self.tasks[task_id]
            
            if task.status != "pending":
                continue
            
            # Check dependencies
            dependencies_met = True
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != "completed":
                    dependencies_met = False
                    break
            
            if dependencies_met:
                runnable_tasks.append(task_id)
        
        # Submit runnable tasks
        for task_id in runnable_tasks[:3]:  # Max 3 concurrent
            if task_id not in self.running_tasks:
                self._execute_task(task_id)
    
    def _execute_task(self, task_id: str):
        """Execute a learning task"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        
        # Check if already running or completed
        if task.status in ["running", "completed", "failed"]:
            return
        
        # Update task status
        task.status = "running"
        task.started_at = datetime.now()
        self.running_tasks.add(task_id)
        self.task_queue.remove(task_id)
        
        # Submit to executor
        future = self.executor.submit(self._run_task, task)
        future.add_done_callback(
            lambda f: self._task_completed_callback(task_id, f)
        )
        
        self._log_event("task_started", {
            "task_id": task_id,
            "name": task.name,
            "type": task.task_type
        })
    
    def _run_task(self, task: LearningTask) -> Dict[str, Any]:
        """Run the actual task"""
        try:
            # Get the appropriate module
            if task.task_type in self.modules:
                result = self.modules[task.task_type](task)
            else:
                result = {"error": f"Unknown task type: {task.task_type}"}
            
            return {
                "success": True,
                "result": result,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }
    
    def _task_completed_callback(self, task_id: str, future):
        """Callback when task completes"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        task.completed_at = datetime.now()
        
        try:
            task_result = future.result(timeout=10)
            
            if task_result["success"]:
                task.status = "completed"
                task.result = task_result["result"]
                self.completed_tasks.append(task)
                self.stats["total_tasks_completed"] += 1
                
                # Calculate duration
                if task.started_at:
                    duration = (task.completed_at - task.started_at).total_seconds()
                    # Update average duration
                    old_avg = self.stats["avg_task_duration"]
                    total_completed = self.stats["total_tasks_completed"]
                    self.stats["avg_task_duration"] = (
                        (old_avg * (total_completed - 1) + duration) / total_completed
                    )
                
                self._log_event("task_completed", {
                    "task_id": task_id,
                    "name": task.name,
                    "duration": duration if task.started_at else None,
                    "result_summary": str(task.result)[:100] if task.result else None
                })
                
                # Update learning impact score
                self._update_learning_impact(task)
                
            else:
                task.status = "failed"
                task.result = {"error": task_result["error"]}
                self.failed_tasks.append(task)
                self.stats["total_tasks_failed"] += 1
                
                self._log_event("task_failed", {
                    "task_id": task_id,
                    "name": task.name,
                    "error": task_result["error"]
                })
                
        except Exception as e:
            task.status = "failed"
            task.result = {"error": f"Callback error: {str(e)}"}
            self.failed_tasks.append(task)
            self.stats["total_tasks_failed"] += 1
            
            self._log_event("task_failed", {
                "task_id": task_id,
                "name": task.name,
                "error": str(e)
            })
        
        finally:
            # Remove from running tasks
            if task_id in self.running_tasks:
                self.running_tasks.remove(task_id)
            
            # Process next tasks
            self._process_queue()
    
    def _run_performance_analysis(self, task: LearningTask) -> Dict[str, Any]:
        """Analyze system performance"""
        print(f"📊 Running performance analysis: {task.name}")
        
        # Get performance data
        daily_report = performance_tracker.get_performance_report(days=1)
        weekly_report = performance_tracker.get_performance_report(days=7)
        
        # Analyze trends
        trends = self._analyze_performance_trends(daily_report, weekly_report)
        
        # Identify issues
        issues = self._identify_performance_issues(daily_report)
        
        # Generate recommendations
        recommendations = self._generate_performance_recommendations(
            daily_report, weekly_report, trends
        )
        
        # Store in episodic memory
        analysis_id = episodic_memory.store(
            content=json.dumps({
                "trends": trends,
                "issues": issues,
                "recommendations": recommendations
            }, indent=2),
            agent_used="learning_orchestrator",
            success=True,
            emotional_context={"curiosity": 0.8, "confidence": 0.7},
            tags=["performance_analysis", "learning", "system"]
        )
        
        return {
            "analysis_id": analysis_id,
            "trends": trends,
            "issues_found": len(issues),
            "recommendations_generated": len(recommendations),
            "daily_success_rate": daily_report.get("success_rate", 0),
            "weekly_success_rate": weekly_report.get("success_rate", 0)
        }
    
    def _run_pattern_learning(self, task: LearningTask) -> Dict[str, Any]:
        """Learn patterns from episodic memory"""
        print(f"🔍 Running pattern learning: {task.name}")
        
        # Learn success patterns
        success_pattern_id = episodic_memory.learn_pattern(
            agent_name="all",
            pattern_type="success_patterns",
            pattern_data={}
        )
        
        # Learn failure patterns
        failure_pattern_id = episodic_memory.learn_pattern(
            agent_name="all",
            pattern_type="failure_patterns",
            pattern_data={}
        )
        
        # Learn emotional patterns
        emotion_pattern_id = episodic_memory.learn_pattern(
            agent_name="all",
            pattern_type="emotional_patterns",
            pattern_data={}
        )
        
        # Get memory stats
        memory_stats = episodic_memory.get_memory_stats()
        
        return {
            "success_pattern_id": success_pattern_id,
            "failure_pattern_id": failure_pattern_id,
            "emotion_pattern_id": emotion_pattern_id,
            "memory_stats": memory_stats,
            "patterns_learned": 3
        }
    
    def _run_agent_optimization(self, task: LearningTask) -> Dict[str, Any]:
        """Optimize agent performance"""
        print(f"⚡ Running agent optimization: {task.name}")
        
        # Get all agents that need optimization
        agents_needing_optimization = []
        
        # Check each agent's performance
        performance_report = performance_tracker.get_performance_report(days=7)
        
        for agent_name in performance_report.get("agent_distribution", {}).keys():
            agent_perf = performance_tracker.get_agent_performance(agent_name)
            
            if agent_perf.get("health") in ["needs_attention", "critical"]:
                agents_needing_optimization.append({
                    "agent": agent_name,
                    "health": agent_perf["health"],
                    "success_rate": agent_perf["success_rate"],
                    "issues": agent_perf.get("suggestions", [])
                })
        
        # Generate optimization suggestions
        optimizations = []
        for agent_info in agents_needing_optimization:
            suggestions = self_improvement_engine.generate_improvement_suggestions(
                agent_name=agent_info["agent"],
                metric=None,  # Will be fetched internally
                recent_errors=[]
            )
            
            if suggestions:
                # Implement top suggestion
                top_suggestion = suggestions[0]
                implementation = self_improvement_engine.implement_improvement(
                    top_suggestion
                )
                
                optimizations.append({
                    "agent": agent_info["agent"],
                    "suggestion": top_suggestion.suggested_change,
                    "priority": top_suggestion.priority,
                    "implementation_status": implementation["status"]
                })
        
        return {
            "agents_analyzed": len(performance_report.get("agent_distribution", {})),
            "agents_needing_optimization": len(agents_needing_optimization),
            "optimizations_applied": len(optimizations),
            "details": optimizations
        }
    
    def _run_memory_cleanup(self, task: LearningTask) -> Dict[str, Any]:
        """Clean up and organize memories"""
        print(f"🧹 Running memory cleanup: {task.name}")
        
        # Get memory stats before cleanup
        before_stats = episodic_memory.get_memory_stats()
        
        # Prune memories (handled internally by episodic memory)
        # The episodic memory class automatically prunes when needed
        
        # Organize memories (re-index)
        # This happens automatically in episodic memory
        
        # Get memory stats after cleanup
        after_stats = episodic_memory.get_memory_stats()
        
        # Calculate cleanup impact
        impact = {
            "memories_before": before_stats["total_memories"],
            "memories_after": after_stats["total_memories"],
            "reduction": before_stats["total_memories"] - after_stats["total_memories"],
            "success_rate_change": after_stats["success_rate"] - before_stats["success_rate"],
            "importance_change": after_stats["avg_importance"] - before_stats["avg_importance"]
        }
        
        return {
            "cleanup_performed": "automatic_pruning_and_reindexing",
            "impact": impact,
            "current_memory_stats": after_stats
        }
    
    def _run_neural_retraining(self, task: LearningTask) -> Dict[str, Any]:
        """Retrain neural engine with recent experiences"""
        print(f"🧠 Running neural retraining: {task.name}")
        
        # Get recent experiences from episodic memory
        recent_memories = episodic_memory.recall(
            query="recent experiences",
            limit=50
        )
        
        if not recent_memories:
            return {"message": "No recent memories for retraining"}
        
        # Analyze emotional patterns
        emotional_patterns = {}
        success_memories = [m for m in recent_memories if m.success]
        failure_memories = [m for m in recent_memories if not m.success]
        
        if success_memories:
            avg_success_emotions = defaultdict(float)
            for memory in success_memories:
                for emotion, value in memory.emotional_context.items():
                    avg_success_emotions[emotion] += value
            
            for emotion in avg_success_emotions:
                avg_success_emotions[emotion] /= len(success_memories)
            
            emotional_patterns["success"] = dict(avg_success_emotions)
        
        if failure_memories:
            avg_failure_emotions = defaultdict(float)
            for memory in failure_memories:
                for emotion, value in memory.emotional_context.items():
                    avg_failure_emotions[emotion] += value
            
            for emotion in avg_failure_emotions:
                avg_failure_emotions[emotion] /= len(failure_memories)
            
            emotional_patterns["failure"] = dict(avg_failure_emotions)
        
        # Update neural engine with learned patterns
        # (In a real implementation, this would update neural network weights)
        
        # For now, log the patterns
        pattern_id = episodic_memory.store(
            content=json.dumps(emotional_patterns, indent=2),
            agent_used="learning_orchestrator",
            success=True,
            emotional_context={"curiosity": 0.9, "confidence": 0.8},
            tags=["neural_retraining", "emotional_patterns", "learning"]
        )
        
        return {
            "memories_analyzed": len(recent_memories),
            "success_memories": len(success_memories),
            "failure_memories": len(failure_memories),
            "emotional_patterns_identified": len(emotional_patterns),
            "pattern_id": pattern_id,
            "retraining_status": "patterns_extracted_and_stored"
        }
    
    def _run_system_health_check(self, task: LearningTask) -> Dict[str, Any]:
        """Check overall system health"""
        print(f"🏥 Running system health check: {task.name}")
        
        # Check each component
        components = {
            "episodic_memory": episodic_memory.get_memory_stats(),
            "performance_tracker": performance_tracker.get_performance_report(days=1),
            "self_improvement_engine": self_improvement_engine.get_improvement_report(),
            "learning_orchestrator": self.get_learning_progress()
        }
        
        # Determine health status
        health_status = "healthy"
        issues = []
        
        # Check memory health
        if components["episodic_memory"]["success_rate"] < 0.7:
            health_status = "needs_attention"
            issues.append("Low memory success rate")
        
        # Check performance
        if components["performance_tracker"]["success_rate"] < 0.7:
            health_status = "needs_attention"
            issues.append("Low system success rate")
        
        # Check learning impact
        if self.stats["learning_impact_score"] < 0.3:
            health_status = "needs_attention"
            issues.append("Low learning impact")
        
        # Generate health report
        health_report = {
            "overall_health": health_status,
            "timestamp": datetime.now().isoformat(),
            "components_checked": list(components.keys()),
            "issues_found": issues,
            "recommendations": self._generate_health_recommendations(components, issues),
            "component_details": components
        }
        
        # Store health report
        report_id = episodic_memory.store(
            content=json.dumps(health_report, indent=2),
            agent_used="learning_orchestrator",
            success=health_status == "healthy",
            emotional_context={
                "confidence": 0.9 if health_status == "healthy" else 0.5,
                "focus": 0.8
            },
            tags=["system_health", "monitoring", "diagnostics"]
        )
        
        return {
            "health_status": health_status,
            "issues_found": len(issues),
            "report_id": report_id,
            "components_checked": len(components),
            "details": health_report
        }
    
    def _estimate_duration(self, task_type: str) -> int:
        """Estimate duration for a task type"""
        durations = {
            "performance_analysis": 30,
            "pattern_learning": 45,
            "agent_optimization": 60,
            "memory_cleanup": 20,
            "neural_retraining": 90,
            "system_health_check": 15
        }
        return durations.get(task_type, 30)
    
    def _analyze_performance_trends(self, daily: Dict, weekly: Dict) -> Dict[str, Any]:
        """Analyze performance trends"""
        trends = {}
        
        # Compare daily vs weekly
        if daily.get("success_rate") and weekly.get("success_rate"):
            daily_sr = daily["success_rate"]
            weekly_sr = weekly["success_rate"]
            trends["success_rate_trend"] = "improving" if daily_sr > weekly_sr else "declining"
            trends["success_rate_change"] = daily_sr - weekly_sr
        
        # Agent distribution changes
        daily_agents = set(daily.get("agent_distribution", {}).keys())
        weekly_agents = set(weekly.get("agent_distribution", {}).keys())
        trends["new_agents"] = list(daily_agents - weekly_agents)
        trends["inactive_agents"] = list(weekly_agents - daily_agents)
        
        return trends
    
    def _identify_performance_issues(self, report: Dict) -> List[Dict[str, Any]]:
        """Identify performance issues from report"""
        issues = []
        
        # Low success rate
        if report.get("success_rate", 1) < 0.7:
            issues.append({
                "type": "low_success_rate",
                "severity": "high",
                "metric": report["success_rate"],
                "threshold": 0.7
            })
        
        # High response time
        if report.get("avg_response_time", 0) > 5.0:
            issues.append({
                "type": "high_response_time",
                "severity": "medium",
                "metric": report["avg_response_time"],
                "threshold": 5.0
            })
        
        # Single agent dominating
        agent_dist = report.get("agent_distribution", {})
        if agent_dist:
            total = sum(agent_dist.values())
            top_agent = max(agent_dist.items(), key=lambda x: x[1])
            if top_agent[1] / total > 0.7:  # 70% of all calls
                issues.append({
                    "type": "agent_monopoly",
                    "severity": "low",
                    "agent": top_agent[0],
                    "percentage": top_agent[1] / total
                })
        
        return issues
    
    def _generate_performance_recommendations(self, 
                                            daily: Dict, 
                                            weekly: Dict,
                                            trends: Dict) -> List[Dict[str, Any]]:
        """Generate performance recommendations"""
        recommendations = []
        
        # If success rate is declining
        if trends.get("success_rate_trend") == "declining":
            recommendations.append({
                "type": "investigate_decline",
                "priority": "high",
                "action": "Analyze recent failures to identify root causes",
                "reason": f"Success rate declined by {abs(trends.get('success_rate_change', 0)):.2%}"
            })
        
        # If response time is high
        if daily.get("avg_response_time", 0) > 5.0:
            recommendations.append({
                "type": "optimize_response_time",
                "priority": "medium",
                "action": "Implement caching and optimize slow agents",
                "reason": f"Average response time is {daily['avg_response_time']:.1f}s"
            })
        
        # If new agents appeared
        if trends.get("new_agents"):
            recommendations.append({
                "type": "analyze_new_agents",
                "priority": "low",
                "action": f"Monitor new agents: {', '.join(trends['new_agents'])}",
                "reason": "New agents detected in daily usage"
            })
        
        return recommendations
    
    def _generate_health_recommendations(self, 
                                       components: Dict[str, Any],
                                       issues: List[str]) -> List[Dict[str, Any]]:
        """Generate health recommendations"""
        recommendations = []
        
        for issue in issues:
            if "memory" in issue.lower():
                recommendations.append({
                    "action": "Run memory optimization and cleanup",
                    "priority": "medium",
                    "component": "episodic_memory"
                })
            
            if "success rate" in issue.lower():
                recommendations.append({
                    "action": "Run detailed performance analysis and agent optimization",
                    "priority": "high",
                    "component": "performance_tracker"
                })
            
            if "learning impact" in issue.lower():
                recommendations.append({
                    "action": "Review learning tasks and adjust learning parameters",
                    "priority": "medium",
                    "component": "learning_orchestrator"
                })
        
        return recommendations
    
    def _update_learning_impact(self, task: LearningTask):
        """Update learning impact score based on task results"""
        if not task.result:
            return
        
        # Simple heuristic for learning impact
        impact = 0.0
        
        if task.task_type == "agent_optimization":
            # Check if optimizations were applied
            if task.result.get("optimizations_applied", 0) > 0:
                impact = 0.3
        
        elif task.task_type == "performance_analysis":
            # Check if issues were found
            if task.result.get("issues_found", 0) > 0:
                impact = 0.2
        
        elif task.task_type == "pattern_learning":
            # Pattern learning always has impact
            impact = 0.1
        
        # Update impact score (exponential moving average)
        old_score = self.stats["learning_impact_score"]
        self.stats["learning_impact_score"] = old_score * 0.9 + impact * 0.1
    
    def _run_scheduler(self):
        """Run the scheduling loop"""
        # Schedule hourly tasks
        schedule.every().hour.do(self.run_scheduled_learning, "hourly")
        
        # Schedule daily tasks (at 2 AM)
        schedule.every().day.at("02:00").do(self.run_scheduled_learning, "daily")
        
        # Schedule weekly tasks (Sunday at 3 AM)
        schedule.every().sunday.at("03:00").do(self.run_scheduled_learning, "weekly")
        
        print("⏰ Learning scheduler started")
        
        # Run scheduler loop
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log learning events"""
        # In production, this would write to a log file or database
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = {
            "timestamp": timestamp,
            "event": event_type,
            "data": data
        }
        
        # Simple print for now
        print(f"[LearningLog] {timestamp} {event_type}: {data.get('task_id', 'no_id')}")



# Singleton instance
learning_orchestrator = LearningOrchestrator()

