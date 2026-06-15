#!/usr/bin/env python3
import json, os, threading, time, sqlite3, hashlib, secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from mcstatus import MinecraftServer

SERVER_ADDR = "127.0.0.1"
SERVER_PORT = 16383
USERCACHE = "/root/NewWorldDevelopmentCommittee/usercache.json"
DB_PATH = "/opt/newworld/auth.db"
CATEGORIES = ["综合讨论", "问题反馈", "创意分享", "公告"]

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

cached = {"online": False}
online_players = {}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT DEFAULT '',
        minecraft_id TEXT DEFAULT '',
        role TEXT DEFAULT 'user',
        avatar TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS forum_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        author_id INTEGER NOT NULL,
        author_name TEXT NOT NULL,
        reply_count INTEGER DEFAULT 0,
        category TEXT DEFAULT '综合讨论',
        is_pinned INTEGER DEFAULT 0,
        updated_at TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (author_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS player_stats (
        username TEXT PRIMARY KEY,
        playtime_seconds INTEGER DEFAULT 0,
        first_seen TEXT DEFAULT (datetime('now')),
        last_seen TEXT DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS tech_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tech_key TEXT NOT NULL,
        username TEXT NOT NULL,
        description TEXT DEFAULT '',
        images TEXT DEFAULT '[]',
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS forum_replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        author_id INTEGER NOT NULL,
        author_name TEXT NOT NULL,
        updated_at TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (post_id) REFERENCES forum_posts(id),
        FOREIGN KEY (author_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS reset_tokens (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        badge_key TEXT NOT NULL,
        earned_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, badge_key),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS post_likes (
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (user_id, post_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (post_id) REFERENCES forum_posts(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS post_bookmarks (
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (user_id, post_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (post_id) REFERENCES forum_posts(id)
    )""")
    conn.commit()
    conn.close()

def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for col in [
        "ALTER TABLE forum_posts ADD COLUMN category TEXT DEFAULT '综合讨论'",
        "ALTER TABLE forum_posts ADD COLUMN is_pinned INTEGER DEFAULT 0",
        "ALTER TABLE forum_posts ADD COLUMN updated_at TEXT",
        "ALTER TABLE forum_replies ADD COLUMN updated_at TEXT",
        "ALTER TABLE player_stats ADD COLUMN playtime_seconds INTEGER DEFAULT 0",
        "ALTER TABLE player_stats ADD COLUMN last_seen TEXT",
        "ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT ''",
    ]:
        try:
            c.execute(col)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return salt + ":" + key.hex()

def check_password(password, stored):
    salt, key = stored.split(":", 1)
    return hash_password(password, salt) == stored

def read_history():
    try:
        if os.path.exists(USERCACHE):
            with open(USERCACHE) as f:
                data = json.load(f)
            return [e["name"] for e in data]
    except Exception:
        pass
    return []

def update_playtime(current_players):
    global online_players
    now = int(time.time())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    current_set = set(current_players)

    for player in list(online_players.keys()):
        if player not in current_set:
            start = online_players.pop(player)
            elapsed = now - start
            c.execute("INSERT INTO player_stats (username, playtime_seconds, first_seen, last_seen) VALUES (?, ?, datetime('now'), datetime('now')) ON CONFLICT(username) DO UPDATE SET playtime_seconds = playtime_seconds + ?, last_seen = datetime('now')", (player, elapsed, elapsed))

    for player in current_set:
        if player not in online_players:
            online_players[player] = now
            c.execute("INSERT INTO player_stats (username, playtime_seconds, first_seen, last_seen) VALUES (?, 0, datetime('now'), datetime('now')) ON CONFLICT(username) DO UPDATE SET last_seen = datetime('now')", (player,))

    conn.commit()
    conn.close()

def poll():
    global cached
    try:
        server = MinecraftServer(SERVER_ADDR, SERVER_PORT)
        status = server.status()
        sample = []
        if status.players.sample:
            sample = [p.name for p in status.players.sample]
        cached = {
            "online": True, "players": {"online": status.players.online, "max": status.players.max, "list": sample},
            "history": read_history(), "version": status.version.name, "motd": str(status.description),
        }
        update_playtime(sample)
    except Exception as e:
        cached = {"online": False, "history": read_history(), "error": str(e)}

def poll_loop():
    while True:
        poll()
        time.sleep(60)

def get_user_from_token(token):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT u.id, u.username, u.email, u.minecraft_id, u.role, u.created_at, u.avatar FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.token = ?", (token,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "email": row[2], "minecraft_id": row[3], "role": row[4], "created_at": row[5], "avatar": row[6] or ""}
    return None

def get_avatar(username):
    path = "/var/www/newworld/uploads/avatars/" + username + ".png"
    if os.path.exists(path):
        return "/uploads/avatars/" + username + ".png"
    return ""

def require_auth(headers):
    token = headers.get("Authorization", "")
    if token.startswith("Bearer "):
        token = token[7:]
    return get_user_from_token(token)

TIER_ITEMS = {
    "中级阶段": ["刷石机", "刷铁机", "自动熔炉组", "甘蔗/竹子机", "简易袭击塔", "基础应力网", "自动压印", "自动粉碎", "自动农场", "自动屠宰"],
    "高级阶段": ["全自动树场", "无限刷石机", "高效率刷铁机", "猪灵交易所", "守卫者农场", "凋零骷髅农场", "袭击塔 V2", "自动冶炼阵列", "动力合成", "自动农夫乐事", "烟花产线", "附魔室", "史莱姆农场", "永久基地"],
    "尖端科技": ["列车系统", "物流仓储", "弹药生产线", "区块加载器", "超级应力网", "村民交易所", "物品分类系统", "经验熔炉", "炮台防御", "跨洲铁路", "探索装备"],
    "终极目标": ["国家首都", "国际合作", "军事力量", "全物品收集", "末影农场", "信标网络", "基建狂魔"],
}
TIER_ICONS = {"中级阶段": "⚙️", "高级阶段": "🏭", "尖端科技": "🚂", "终极目标": "💎"}
TIER_NAMES_CN = {"中级阶段": "中级阶段", "高级阶段": "高级阶段", "尖端科技": "尖端科技", "终极目标": "终极目标"}

def add_message(user_id, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (user_id, content) VALUES (?, ?)", (user_id, content))
    conn.commit()
    conn.close()

def check_and_award_badges(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_row = c.fetchone()
    if not user_row:
        conn.close()
        return
    user_id = user_row[0]
    for tier_name, items in TIER_ITEMS.items():
        placeholders = ",".join("?" for _ in items)
        c.execute("SELECT DISTINCT tech_key FROM tech_submissions WHERE username = ? AND tech_key IN (" + placeholders + ") AND status = 'approved'", (username,) + tuple(items))
        approved = {r[0] for r in c.fetchall()}
        if all(item in approved for item in items):
            badge_key = "tier_" + tier_name
            try:
                c.execute("INSERT OR IGNORE INTO badges (user_id, badge_key) VALUES (?, ?)", (user_id, badge_key))
            except sqlite3.IntegrityError:
                pass
    conn.commit()
    conn.close()

def require_admin(headers):
    user = require_auth(headers)
    if user and user["role"] == "腐竹":
        return user
    return None

def json_response(handler, data, status=200):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(data).encode())

class Handler(BaseHTTPRequestHandler):
    timeout = 30

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):
        if self.path.startswith("/api/upload"):
            self._handle_upload()
            return

        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        data = json.loads(body) if body else {}

        if self.path == "/api/register":
            username = data.get("username", "").strip()
            password = data.get("password", "")
            email = data.get("email", "")
            if len(username) < 2 or len(password) < 4:
                json_response(self, {"ok": False, "error": "用户名至少2个字符，密码至少4个字符"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", (username, hash_password(password), email))
                conn.commit()
                token = secrets.token_hex(32)
                c.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, c.lastrowid))
                conn.commit()
                json_response(self, {"ok": True, "token": token, "username": username})
            except sqlite3.IntegrityError:
                json_response(self, {"ok": False, "error": "用户名已存在"})
            conn.close()
            return

        if self.path == "/api/login":
            username = data.get("username", "").strip()
            password = data.get("password", "")
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            if row and check_password(password, row[2]):
                token = secrets.token_hex(32)
                c.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, row[0]))
                conn.commit()
                json_response(self, {"ok": True, "token": token, "username": row[1]})
            else:
                json_response(self, {"ok": False, "error": "用户名或密码错误"})
            conn.close()
            return

        if self.path == "/api/logout":
            token = data.get("token", "")
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True})
            return

        if self.path == "/api/update_profile":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            if "minecraft_id" in data:
                c.execute("UPDATE users SET minecraft_id = ? WHERE id = ?", (data["minecraft_id"], user["id"]))
            if "email" in data:
                c.execute("UPDATE users SET email = ? WHERE id = ?", (data["email"], user["id"]))
            if "avatar_url" in data:
                c.execute("UPDATE users SET avatar = ? WHERE id = ?", (data["avatar_url"], user["id"]))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True})
            return

        if self.path == "/api/forum/post":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            title = data.get("title", "").strip()
            content = data.get("content", "").strip()
            category = data.get("category", "综合讨论").strip()
            if category not in CATEGORIES:
                category = "综合讨论"
            if not title or not content:
                json_response(self, {"ok": False, "error": "标题和内容不能为空"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO forum_posts (title, content, author_id, author_name, category) VALUES (?, ?, ?, ?, ?)",
                      (title, content, user["id"], user["username"], category))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True})
            return

        if self.path == "/api/forum/edit":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            post_id = data.get("post_id")
            title = data.get("title", "").strip()
            content = data.get("content", "").strip()
            if not post_id or not content:
                json_response(self, {"ok": False, "error": "参数错误"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT author_id FROM forum_posts WHERE id = ?", (post_id,))
            row = c.fetchone()
            if not row:
                json_response(self, {"ok": False, "error": "帖子不存在"})
                conn.close()
                return
            if row[0] != user["id"] and user["role"] != "腐竹":
                json_response(self, {"ok": False, "error": "无权编辑"})
                conn.close()
                return
            if title:
                c.execute("UPDATE forum_posts SET title = ?, content = ?, updated_at = datetime('now') WHERE id = ?", (title, content, post_id))
            else:
                c.execute("UPDATE forum_posts SET content = ?, updated_at = datetime('now') WHERE id = ?", (content, post_id))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True})
            return

        if self.path == "/api/forum/reply/edit":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            reply_id = data.get("reply_id")
            content = data.get("content", "").strip()
            if not reply_id or not content:
                json_response(self, {"ok": False, "error": "参数错误"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT author_id FROM forum_replies WHERE id = ?", (reply_id,))
            row = c.fetchone()
            if not row:
                json_response(self, {"ok": False, "error": "回复不存在"})
                conn.close()
                return
            if row[0] != user["id"] and user["role"] != "腐竹":
                json_response(self, {"ok": False, "error": "无权编辑"})
                conn.close()
                return
            c.execute("UPDATE forum_replies SET content = ?, updated_at = datetime('now') WHERE id = ?", (content, reply_id))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True})
            return

        if self.path == "/api/forum/delete":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            post_id = data.get("post_id")
            if not post_id:
                json_response(self, {"ok": False, "error": "参数错误"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT author_id FROM forum_posts WHERE id = ?", (post_id,))
            row = c.fetchone()
            if not row:
                json_response(self, {"ok": False, "error": "帖子不存在"})
                conn.close()
                return
            if row[0] != user["id"] and user["role"] != "腐竹":
                json_response(self, {"ok": False, "error": "无权删除"})
                conn.close()
                return
            c.execute("DELETE FROM forum_replies WHERE post_id = ?", (post_id,))
            c.execute("DELETE FROM forum_posts WHERE id = ?", (post_id,))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True})
            return

        if self.path == "/api/forum/reply":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            post_id = data.get("post_id")
            content = data.get("content", "").strip()
            if not post_id or not content:
                json_response(self, {"ok": False, "error": "参数错误"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO forum_replies (post_id, content, author_id, author_name) VALUES (?, ?, ?, ?)",
                      (post_id, content, user["id"], user["username"]))
            c.execute("UPDATE forum_posts SET reply_count = reply_count + 1 WHERE id = ?", (post_id,))
            c.execute("SELECT author_id, title FROM forum_posts WHERE id = ?", (post_id,))
            post_row = c.fetchone()
            if post_row and post_row[0] != user["id"]:
                msg = "💬 你的帖子《" + post_row[1] + "》有了新回复"
                c.execute("INSERT INTO messages (user_id, content) VALUES (?, ?)", (post_row[0], msg))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True})
            return

        if self.path == "/api/forum/pin":
            user = require_admin(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "无权操作"})
                return
            post_id = data.get("post_id")
            if not post_id:
                json_response(self, {"ok": False, "error": "参数错误"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT is_pinned FROM forum_posts WHERE id = ?", (post_id,))
            row = c.fetchone()
            if not row:
                json_response(self, {"ok": False, "error": "帖子不存在"})
                conn.close()
                return
            new_val = 0 if row[0] else 1
            c.execute("UPDATE forum_posts SET is_pinned = ? WHERE id = ?", (new_val, post_id))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True, "is_pinned": new_val})
            return

        if self.path == "/api/change_password":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE id = ?", (user["id"],))
            row = c.fetchone()
            if not check_password(data.get("old_password", ""), row[0]):
                json_response(self, {"ok": False, "error": "原密码错误"})
                conn.close()
                return
            new_pw = data.get("new_password", "")
            if len(new_pw) < 4:
                json_response(self, {"ok": False, "error": "新密码至少4个字符"})
                conn.close()
                return
            c.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(new_pw), user["id"]))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True})
            return

        if self.path.startswith("/api/upload"):
            json_response(self, {"ok": False, "error": "请使用 POST"})
            return

        if self.path == "/api/tech/submit":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            tech_key = data.get("tech_key", "").strip()
            description = data.get("description", "").strip()
            images = data.get("images", [])
            if not tech_key:
                json_response(self, {"ok": False, "error": "参数错误"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, status FROM tech_submissions WHERE tech_key = ? AND username = ?", (tech_key, user["username"]))
            row = c.fetchone()
            if row:
                c.execute("UPDATE tech_submissions SET description = ?, images = ?, status = 'pending', updated_at = datetime('now') WHERE id = ?", (description, json.dumps(images), row[0]))
            else:
                c.execute("INSERT INTO tech_submissions (tech_key, username, description, images) VALUES (?, ?, ?, ?)", (tech_key, user["username"], description, json.dumps(images)))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True})
            return

        if self.path == "/api/tech/review":
            user = require_admin(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "无权操作"})
                return
            sub_id = data.get("id")
            status = data.get("status", "")
            if not sub_id or status not in ("approved", "rejected"):
                json_response(self, {"ok": False, "error": "参数错误"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT username, tech_key FROM tech_submissions WHERE id = ?", (sub_id,))
            sub_row = c.fetchone()
            if not sub_row:
                conn.close()
                json_response(self, {"ok": False, "error": "提交不存在"})
                return
            submitter_name, tech_key = sub_row
            c.execute("UPDATE tech_submissions SET status = ?, updated_at = datetime('now') WHERE id = ?", (status, sub_id))
            c.execute("SELECT id FROM users WHERE username = ?", (submitter_name,))
            uid_row = c.fetchone()
            if uid_row:
                label = "✅ 已通过" if status == "approved" else "❌ 未通过"
                msg = "🔬 你的科技树提交《" + tech_key + "》" + label
                c.execute("INSERT INTO messages (user_id, content) VALUES (?, ?)", (uid_row[0], msg))
            conn.commit()
            conn.close()
            if status == "approved":
                check_and_award_badges(submitter_name)
            json_response(self, {"ok": True})
            return

        if self.path == "/api/admin/message":
            user = require_admin(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "无权操作"})
                return
            target_user_id = data.get("user_id")
            content = data.get("content", "").strip()
            if not target_user_id or not content:
                json_response(self, {"ok": False, "error": "参数错误"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO messages (user_id, content) VALUES (?, ?)", (target_user_id, content))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True})
            return

        if self.path == "/api/forgot_password":
            email = data.get("email", "").strip()
            if not email:
                json_response(self, {"ok": False, "error": "请输入邮箱"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, username FROM users WHERE email = ?", (email,))
            row = c.fetchone()
            if not row:
                conn.close()
                json_response(self, {"ok": False, "error": "该邮箱未注册"})
                return
            user_id, username = row
            token = secrets.token_hex(32)
            c.execute("DELETE FROM reset_tokens WHERE user_id = ?", (user_id,))
            c.execute("INSERT INTO reset_tokens (token, user_id, expires_at) VALUES (?, ?, datetime('now', '+1 hour'))", (token, user_id))
            conn.commit()
            conn.close()
            reset_link = "https://newworld.largemodel.online/reset_password?token=" + token
            json_response(self, {"ok": True, "reset_link": reset_link, "message": "重置链接已生成，请访问该链接修改密码（生产环境应通过邮件发送）"})
            return

        if self.path == "/api/reset_password":
            token = data.get("token", "").strip()
            new_password = data.get("new_password", "")
            if not token or len(new_password) < 4:
                json_response(self, {"ok": False, "error": "参数错误或密码太短"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT user_id FROM reset_tokens WHERE token = ? AND expires_at > datetime('now')", (token,))
            row = c.fetchone()
            if not row:
                conn.close()
                json_response(self, {"ok": False, "error": "链接无效或已过期"})
                return
            c.execute("UPDATE users SET password = ? WHERE id = ?", (hash_password(new_password), row[0]))
            c.execute("DELETE FROM reset_tokens WHERE token = ?", (token,))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True, "message": "密码已重置，请重新登录"})
            return

        if self.path == "/api/forum/like":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            post_id = data.get("post_id")
            if not post_id:
                json_response(self, {"ok": False, "error": "参数错误"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT 1 FROM post_likes WHERE user_id = ? AND post_id = ?", (user["id"], post_id))
            liked = c.fetchone()
            if liked:
                c.execute("DELETE FROM post_likes WHERE user_id = ? AND post_id = ?", (user["id"], post_id))
                conn.commit()
                conn.close()
                json_response(self, {"ok": True, "liked": False})
            else:
                c.execute("INSERT INTO post_likes (user_id, post_id) VALUES (?, ?)", (user["id"], post_id))
                conn.commit()
                conn.close()
                json_response(self, {"ok": True, "liked": True})
            return

        if self.path == "/api/forum/bookmark":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            post_id = data.get("post_id")
            if not post_id:
                json_response(self, {"ok": False, "error": "参数错误"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT 1 FROM post_bookmarks WHERE user_id = ? AND post_id = ?", (user["id"], post_id))
            bookmarked = c.fetchone()
            if bookmarked:
                c.execute("DELETE FROM post_bookmarks WHERE user_id = ? AND post_id = ?", (user["id"], post_id))
                conn.commit()
                conn.close()
                json_response(self, {"ok": True, "bookmarked": False})
            else:
                c.execute("INSERT INTO post_bookmarks (user_id, post_id) VALUES (?, ?)", (user["id"], post_id))
                conn.commit()
                conn.close()
                json_response(self, {"ok": True, "bookmarked": True})
            return

        json_response(self, {"ok": False})

    def _handle_upload(self):
        user = require_auth(self.headers)
        if not user:
            json_response(self, {"ok": False, "error": "未登录"})
            return
        import uuid
        filename = self.headers.get("X-Filename", "image.png")
        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"):
            json_response(self, {"ok": False, "error": "不支持的图片格式"})
            return
        if ext in (".bmp", ".svg"):
            ext = ".png"
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        if len(body) > 5 * 1024 * 1024:
            json_response(self, {"ok": False, "error": "图片太大，最大5MB"})
            return
        name = uuid.uuid4().hex + ext
        dest = "/var/www/newworld/uploads/" + name
        with open(dest, "wb") as f:
            f.write(body)
        url = "/uploads/" + name
        json_response(self, {"ok": True, "url": url})

    def do_GET(self):
        if self.path == "/api/status":
            json_response(self, cached)
            return

        if self.path == "/api/me":
            user = require_auth(self.headers)
            if user:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM messages WHERE user_id = ? AND is_read = 0", (user["id"],))
                unread = c.fetchone()[0]
                c.execute("SELECT id, title, reply_count, created_at FROM forum_posts WHERE author_id = ? ORDER BY created_at DESC", (user["id"],))
                posts = [{"id": r[0], "title": r[1], "reply_count": r[2], "created_at": r[3]} for r in c.fetchall()]
                conn.close()
                user["unread"] = unread
                user["posts"] = posts
            json_response(self, {"ok": bool(user), "user": user})
            return

        if self.path == "/api/messages":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, content, is_read, created_at FROM messages WHERE user_id = ? ORDER BY created_at DESC", (user["id"],))
            rows = c.fetchall()
            c.execute("UPDATE messages SET is_read = 1 WHERE user_id = ? AND is_read = 0", (user["id"],))
            conn.commit()
            conn.close()
            json_response(self, {"ok": True, "messages": [{"id": r[0], "content": r[1], "is_read": r[2], "created_at": r[3]} for r in rows]})
            return

        if self.path == "/api/activity":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT 'post', id, title, author_name, created_at FROM forum_posts ORDER BY created_at DESC LIMIT 15")
            posts = [{"type": "post", "id": r[1], "title": r[2], "username": r[3], "time": r[4]} for r in c.fetchall()]
            c.execute("SELECT 'reply', fr.id, fp.title, fr.author_name, fr.created_at, fp.id FROM forum_replies fr JOIN forum_posts fp ON fr.post_id = fp.id ORDER BY fr.created_at DESC LIMIT 15")
            replies = [{"type": "reply", "id": r[1], "title": r[2], "username": r[3], "time": r[4], "post_id": r[5]} for r in c.fetchall()]
            c.execute("SELECT 'tech', id, tech_key, username, status, created_at FROM tech_submissions ORDER BY created_at DESC LIMIT 15")
            tech = [{"type": "tech", "id": r[1], "tech_key": r[2], "username": r[3], "status": r[4], "time": r[5]} for r in c.fetchall()]
            c.execute("SELECT 'user', id, username, created_at FROM users ORDER BY created_at DESC LIMIT 10")
            users = [{"type": "user", "id": r[1], "username": r[2], "time": r[3]} for r in c.fetchall()]
            conn.close()
            all_activity = sorted(posts + replies + tech + users, key=lambda x: x["time"], reverse=True)[:50]
            json_response(self, {"ok": True, "activity": all_activity})
            return

        if self.path.startswith("/api/forum/posts"):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            parts = self.path.split("/")

            current_user = require_auth(self.headers)
            current_user_id = current_user["id"] if current_user else None

            if len(parts) == 5 and parts[4].isdigit():
                pid = int(parts[4])
                c.execute("SELECT fp.id, fp.title, fp.content, fp.author_name, fp.reply_count, fp.category, fp.is_pinned, fp.created_at, fp.updated_at, u.avatar FROM forum_posts fp LEFT JOIN users u ON fp.author_name = u.username WHERE fp.id = ?", (pid,))
                row = c.fetchone()
                post = None
                if row:
                    post = {
                        "id": row[0], "title": row[1], "content": row[2], "author_name": row[3],
                        "reply_count": row[4], "category": row[5], "is_pinned": bool(row[6]),
                        "created_at": row[7], "updated_at": row[8], "author_avatar": row[9] or ""
                    }
                    c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id = ?", (pid,))
                    post["like_count"] = c.fetchone()[0]
                    if current_user_id:
                        c.execute("SELECT 1 FROM post_likes WHERE user_id = ? AND post_id = ?", (current_user_id, pid))
                        post["is_liked"] = bool(c.fetchone())
                        c.execute("SELECT 1 FROM post_bookmarks WHERE user_id = ? AND post_id = ?", (current_user_id, pid))
                        post["is_bookmarked"] = bool(c.fetchone())
                    else:
                        post["is_liked"] = False
                        post["is_bookmarked"] = False
                    c.execute("SELECT fr.id, fr.content, fr.author_name, fr.created_at, fr.updated_at, u.avatar FROM forum_replies fr LEFT JOIN users u ON fr.author_name = u.username WHERE fr.post_id = ? ORDER BY fr.created_at", (pid,))
                    replies = [{"id": r[0], "content": r[1], "author_name": r[2], "created_at": r[3], "updated_at": r[4], "author_avatar": r[5] or ""} for r in c.fetchall()]
                    post["replies"] = replies
                conn.close()
                json_response(self, {"ok": bool(post), "post": post})
                return

            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            category = qs.get("category", [None])[0]
            search = qs.get("q", [None])[0]
            page = int(qs.get("page", ["1"])[0])
            limit = int(qs.get("limit", ["20"])[0])
            offset = (page - 1) * limit

            where = []
            params = []
            if category and category in CATEGORIES:
                where.append("category = ?")
                params.append(category)
            if search:
                where.append("(title LIKE ? OR content LIKE ?)")
                params.extend(["%" + search + "%", "%" + search + "%"])

            where_sql = "WHERE " + " AND ".join(where) if where else ""

            c.execute("SELECT COUNT(*) FROM forum_posts " + where_sql, params)
            total = c.fetchone()[0]

            c.execute("SELECT fp.id, fp.title, fp.author_name, fp.reply_count, fp.category, fp.is_pinned, fp.created_at, u.avatar FROM forum_posts fp LEFT JOIN users u ON fp.author_name = u.username " + where_sql + " ORDER BY fp.is_pinned DESC, fp.created_at DESC LIMIT ? OFFSET ?", params + [limit, offset])
            posts = [{"id": r[0], "title": r[1], "author_name": r[2], "reply_count": r[3], "category": r[4], "is_pinned": bool(r[5]), "created_at": r[6], "author_avatar": r[7] or ""} for r in c.fetchall()]
            if current_user_id:
                for p in posts:
                    c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id = ?", (p["id"],))
                    p["like_count"] = c.fetchone()[0]
                    c.execute("SELECT 1 FROM post_bookmarks WHERE user_id = ? AND post_id = ?", (current_user_id, p["id"]))
                    p["is_bookmarked"] = bool(c.fetchone())
            conn.close()
            json_response(self, {"ok": True, "posts": posts, "total": total, "page": page, "limit": limit, "categories": CATEGORIES})
            return

        if self.path == "/api/forum/bookmarks":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT fp.id, fp.title, fp.author_name, fp.reply_count, fp.category, fp.created_at, u.avatar FROM post_bookmarks pb JOIN forum_posts fp ON pb.post_id = fp.id LEFT JOIN users u ON fp.author_name = u.username WHERE pb.user_id = ? ORDER BY pb.created_at DESC", (user["id"],))
            posts = [{"id": r[0], "title": r[1], "author_name": r[2], "reply_count": r[3], "category": r[4], "created_at": r[5], "author_avatar": r[6] or ""} for r in c.fetchall()]
            conn.close()
            json_response(self, {"ok": True, "posts": posts})
            return

        if self.path == "/api/gallery":
            upload_dir = "/var/www/newworld/uploads/"
            images = []
            try:
                for f in sorted(os.listdir(upload_dir), key=lambda x: -os.path.getmtime(os.path.join(upload_dir, x))):
                    if f == ".gitkeep" or f == "avatars":
                        continue
                    ext = os.path.splitext(f)[1].lower()
                    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                        fp = os.path.join(upload_dir, f)
                        images.append({"url": "/uploads/" + f, "size": os.path.getsize(fp)})
            except Exception:
                pass
            json_response(self, {"ok": True, "images": images})
            return

        if self.path.startswith("/api/badges"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            username = qs.get("username", [None])[0]
            if not username:
                json_response(self, {"ok": False, "error": "缺少 username 参数"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            if not row:
                conn.close()
                json_response(self, {"ok": False, "error": "用户不存在"})
                return
            c.execute("SELECT badge_key, earned_at FROM badges WHERE user_id = ? ORDER BY earned_at", (row[0],))
            badges = [{"key": r[0], "earned_at": r[1]} for r in c.fetchall()]
            conn.close()
            json_response(self, {"ok": True, "badges": badges})
            return

        if self.path == "/api/leaderboard":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()

            c.execute("SELECT ps.username, ps.playtime_seconds, ps.first_seen, ps.last_seen, u.avatar FROM player_stats ps LEFT JOIN users u ON ps.username = u.username ORDER BY ps.playtime_seconds DESC LIMIT 50")
            playtime = [{"username": r[0], "playtime_seconds": r[1], "first_seen": r[2], "last_seen": r[3], "avatar": r[4] or ""} for r in c.fetchall()]

            c.execute("SELECT author_name, COUNT(*) as cnt FROM forum_posts GROUP BY author_name ORDER BY cnt DESC LIMIT 50")
            post_counts = {r[0]: r[1] for r in c.fetchall()}
            c.execute("SELECT author_name, COUNT(*) as cnt FROM forum_replies GROUP BY author_name ORDER BY cnt DESC LIMIT 50")
            reply_counts = {r[0]: r[1] for r in c.fetchall()}
            all_forum_users = set(list(post_counts.keys()) + list(reply_counts.keys()))
            avatars = {}
            if all_forum_users:
                placeholders = ",".join("?" for _ in all_forum_users)
                c.execute("SELECT username, avatar FROM users WHERE username IN (" + placeholders + ")", list(all_forum_users))
                avatars = {r[0]: r[1] or "" for r in c.fetchall()}
            forum = sorted([{"username": u, "posts": post_counts.get(u, 0), "replies": reply_counts.get(u, 0), "total": post_counts.get(u, 0) + reply_counts.get(u, 0), "avatar": avatars.get(u, "")} for u in all_forum_users], key=lambda x: -x["total"])[:50]

            usercache_path = USERCACHE
            first_joined = []
            try:
                if os.path.exists(usercache_path):
                    with open(usercache_path) as f:
                        data = json.load(f)
                    first_joined = [{"username": e["name"]} for e in data]
            except Exception:
                pass

            conn.close()
            json_response(self, {"ok": True, "playtime": playtime, "forum": forum, "history": first_joined})
            return

        if self.path.startswith("/api/tech/submissions"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            tech_key = qs.get("tech_key", [None])[0]
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            if tech_key:
                c.execute("SELECT id, tech_key, username, description, images, status, created_at FROM tech_submissions WHERE tech_key = ? ORDER BY status ASC, created_at DESC", (tech_key,))
            else:
                c.execute("SELECT id, tech_key, username, description, images, status, created_at FROM tech_submissions ORDER BY created_at DESC")
            subs = [{"id": r[0], "tech_key": r[1], "username": r[2], "description": r[3], "images": json.loads(r[4]), "status": r[5], "created_at": r[6]} for r in c.fetchall()]
            conn.close()
            json_response(self, {"ok": True, "submissions": subs})
            return

        if self.path == "/api/tech/mine":
            user = require_auth(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "未登录"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, tech_key, username, description, images, status, created_at FROM tech_submissions WHERE username = ? ORDER BY created_at DESC", (user["username"],))
            subs = [{"id": r[0], "tech_key": r[1], "username": r[2], "description": r[3], "images": json.loads(r[4]), "status": r[5], "created_at": r[6]} for r in c.fetchall()]
            conn.close()
            json_response(self, {"ok": True, "submissions": subs})
            return

        if self.path == "/api/tech/pending":
            user = require_admin(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "无权访问"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, tech_key, username, description, images, status, created_at FROM tech_submissions WHERE status = 'pending' ORDER BY created_at DESC")
            subs = [{"id": r[0], "tech_key": r[1], "username": r[2], "description": r[3], "images": json.loads(r[4]), "status": r[5], "created_at": r[6]} for r in c.fetchall()]
            conn.close()
            json_response(self, {"ok": True, "submissions": subs})
            return

        if self.path == "/api/admin/users":
            user = require_admin(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "无权访问"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, username, minecraft_id, role, created_at, avatar FROM users ORDER BY created_at DESC")
            users = [{"id": r[0], "username": r[1], "minecraft_id": r[2], "role": r[3], "created_at": r[4], "avatar": r[5] or ""} for r in c.fetchall()]
            conn.close()
            json_response(self, {"ok": True, "users": users})
            return

        if self.path == "/api/admin/posts":
            user = require_admin(self.headers)
            if not user:
                json_response(self, {"ok": False, "error": "无权访问"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, title, author_name, reply_count, category, is_pinned, created_at FROM forum_posts ORDER BY created_at DESC LIMIT 50")
            posts = [{"id": r[0], "title": r[1], "author_name": r[2], "reply_count": r[3], "category": r[4], "is_pinned": bool(r[5]), "created_at": r[6]} for r in c.fetchall()]
            conn.close()
            json_response(self, {"ok": True, "posts": posts})
            return

        if self.path.startswith("/api/user"):
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            username = qs.get("username", [None])[0]
            if not username:
                json_response(self, {"ok": False, "error": "缺少 username 参数"})
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, username, minecraft_id, role, avatar, created_at FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            if not row:
                conn.close()
                json_response(self, {"ok": False, "error": "用户不存在"})
                return
            user_data = {"id": row[0], "username": row[1], "minecraft_id": row[2] or "", "role": row[3], "avatar": row[4] or "", "created_at": row[5]}
            c.execute("SELECT COUNT(*) FROM forum_posts WHERE author_name = ?", (username,))
            post_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM forum_replies WHERE author_name = ?", (username,))
            reply_count = c.fetchone()[0]
            c.execute("SELECT playtime_seconds FROM player_stats WHERE username = ?", (username,))
            pt = c.fetchone()
            playtime_seconds = pt[0] if pt else 0
            conn.close()
            user_data["post_count"] = post_count
            user_data["reply_count"] = reply_count
            user_data["playtime_seconds"] = playtime_seconds
            json_response(self, {"ok": True, "user": user_data})
            return

        json_response(self, {"ok": False})

init_db()
migrate_db()
threading.Thread(target=poll_loop, daemon=True).start()
poll()
server = ThreadingHTTPServer(("127.0.0.1", 9001), Handler)
server.socket.listen(128)
server.serve_forever()
