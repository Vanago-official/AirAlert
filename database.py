import json
import os
import logging

USERS_FILE = "subscribers.json"

class User:
    def __init__(self, user_id: int, muted: bool = False):
        self.user_id = user_id
        self.muted = muted

    def to_dict(self):
        return {"user_id": self.user_id, "muted": self.muted}

    @classmethod
    def from_dict(cls, data: dict):
        return cls(user_id=data["user_id"], muted=data.get("muted", False))

    async def send_alert(self, bot, text: str) -> bool:
        """
        Відправляє сповіщення, якщо користувач не зам'ючений.
        Після успішної відправки автоматично м'ютить користувача.
        Повертає True, якщо повідомлення було успішно відправлено.
        """
        if not self.muted:
            try:
                await bot.send_message(chat_id=self.user_id, text=text)
                self.muted = True
                return True
            except Exception as e:
                logging.error(f"Помилка відправки користувачу {self.user_id}: {e}")
        return False


class UserManager:
    def __init__(self, filepath: str = USERS_FILE):
        self.filepath = filepath
        self.users = {}
        self.load()

    def load(self):
        if not os.path.exists(self.filepath):
            return
        with open(self.filepath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return
                
            if not data:
                return
            
            # Підтримка старого формату бази (якщо там просто список ID [123, 456])
            if isinstance(data[0], int):
                self.users = {uid: User(uid) for uid in data}
            else:
                self.users = {item["user_id"]: User.from_dict(item) for item in data}

    def save(self):
        data = [user.to_dict() for user in self.users.values()]
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def add_user(self, user_id: int):
        if user_id not in self.users:
            self.users[user_id] = User(user_id)
            self.save()

    def remove_user(self, user_id: int):
        if user_id in self.users:
            del self.users[user_id]
            self.save()

    def unmute_user(self, user_id: int) -> bool:
        """Повертає True, якщо юзера розм'ючено, і False якщо він не підписаний"""
        if user_id in self.users:
            self.users[user_id].muted = False
            self.save()
            return True
        return False

    def mute_user(self, user_id: int) -> bool:
        """Повертає True, якщо юзера зам'ючено, і False якщо він не підписаний"""
        if user_id in self.users:
            self.users[user_id].muted = True
            self.save()
            return True
        return False

    def unmute_all_users(self) -> list:
        """Розм'ючує всіх користувачів і повертає список їхніх ID, які були розм'ючені"""
        unmuted_ids = []
        for user in self.users.values():
            if user.muted:
                user.muted = False
                unmuted_ids.append(user.user_id)
        if unmuted_ids:
            self.save()
        return unmuted_ids

    def get_all_users(self):
        return list(self.users.values())

    def get_user(self, user_id: int):
        return self.users.get(user_id)
