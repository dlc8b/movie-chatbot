"""Simple movie-review knowledge base with retrieval and feedback-based learning."""

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DB_PATH = Path(__file__).with_name("movie_kb.sqlite3")
WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = os.getenv(
    "MOVIE_KB_USER_AGENT",
    "MovieReviewBot/0.1 (replace with your contact information)",
)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY,
            title TEXT UNIQUE COLLATE NOCASE,
            url TEXT
        );
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            movie_id INTEGER REFERENCES movies(id),
            kind TEXT,
            source TEXT,
            source_title TEXT,
            url TEXT,
            license TEXT,
            permission TEXT,
            text TEXT,
            added_at TEXT
        );
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            evidence TEXT NOT NULL,
            rating REAL,
            correction TEXT,
            added_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS source_feedback (
            source TEXT PRIMARY KEY,
            total REAL NOT NULL DEFAULT 0,
            count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            added_at TEXT NOT NULL
        );
    """)
    return db


def wiki_request(params):
    params.update({"format": "json", "formatversion": "2"})
    request = Request(
        f"{WIKI_API}?{urlencode(params)}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def import_movie(query):
    """Add a short factual introduction from a Wikipedia article, not reviews."""
    search = wiki_request({
        "action": "query", "list": "search", "srsearch": f'intitle:"{query}" film',
        "srnamespace": "0", "srlimit": "5",
    })
    hits = search.get("query", {}).get("search", [])
    if not hits:
        print("No matching Wikipedia page found.")
        return

    title = hits[0]["title"]
    result = wiki_request({
        "action": "query", "prop": "extracts|info", "exintro": "1",
        "explaintext": "1", "inprop": "url", "titles": title,
    })
    pages = result.get("query", {}).get("pages", [])
    if not pages or not pages[0].get("extract"):
        print("Wikipedia did not return an article summary.")
        return

    page = pages[0]
    url = page.get("fullurl", f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}")
    db = connect()
    db.execute("INSERT OR IGNORE INTO movies(title, url) VALUES (?, ?)", (title, url))
    movie_id = db.execute("SELECT id FROM movies WHERE title=?", (title,)).fetchone()["id"]
    exists = db.execute(
        "SELECT 1 FROM documents WHERE movie_id=? AND source='Wikipedia'", (movie_id,)
    ).fetchone()
    if exists:
        print(f"{title} is already in the KB.")
        return
    db.execute("""INSERT INTO documents
        (movie_id, kind, source, source_title, url, license, permission, text, added_at)
        VALUES (?, 'fact', 'Wikipedia', ?, ?, ?, ?, ?, ?)""",
        (movie_id, title, url,
         "Wikipedia text is generally CC BY-SA/GFDL; verify article notices",
         "Public MediaWiki API; reuse subject to the article's license and attribution terms",
         pages[0]["extract"], now()),
    )
    db.commit()
    print(f"Added factual context for {title}.\n{url}")
    if len(hits) > 1:
        print("Other matches: " + "; ".join(hit["title"] for hit in hits[1:]))


def add_review(movie_title):
    """Manually add a review only when its storage/use is permitted."""
    print("Enter information for review text you are allowed to store and use.")
    source_title = input("Source page/title: ").strip()
    source = input("Source name: ").strip()
    url = input("Source URL: ").strip()
    license_name = input("License: ").strip()
    permission = input("Permission basis: ").strip()
    text = input("Review text: ").strip()
    if not all((source_title, source, url, license_name, permission, text)):
        print("All fields are required; nothing was saved.")
        return

    db = connect()
    db.execute("INSERT OR IGNORE INTO movies(title, url) VALUES (?, '')", (movie_title,))
    movie_id = db.execute("SELECT id FROM movies WHERE title=?", (movie_title,)).fetchone()["id"]
    db.execute("""INSERT INTO documents
        (movie_id, kind, source, source_title, url, license, permission, text, added_at)
        VALUES (?, 'review', ?, ?, ?, ?, ?, ?, ?)""",
        (movie_id, source, source_title, url, license_name, permission, text, now()),
    )
    db.commit()
    print("Review saved with its source and permission details.")


def retrieve(question, limit=5):
    """Simple keyword retrieval. Prior feedback can nudge source ranking."""
    words = set(re.findall(r"[a-z0-9]+", question.lower()))
    if not words:
        return []
    db = connect()
    documents = db.execute("""SELECT d.id,d.kind,d.source,d.source_title,d.url,d.text,m.title
        FROM documents d LEFT JOIN movies m ON m.id=d.movie_id""").fetchall()
    ranked = []
    for doc in documents:
        text_words = set(re.findall(
            r"[a-z0-9]+", ((doc["title"] or "") + " " + doc["text"]).lower()
        ))
        matches = len(words & text_words)
        if matches:
            feedback = db.execute(
                "SELECT total,count FROM source_feedback WHERE source=?", (doc["source"],)
            ).fetchone()
            # Rating average is 0..1. Center it at 0.5 so feedback adjusts, but
            # does not overwhelm, the number of matching query words.
            source_average = feedback["total"] / feedback["count"] if feedback and feedback["count"] else 0.5
            score = matches + (source_average - 0.5) * 0.5
            ranked.append((score, doc))
    ranked.sort(key=lambda item: item[0], reverse=True)
    results = [doc for _, doc in ranked[:limit]]
    # Team corrections become clearly labeled retrieval hints on later questions.
    for correction in db.execute("SELECT id,question,answer FROM corrections"):
        correction_words = set(re.findall(
            r"[a-z0-9]+", (correction["question"] + " " + correction["answer"]).lower()
        ))
        if words & correction_words:
            results.append({
                "id": None, "kind": "correction", "source": "Team correction",
                "source_title": f"Correction for: {correction['question']}", "url": "",
                "text": correction["answer"], "title": "Prior team correction",
            })
    return results[:limit]


def ask(question):
    """Show retrieved evidence, then save the generated answer and evidence."""
    evidence = retrieve(question)
    if not evidence:
        print("I don't have enough stored evidence to answer. Add an authorized source first.")
        return
    print("Retrieved passages (use these as evidence and cite their URLs):")
    for number, doc in enumerate(evidence, start=1):
        label = "Prior team correction (internal guidance)" if doc["kind"] == "correction" else (
            f"{doc['title'] or 'Movie'} — {doc['source_title']} ({doc['source']})"
        )
        print(f"\n[{number}] {label}")
        print(doc["text"])
        if doc["url"]:
            print(f"Source: {doc['url']}")
    print("\nFor now, draft the bot's answer using only the evidence above.")
    answer = input("Bot answer: ").strip()
    if not answer:
        print("No answer saved.")
        return
    db = connect()
    evidence_json = json.dumps([{
        "document_id": doc["id"], "source": doc["source"], "url": doc["url"]
    } for doc in evidence])
    cursor = db.execute(
        "INSERT INTO interactions(question,answer,evidence,added_at) VALUES(?,?,?,?)",
        (question, answer, evidence_json, now()),
    )
    db.commit()
    print(f"Saved interaction #{cursor.lastrowid}. Use feedback with that ID to rate it.")


def give_feedback(interaction_id, rating, correction):
    """Record feedback and update simple source scores for future retrieval."""
    db = connect()
    interaction = db.execute("SELECT * FROM interactions WHERE id=?", (interaction_id,)).fetchone()
    if interaction is None:
        print("Interaction not found.")
        return
    if interaction["rating"] is not None:
        print("This interaction already has feedback; it was not counted again.")
        return
    evidence = json.loads(interaction["evidence"])
    db.execute("UPDATE interactions SET rating=?, correction=? WHERE id=?",
               (rating, correction or None, interaction_id))
    for item in evidence:
        if item["source"] == "Team correction":
            continue
        db.execute("""INSERT INTO source_feedback(source,total,count) VALUES(?,?,1)
            ON CONFLICT(source) DO UPDATE SET total=total+excluded.total,count=count+1""",
            (item["source"], rating),
        )
    if correction:
        db.execute("INSERT INTO corrections(question,answer,added_at) VALUES(?,?,?)",
                   (interaction["question"], correction, now()))
    db.commit()
    print(f"Saved rating {rating:+g} for interaction #{interaction_id}.")
    if correction:
        print("Saved the correction as internal guidance for later retrieval.")


def main():
    parser = argparse.ArgumentParser(description="Movie review KB with a small feedback loop")
    commands = parser.add_subparsers(dest="command", required=True)
    imp = commands.add_parser("import", help="Import factual context from Wikipedia")
    imp.add_argument("title")
    add = commands.add_parser("add", help="Manually add an authorized review")
    add.add_argument("movie")
    ask_cmd = commands.add_parser("ask", help="Retrieve evidence and log a draft answer")
    ask_cmd.add_argument("question")
    feedback = commands.add_parser("feedback", help="Rate a saved answer: +1, +0.5, or 0")
    feedback.add_argument("interaction_id", type=int)
    feedback.add_argument("rating", type=float, choices=(0.0, 0.5, 1.0))
    feedback.add_argument("--correction", default="", help="Correct answer or feedback note")
    search = commands.add_parser("search", help="Search saved passages")
    search.add_argument("query")
    show = commands.add_parser("show", help="Show saved information for a movie")
    show.add_argument("movie")
    args = parser.parse_args()

    if args.command == "import":
        try:
            import_movie(args.title)
        except Exception as error:
            parser.exit(1, f"Wikipedia API error: {error}\n")
    elif args.command == "add":
        add_review(args.movie)
    elif args.command == "ask":
        ask(args.question)
    elif args.command == "feedback":
        give_feedback(args.interaction_id, args.rating, args.correction)
    elif args.command == "search":
        for doc in retrieve(args.query, limit=10):
            print(f"{doc['title']} [{doc['kind']}] — {doc['source']}\n{doc['text']}\n{doc['url']}\n")
        db = connect()
        corrections = db.execute("SELECT question,answer FROM corrections").fetchall()
        for item in corrections:
            if set(args.query.lower().split()) & set(item["question"].lower().split()):
                print(f"Team correction for '{item['question']}':\n{item['answer']}\n")
    elif args.command == "show":
        rows = connect().execute("""SELECT m.title,d.kind,d.source,d.source_title,d.url,
            d.license,d.text FROM movies m JOIN documents d ON d.movie_id=m.id
            WHERE m.title=? COLLATE NOCASE""", (args.movie,))
        for row in rows:
            print(f"{row['title']} [{row['kind']}] — {row['source_title']} ({row['source']})\n"
                  f"{row['text']}\nURL: {row['url']}\nLicense: {row['license']}\n")


if __name__ == "__main__":
    main()
