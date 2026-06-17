import sqlite3
import json
from collections import defaultdict

DB_NAME = "user_data.db";

def connect():
    return sqlite3.connect(DB_NAME);

def list_users(cursor):
    cursor.execute("""
        SELECT user_id, name
        FROM users
        ORDER BY last_seen DESC
    """);
    users = cursor.fetchall();

    print("\nUsers:");
    for user_id, name in users:
        display = name if name else "Unknown";
        print(f"{display} ({user_id})");

def find_user_by_name(cursor, name):
    cursor.execute("""
        SELECT user_id, name
        FROM users
        WHERE LOWER(name) LIKE LOWER(?)
    """, (f"%{name}%",));

    rows = cursor.fetchall();

    if not rows:
        print("No users found.");
        return;

    print("\nMatches:");
    for user_id, name in rows:
        print(f"{name} ({user_id})");

def get_user_name(cursor, user_id):
    cursor.execute("""
        SELECT name FROM users WHERE user_id = ?
    """, (user_id,));
    result = cursor.fetchone();
    return result[0] if result else None;

def list_games(cursor):
    cursor.execute("SELECT DISTINCT game FROM scores");
    games = [r[0] for r in cursor.fetchall()];
    print("\nGames:");
    print(games);

def inspect(cursor):
    tables = ["users", "scores", "daily_claims"];

    print("\n=== DATABASE INSPECT ===");

    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM {table}");
            rows = cursor.fetchall();

            print(f"\n[{table}]");
            if not rows:
                print("  (empty)");
                continue;

            for row in rows:
                print(" ", row);

        except sqlite3.OperationalError as e:
            print(f"\n[{table}] ERROR: {e}");

def leaderboard(cursor, game):
    cursor.execute("""
        SELECT user_id, points
        FROM scores
        WHERE game = ?
        ORDER BY points DESC
    """, (game,));

    rows = cursor.fetchall();

    print(f"\nLeaderboard: {game}");
    for i, (user_id, pts) in enumerate(rows, 1):
        name = get_user_name(cursor, user_id) or "Unknown";
        print(f"{i}. {name} ({user_id}) - {pts}");

def total_leaderboard(cursor):
    cursor.execute("""
        SELECT user_id, SUM(points)
        FROM scores
        GROUP BY user_id
        ORDER BY SUM(points) DESC
    """);

    rows = cursor.fetchall();

    print("\nTotal Leaderboard:");
    for i, (user_id, pts) in enumerate(rows, 1):
        name = get_user_name(cursor, user_id) or "Unknown";
        print(f"{i}. {name} ({user_id}) - {pts}");

def find_user(cursor, user_id):
    cursor.execute("""
        SELECT game, points
        FROM scores
        WHERE user_id = ?
    """, (user_id,));

    rows = cursor.fetchall();

    name = get_user_name(cursor, user_id);

    if not rows:
        print(f"No data for user {user_id}");
        return;

    print(f"\nUser: {name or 'Unknown'} ({user_id})");
    for game, pts in rows:
        print(f"- {game}: {pts}");

def profile(cursor, user_id):
    cursor.execute("""
        SELECT game, points
        FROM scores
        WHERE user_id = ?
    """, (user_id,));

    rows = cursor.fetchall();

    name = get_user_name(cursor, user_id);

    if not rows:
        print(f"No profile found for {user_id}");
        return;

    total = sum(r[1] for r in rows);

    cursor.execute("""
        SELECT last_claim
        FROM daily_claims
        WHERE user_id = ?
    """, (user_id,));

    daily = cursor.fetchone();

    print(f"\n=== PROFILE ===");
    print(f"Name: {name or 'Unknown'}");
    print(f"User ID: {user_id}");
    print(f"Total Wins: {total}");

    if daily:
        import time
        last = daily[0];
        next_claim = last + 86400;
        now = int(time.time());

        if now >= next_claim:
            print("Daily: READY");
        else:
            print(f"Daily: cooldown (<t:{next_claim}:R>)");
    else:
        print("Daily: never claimed");

    print("\nGames:");
    for game, pts in rows:
        print(f"  {game}: {pts}");

def modify_wins(cursor, user_id, game, amount):
    cursor.execute("""
        INSERT OR IGNORE INTO scores (user_id, game, points)
        VALUES (?, ?, 0)
    """, (user_id, game));

    cursor.execute("""
        UPDATE scores
        SET points = points + ?
        WHERE user_id = ? AND game = ?
    """, (amount, user_id, game));

    print(f"Updated {user_id} | {game} by {amount}");

def reset_user(cursor, user_id):
    cursor.execute("DELETE FROM scores WHERE user_id = ?", (user_id,));
    print(f"Deleted scores for {user_id}");

def reset_game(cursor, game):
    cursor.execute("DELETE FROM scores WHERE game = ?", (game,));
    print(f"Deleted all data for game {game}");

def export_db(cursor):
    cursor.execute("SELECT user_id, game, points FROM scores");
    scores = cursor.fetchall();

    cursor.execute("SELECT user_id, name FROM users");
    users = cursor.fetchall();

    cursor.execute("SELECT user_id, last_claim FROM daily_claims");
    dailies = cursor.fetchall();

    data = {
        "users": {},
        "scores": defaultdict(dict),
        "daily_claims": {}
    };

    for user_id, name in users:
        data["users"][user_id] = name;

    for user_id, game, points in scores:
        data["scores"][user_id][game] = points;

    for user_id, last_claim in dailies:
        data["daily_claims"][user_id] = last_claim;

    with open("export.json", "w") as f:
        json.dump(data, f, indent=4);

    print("Exported to export.json");

def add(cursor, parts):
    if len(parts) != 4:
        print("Usage: add <user> <game> <amount>");
        return;

    user_id = parts[1];
    game = parts[2];
    amount = int(parts[3]);

    modify_wins(cursor, user_id, game, amount);

def start_cli():
    conn = connect();
    cursor = conn.cursor();

    print("Admin Panel Ready (type 'help')");

    while True:
        command = input("> ").strip();
        parts = command.split();

        if command.lower() in ["exit", "quit", "q"]:
            break;

        match parts:

            case ["help"]:
                print("""
Commands:
  users
  games
  leaderboard <game>
  total
  inspect

  find <user>
  profile <user>

  findname <name>

  add <user> <game> <amount>

  reset user <user>
  reset game <game>

  export
  exit
                """);

            case ["users"]:
                list_users(cursor);

            case ["games"]:
                list_games(cursor);

            case ["inspect"]:
                inspect(cursor);

            case ["total"]:
                total_leaderboard(cursor);

            case ["find", user_id]:
                find_user(cursor, user_id);

            case ["findname", *name_parts]:
                find_user_by_name(cursor, " ".join(name_parts));

            case ["profile", user_id]:
                profile(cursor, user_id);

            case ["reset", "user", user_id]:
                reset_user(cursor, user_id);

            case ["reset", "game", game]:
                reset_game(cursor, game);

            case ["export"]:
                export_db(cursor);

            case ["leaderboard", game]:
                leaderboard(cursor, game);

            case _ if parts[0] == "add":
                add(cursor, parts);

            case _:
                print("Unknown command. Type 'help'.");

        conn.commit();

    conn.close();

if __name__ == "__main__":
    start_cli();