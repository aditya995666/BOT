# # utils/ban_manager.py
# import time

# BANNED_USERS = {}

# def ban_user(user_id: str, reason: str):
#     BANNED_USERS[user_id] = {
#         "reason": reason,
#         "time": time.ctime()
#     }

# def is_banned(user_id: str) -> bool:
#     return user_id in BANNED_USERS
