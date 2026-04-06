# # agents/agent_guard.py

# from security.defensive_scanner import scan_path

# # Only scan folders that can EXECUTE system-level code
# CRITICAL_PATHS = [
#     "tools",   # execution helpers, shell, subprocess etc.
#     # "brain", # optional – enable only in strict mode
#     # "memory",
#     # "utils",
#     # "agents"  # skipped by default (user code analysis allowed)
# ]

# def preflight_system_scan(
#     skip_agents: bool = True,
#     mode: str = "analysis"   # analysis | execution
# ):
#     """
#     Runs before agent loads or upgrades itself.

#     mode = "analysis"
#         - User pasted code allowed
#         - Dangerous functions allowed IF NOT EXECUTED

#     mode = "execution"
#         - Strict security
#         - Dangerous runtime calls are BLOCKED
#     """

#     paths_to_scan = CRITICAL_PATHS.copy()

#     # Agents folder scanned ONLY in strict execution mode
#     if not skip_agents and mode == "execution":
#         paths_to_scan.append("agents")

#     for path in paths_to_scan:
#         report = scan_path(
#             path=path,
#             mode=mode   # pass context to scanner
#         )

#         if report.get("status") == "CRITICAL":
#             raise RuntimeError(
#                 f"🚨 SYSTEM BLOCKED\n"
#                 f"Path   : {path}\n"
#                 f"Reason : {report.get('details', 'Unsafe runtime code detected')}"
#             )

#     return True
