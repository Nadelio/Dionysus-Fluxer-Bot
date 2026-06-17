import fluxer
import sqlite3
import random as rand
import time

rand.seed(time.time());

bot = fluxer.Bot(command_prefix="!");
DB_NAME = "user_data.db";

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

conn.commit();
conn.close();

@bot.event
async def on_ready():
    print("Dionysus is awake!");
    print(f"Dionysus is logged in as {bot.user.username}");
    print(f"Dionysus's user_id is {bot.user.id}");

def add_points(user_id: int, points_to_add: int, game: str):
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

def remove_points(user_id: int, points_to_add: int, game: str):
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

def query_points(user_id: int, game: str) -> int:
    conn = sqlite3.connect(DB_NAME);
    cursor = conn.cursor();

    cursor.execute("""
    SELECT points
    FROM scores
    WHERE user_id = ? AND game = ?
    """, (user_id, game));

    result = cursor.fetchone();

    if result is None:
        cursor.execute("""
        INSERT INTO scores (user_id, game, points)
        VALUES (?, ?, 0)
        """, (user_id, game));

        conn.commit();
        conn.close();
        return 0;

    conn.close();
    return result[0];

@bot.command()
async def wins(ctx, game: str):
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
async def games(ctx):
    await ctx.reply(f"Current games:\n- Ping Pong (`ping`),\n- Guess A Number (`guess`),\n- Coin Flip (`coin_flip`),\n- Craps/Dice (`dice`),\n- Rock-Paper-Scissors (`rps`),\n- Word Scramble (`scramble`)\n");

@bot.command()
async def help(ctx):
    await ctx.reply("Commands:\n- `help`, see a list of current commands\n- `games`, see a list of the current games\n- `wins`, see wins for a specific game\n- `balance`, see your current balance\n- `daily`, collect your daily reward");

#--- PING PONG ---
@bot.command()
async def ping(ctx):
    add_points(ctx.author.id, 1, "ping");
    await ctx.reply("Pong!");
#--- PING PONG ---

#--- GUESSING GAME ---
secret_number: int = rand.randint(1, 100);

@bot.command()
async def guess(ctx, number: int):
    global secret_number

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
    user_balance: int = query_points(ctx.author.id, "balance");
    if user_balance < bet:
        await ctx.reply("You don't have enough money! Use `!daily` to get more!");
        return;

    is_heads = rand.randint(0,1) == 0;
    heads: bool;
    if side.lower() == "heads" or side.lower() == "head" or side.lower() == "h":
        heads = True;
        if heads == is_heads: # both are heads
            add_points(ctx.author.id, bet * 2, "balance");
            add_points(ctx.author.id, 1, "coin_flip");
            await ctx.reply("It is heads! You win!");
        else: # wrong guess
            remove_points(ctx.author.id, bet, "balance");
            await ctx.reply("It is tails! You lose!");
    elif side.lower() == "tails" or side.lower() == "tail" or side.lower() == "t":
        heads = False;
        if heads == is_heads: # both are tails
            add_points(ctx.author.id, bet * 2, "balance");
            add_points(ctx.author.id, 1, "coin_flip");
            await ctx.reply("It is tails! You win!");
        else: # wrong guess
            remove_points(ctx.author.id, bet, "balance");
            await ctx.reply("It is heads! You lose!");
    else:
        await ctx.reply(f"{side} is not a valid coin side.");
        return;
#--- COIN FLIP ---

#--- CRAPS/DICE ---
@bot.command()
async def dice(ctx, bet: int = 0):
    user_balance: int = query_points(ctx.author.id, "balance");
    if user_balance < bet:
        await ctx.reply("You don't have enough money! Use `!daily` to get more!");
        return;

    roll_1: int = rand.randint(1, 6);
    roll_2: int = rand.randint(1, 6);
    sum: int = roll_1 + roll_2;
    if sum == 7 or sum == 11:
        add_points(ctx.author.id, 1, "dice");
        add_points(ctx.author.id, bet * 2, "balance");
        await ctx.reply("You win!");
    elif sum in [2, 3, 12]:
        remove_points(ctx.author.id, bet, "balance");
        await ctx.reply("You lose!");
    else:
        await ctx.reply("No dice! Better luck next time!");
#--- CRAPS/DICE ---

#--- RPS ---
@bot.command()
async def rps(ctx, choice: str, bet: int = 0):
    user_balance: int = query_points(ctx.author.id, "balance");
    if user_balance < bet:
        await ctx.reply("You don't have enough money! Use `!daily` to get more!");
        return;

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
            add_points(ctx.author.id, 5, "balanace");
            await ctx.reply("You Win!");
        elif choice == "p" and bot_choice == "r":
            add_points(ctx.author.id, 1, "rps");
            add_points(ctx.author.id, 5, "balanace");
            await ctx.reply("You Win!");
        elif choice == "s" and bot_choice == "p":
            add_points(ctx.author.id, 1, "rps");
            add_points(ctx.author.id, 5, "balanace");
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
    await ctx.reply(f"Current word: {scrambled}");
    if guess == current_word:
        add_points(ctx.author.id, 1, "scramble");
        add_points(ctx.author.id, 5, "balance");
        await ctx.reply("Correct!");
        current_word = get_random_word();
    else:
        await ctx.reply("Not quite!");
#--- WORD SCRAMBLE ---

#--- DAILY ---
DAILY_COOLDOWN = 86400

@bot.command()
async def daily(ctx):
    user_id = ctx.author.id;
    now = int(time.time());

    conn = sqlite3.connect(DB_NAME);
    cursor = conn.cursor();

    cursor.execute("""
    SELECT last_claim
    FROM daily_claims
    WHERE user_id = ?
    """, (user_id,));

    result = cursor.fetchone();

    if result is None:
        cursor.execute("""
        INSERT INTO daily_claims (user_id, last_claim)
        VALUES (?, ?)
        """, (user_id, now));

        conn.commit();
        conn.close();

        add_points(user_id, 10, "balance");
        await ctx.reply("You received $10!");

    else:
        last_claim = result[0]
        next_claim = last_claim + DAILY_COOLDOWN

        if now >= next_claim:
            cursor.execute("""
            UPDATE daily_claims
            SET last_claim = ?
            WHERE user_id = ?
            """, (now, user_id));

            conn.commit();
            conn.close();

            add_points(user_id, 10, "balance");
            await ctx.reply("You received $10!");

        else:
            await ctx.reply(
                f"You can claim your next daily <t:{next_claim}:R>."
            );

    conn.commit();
    conn.close();
#--- DAILY ---

if __name__ == "__main__":
    with open("./app_token", "r") as token_file:
        TOKEN = token_file.readline();
        bot.run(TOKEN);