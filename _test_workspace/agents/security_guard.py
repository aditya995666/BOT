# # agents/security_guard.py
# from agents.moderation_agent import moderate_content
# from utils.ban_manager import ban_user, is_banned

# def security_check(user_id: str, content: str):
#     # Already banned
#     if is_banned(user_id):
#         raise PermissionError("🚫 Your ID is permanently banned.")

#     result = moderate_content(content)

#     if result["action"] == "BAN":
#         ban_user(user_id, result["verdict"])
#         raise PermissionError("🚫 Community guidelines violated. ID banned.")
