import fluxer
import sqlite3
import random as rand
import time
import threading

rand.seed(time.time());

user_cache = {};
score_cache = {};
daily_cache = {};

bot = fluxer.Bot(command_prefix="!");
DB_NAME = "user_data.db";

conn = sqlite3.connect(DB_NAME);
conn.execute("PRAGMA journal_mode=WAL;");
conn.close();

conn = sqlite3.connect(DB_NAME);
cursor = conn.cursor();

cursor.execute("""
CREATE TABLE IF NOT EXISTS scores (
    user_id TEXT,
    game TEXT,
    points INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, game)
)
""");

cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_claims (
    user_id TEXT PRIMARY KEY,
    last_claim INTEGER
)
""");

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    last_seen INTEGER
)
""");

conn.commit();
conn.close();

def upsert_user(user):
    conn = sqlite3.connect(DB_NAME);
    cursor = conn.cursor();

    now = int(time.time());
    user_id = str(user.id);

    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, name, last_seen)
    VALUES (?, ?, ?)
    """, (user_id, user.username, now));

    cursor.execute("""
    UPDATE users
    SET name = ?, last_seen = ?
    WHERE user_id = ?
    """, (user.username, now, user_id));

    conn.commit();
    conn.close();

    user_cache[user_id] = user.username;

@bot.event
async def on_ready():
    print("Dionysus is awake!");
    print(f"Dionysus is logged in as {bot.user.username}"); # pyright: ignore[reportOptionalMemberAccess]
    print(f"Dionysus's user_id is {bot.user.id}"); # pyright: ignore[reportOptionalMemberAccess]

def add_points(user_id, points_to_add: int, game: str):
    user_id = str(user_id);

    conn = sqlite3.connect(DB_NAME);
    cursor = conn.cursor();

    cursor.execute("""
    INSERT OR IGNORE INTO scores (user_id, game, points)
    VALUES (?, ?, 0)
    """, (user_id, game));

    cursor.execute("""
    UPDATE scores
    SET points = points + ?
    WHERE user_id = ? AND game = ?
    """, (points_to_add, user_id, game));

    conn.commit();
    conn.close();

    score_cache.setdefault(user_id, {});
    score_cache[user_id][game] = score_cache[user_id].get(game, 0) + points_to_add;

def remove_points(user_id, points_to_add: int, game: str):
    user_id = str(user_id);

    conn = sqlite3.connect(DB_NAME);
    cursor = conn.cursor();

    cursor.execute("""
    INSERT OR IGNORE INTO scores (user_id, game, points)
    VALUES (?, ?, 0)
    """, (user_id, game));

    cursor.execute("""
    UPDATE scores
    SET points = points - ?
    WHERE user_id = ? AND game = ?
    """, (points_to_add, user_id, game));

    conn.commit();
    conn.close();

    score_cache.setdefault(user_id, {});
    score_cache[user_id][game] = score_cache[user_id].get(game, 0) - points_to_add;

def query_points(user_id: int, game: str) -> int:
    return score_cache.get(str(user_id), {}).get(game, 0)

def get_user_name(user_id: int):
    return user_cache.get(str(user_id));

#--- INFO COMMANDS ---
@bot.command()
async def wins(ctx, game: str):
    upsert_user(ctx.author);
    pts = query_points(ctx.author.id, game);
    if pts == 1:
        await ctx.reply(f"You have {pts} win in {game}.");
    else:
        await ctx.reply(f"You have {pts} wins in {game}.");

@bot.command()
async def balance(ctx):
    bal = query_points(ctx.author.id, "balance");
    await ctx.reply(f"You have a balance of ${bal}");

@bot.command()
async def b(ctx):
    await balance(ctx);

@bot.command()
async def bal(ctx):
    await balance(ctx);

@bot.command()
async def leaderboard(ctx, category: str = "wins"):
    upsert_user(ctx.author);

    VALID_LEADERBOARDS = {
        "wins",
        "w",
        "balance",
        "b",
        "guess",
        "rps",
        "scramble",
        "coin_flip",
        "cf",
        "dice",
        "ping",
        "pp",
        "ping_pong"
    };

    leaderboard_data = [];

    category = category.lower();

    if category not in VALID_LEADERBOARDS:
        await ctx.reply(
            "Valid leaderboards: wins, balance, guess, rps, scramble, coin_flip, dice, ping"
        );
        return;

    for user_id, games in score_cache.items():

        if category == "wins" or category == "w":
            score = sum(
                points
                for game, points in games.items()
                if game not in ("balance", "ping")
            );
        elif category == "balance" or category == "b":
            score = games.get("balance", 0);
        elif category == "cf":
            score = games.get("coin_flip", 0);
        elif category == "pp" or category == "ping_pong":
            score = games.get("ping", 0);
        else:
            score = games.get(category, 0);

        leaderboard_data.append((user_id, score));

    leaderboard_data.sort(key=lambda x: x[1], reverse=True);

    if category == "wins" or category == "w":
        title = "Total Wins Leaderboard";
    elif category == "balance" or category == "b":
        title = "Balance Leaderboard";
    elif category == "rps":
        title = "RPS Leaderboard";
    elif category == "coin_flip" or category == "cf":
        title = "Coin Flip Leaderboard";
    elif category == "ping" or category == "pp":
        title = "Ping Pong Leaderboard";
    else:
        title = f"{category.title()} Leaderboard";

    reply_str = title + "\n";

    for i, (user_id, score) in enumerate(leaderboard_data[:10], start=1):
        name = user_cache.get(str(user_id), "Unknown");

        if category == "balance" or category == "b":
            reply_str += f" {i}. {name} - ${score}\n";
        else:
            reply_str += f" {i}. {name} - {score}\n";

    await ctx.reply(reply_str);

@bot.command()
async def lb(ctx, sort: str):
    await leaderboard(ctx, sort);

@bot.command()
async def games(ctx):
    upsert_user(ctx.author);
    await ctx.reply(f"Current games:\n- Ping Pong (`ping`),\n- Guess A Number (`guess`),\n- Coin Flip (`coin_flip`),\n- Craps/Dice (`dice`),\n- Rock-Paper-Scissors (`rps`),\n- Word Scramble (`scramble`)\n");

@bot.command()
async def help(ctx):
    upsert_user(ctx.author);
    await ctx.reply("Commands:\n- `help`, see a list of current commands\n- `games`, see a list of the current games\n- `wins`, see wins for a specific game\n- `balance`, see your current balance\n- `daily`, collect your daily reward\n- `leaderboard`, see the leaderboards for wins or balance");

@bot.command()
async def h(ctx):
    await help(ctx);
#--- INFO COMMANDS ---

#--- PING PONG ---
@bot.command()
async def ping(ctx):
    upsert_user(ctx.author)
    add_points(ctx.author.id, 1, "ping");
    await ctx.reply("Pong!");
#--- PING PONG ---

#--- GUESSING GAME ---
secret_number: int = rand.randint(1, 100);

@bot.command()
async def guess(ctx, number: int):
    global secret_number

    upsert_user(ctx.author)
    if number < secret_number:
        await ctx.reply("Too low!");
    elif number > secret_number:
        await ctx.reply("Too high!");
    else:
        add_points(ctx.author.id, 1, "guess");
        add_points(ctx.author.id, 5, "balance");
        await ctx.reply(f"The secret number was {secret_number}!");
        secret_number = rand.randint(1, 100);
#--- GUESSING GAME ---

#--- COIN FLIP ---
@bot.command()
async def coin_flip(ctx, side: str, bet: int = 0):
    upsert_user(ctx.author)
    user_balance: int = query_points(ctx.author.id, "balance");
    if user_balance < bet:
        await ctx.reply("You don't have enough money! Use `!daily` to get more!");
        return;
    remove_points(ctx.author.id, bet, "balance");

    is_heads = rand.randint(0,1) == 0;
    heads: bool;
    if side.lower() == "heads" or side.lower() == "head" or side.lower() == "h":
        heads = True;
        if heads == is_heads: # both are heads
            add_points(ctx.author.id, bet * 2, "balance");
            add_points(ctx.author.id, 1, "coin_flip");
            await ctx.reply("It is heads! You win!");
        else: # wrong guess
            await ctx.reply("It is tails! You lose!");
    elif side.lower() == "tails" or side.lower() == "tail" or side.lower() == "t":
        heads = False;
        if heads == is_heads: # both are tails
            add_points(ctx.author.id, bet * 2, "balance");
            add_points(ctx.author.id, 1, "coin_flip");
            await ctx.reply("It is tails! You win!");
        else: # wrong guess
            await ctx.reply("It is heads! You lose!");
    else:
        await ctx.reply(f"{side} is not a valid coin side.");
        return;

@bot.command()
async def flip(ctx, side: str, bet: int = 0):
    await coin_flip(ctx, side, bet);

@bot.command()
async def coin(ctx, side: str, bet: int = 0):
    await coin_flip(ctx, side, bet);

@bot.command()
async def c(ctx, side: str, bet: int = 0):
    await coin_flip(ctx, side, bet);
#--- COIN FLIP ---

#--- CRAPS/DICE ---
@bot.command()
async def dice(ctx, bet: int = 0):
    upsert_user(ctx.author)
    user_balance: int = query_points(ctx.author.id, "balance");
    if user_balance < bet:
        await ctx.reply("You don't have enough money! Use `!daily` to get more!");
        return;
    remove_points(ctx.author.id, bet, "balance");
    roll_1: int = rand.randint(1, 6);
    roll_2: int = rand.randint(1, 6);
    sum: int = roll_1 + roll_2;
    if sum == 7 or sum == 11:
        add_points(ctx.author.id, 1, "dice");
        add_points(ctx.author.id, bet * 2, "balance");
        await ctx.reply("You win!");
    elif sum in [2, 3, 12]:
        await ctx.reply("You lose!");
    else:
        await ctx.reply("No dice! Better luck next time!");

@bot.command()
async def r(ctx, bet: int = 0):
    await dice(ctx, bet);

@bot.command()
async def roll(ctx, bet: int = 0):
    await dice(ctx, bet);
#--- CRAPS/DICE ---

#--- RPS ---
@bot.command()
async def rps(ctx, choice: str, bet: int = 0):
    upsert_user(ctx.author)
    user_balance: int = query_points(ctx.author.id, "balance");
    if user_balance < bet:
        await ctx.reply("You don't have enough money! Use `!daily` to get more!");
        return;
    remove_points(ctx.author.id, bet, "balance");
    choices = ["r", "p", "s"];
    idx = rand.randint(0, 2);
    bot_choice = choices[idx];

    choice = choice.lower()[0];
    valid_choices = "rps";
    if choice in valid_choices:
        if choice == bot_choice:
            await ctx.reply("Tie!");
        elif choice == "r" and bot_choice == "s":
            add_points(ctx.author.id, 1, "rps");
            add_points(ctx.author.id, bet * 2, "balance");
            await ctx.reply("You Win!");
        elif choice == "p" and bot_choice == "r":
            add_points(ctx.author.id, 1, "rps");
            add_points(ctx.author.id, bet * 2, "balance");
            await ctx.reply("You Win!");
        elif choice == "s" and bot_choice == "p":
            add_points(ctx.author.id, 1, "rps");
            add_points(ctx.author.id, bet * 2, "balance");
            await ctx.reply("You Win!");
        else:
            await ctx.reply("You Lose!");
    else:
        await ctx.reply(f"{choice} isn't a valid choice!");
#--- RPS ---

#--- WORD SCRAMBLE ---
def get_random_word():
    idx = rand.randint(0, 49);
    words = [
        "plant", "wheel", "short", "tract", "video",
        "salad", "leave", "bacon", "enter", "shine",
        "float", "error", "limit", "chord", "build",
        "track", "equip", "trust", "choke", "entry",
        "flour", "berry", "troop", "lunch", "faint",
        "block", "awful", "queue", "adopt", "trace",
        "split", "upset", "abuse", "press", "cable",
        "woman", "acute", "pride", "raise", "stage",
        "solid", "flush", "mercy", "count", "virus",
        "eject", "ranch", "eagle", "cheek", "grime"
    ]
    return words[idx];

current_word: str = get_random_word();
scrambled = list(current_word);
rand.shuffle(scrambled);

@bot.command()
async def scramble(ctx, guess: str):
    global current_word

    upsert_user(ctx.author)
    await ctx.reply(f"Current word: {scrambled}");
    if guess == current_word:
        add_points(ctx.author.id, 1, "scramble");
        add_points(ctx.author.id, 5, "balance");
        await ctx.reply("Correct!");
        current_word = get_random_word();
    else:
        await ctx.reply("Not quite!");

@bot.command()
async def word(ctx, guess: str):
    await scramble(ctx, guess);

@bot.command()
async def w(ctx, guess: str):
    await scramble(ctx, guess);
#--- WORD SCRAMBLE ---

#--- DAILY ---
DAILY_COOLDOWN = 86400

@bot.command()
async def daily(ctx):
    upsert_user(ctx.author);
    user_id = ctx.author.id;
    now = int(time.time());

    result = daily_cache.get(str(user_id));

    if result is None:
        cursor.execute("""
        INSERT INTO daily_claims (user_id, last_claim)
        VALUES (?, ?)
        """, (user_id, now));

        add_points(user_id, 10, "balance");
        conn.commit();
        conn.close();

        daily_cache[str(user_id)] = now
        await ctx.reply("You received $10!");
    else:
        last_claim = result
        next_claim = last_claim + DAILY_COOLDOWN

        if now >= next_claim:
            cursor.execute("""
            UPDATE daily_claims
            SET last_claim = ?
            WHERE user_id = ?
            """, (now, user_id));

            add_points(user_id, 10, "balance");
            conn.commit();
            conn.close();

            daily_cache[str(user_id)] = now
            await ctx.reply("You received $10!");

        else:
            await ctx.reply(
                f"You can claim your next daily <t:{next_claim}:R>."
            );

@bot.command()
async def day(ctx):
    await daily(ctx);

@bot.command()
async def d(ctx):
    await daily(ctx);
#--- DAILY ---

#--- DATABASE SYNC ---
def sync_database():
    global user_cache, score_cache, daily_cache

    while True:
        conn = sqlite3.connect(DB_NAME);
        cursor = conn.cursor();

        cursor.execute("SELECT user_id, name FROM users");
        user_cache = {row[0]: row[1] for row in cursor.fetchall()};

        cursor.execute("SELECT user_id, game, points FROM scores");
        score_cache.clear();
        for user_id, game, points in cursor.fetchall():
            score_cache.setdefault(user_id, {})[game] = points;

        cursor.execute("SELECT user_id, last_claim FROM daily_claims");
        daily_cache = {row[0]: row[1] for row in cursor.fetchall()};

        conn.close();

        time.sleep(2);

def start_sync_thread():
    t = threading.Thread(target=sync_database, daemon=True);
    t.start();
#--- DATABASE SYNC ---

if __name__ == "__main__":
    with open("./app_token", "r") as token_file:
        start_sync_thread();
        TOKEN = token_file.readline();
        bot.run(TOKEN);