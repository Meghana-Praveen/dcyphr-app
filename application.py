import os
import re
import math
# import smtplib

# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for, send_from_directory
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, datetime
from bs4 import BeautifulSoup
import jellyfish
# from flask_email_verifier import EmailVerifier
# from validate_email import validate_email
from helpers import apology, login_required, lookup, usd, readability, remove_scripts, percent_remove

# Configure application
app = Flask(__name__)
# verifier = EmailVerifier(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# Configure CS50 Library to use SQLite database
# db = SQL('postgres://hwicvwhg:4zzgStNJkiEy3hC3gtFHrdlyLFR_vQUN@rajje.db.elephantsql.com:5432/hwicvwhg?sslmode=require')
# db = SQL("sqlite:///dcyphr.db")
db = SQL(os.environ['DATABASE_URL'])
# This allows the user to browse the different articles
@app.route("/form")
def form():# Displays articles by recency of completion and displays only the article title and author as a link to the page that contains the actual summary
    return render_template("form.html")

@app.route("/browse/<int:page>", methods=["GET", "POST"])
def browse(page):
    if request.method == "GET":
        page_length = 10
        # Selects doi so we know where to route people when they click on the article link

        # Creates an array of links to route people to that corresponds to what people click on
        length = db.execute("SELECT COUNT(*) AS count FROM summary WHERE summary.done = CAST(1 AS BIT) and summary.approved = 1")[0]['count']
        number = int(math.ceil(length/page_length))


        summaries = db.execute(
            "SELECT summary.likes, article, username, users.id AS user, doi, summary.id, summary.summary FROM summary JOIN users ON summary.user_id = users.id WHERE summary.done = CAST(1 AS BIT) and summary.approved = 1 ORDER BY summary.likes DESC LIMIT :limit OFFSET :offset;", limit=page_length, offset=page_length*page)

        if page + 1 == number:
            page_length = len(summaries)

        # Displays preview information about articles


        # Gets length because there is no len function in jinja
        tags = db.execute("SELECT id, title FROM tags")
        tags_length = len(tags)
        if length == 0:
            p = "No summaries to show. Please contribute."
            return render_template("browse.html", summaries=summaries, length=length, p=p)
        else:
            soup = []
            for i in range(len(summaries)):
                soup.append(percent_remove(str(BeautifulSoup(summaries[i]["summary"], features = "html5lib").get_text()[0:500])))
            return render_template("browse.html", tags=tags, tags_length=tags_length, summaries=summaries, length=length, preview=soup, page=page, page_length = page_length, number=number)

# This route displays the summaries to the people
# Note that there is a variable in the route to specify what article they are looking at
@app.route("/read/<int:summary_id>", methods=["GET", "POST"])
def read(summary_id):
    if request.method == "GET":
        # Gets information about article to display
        article = db.execute("SELECT article FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]["article"]
        summary = db.execute(
            "SELECT summary.id, summary.summary, user_id, doi, username FROM summary JOIN users ON summary.user_id = users.id WHERE summary.id=:summary_id", summary_id=summary_id)
        username = db.execute("SELECT username FROM users WHERE id=:user_id", user_id=summary[0]["user_id"])
        comments = db.execute("SELECT * FROM comments JOIN users ON comments.user_id = users.id WHERE summary_id=:summary_id ORDER BY comment_id, comments.id", summary_id=summary_id)
        link = db.execute("SELECT link FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]["link"]
        likes = db.execute("SELECT likes FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]["likes"]
        citation = db.execute("SELECT citation FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]["citation"]
        tags = db.execute("SELECT title, tags.id FROM tags JOIN tagitem ON tags.id=tagitem.tag_id WHERE tagitem.item_id=:summary_id", summary_id=summary[0]['id'])
        tag_length = len(tags)
        all_tags = db.execute("SELECT title FROM tags")
        all_tags_len = len(all_tags)
        article_methods = summary[0]["summary"].lower()
        methods = db.execute("SELECT name FROM methods")
        methods_list = []
        for i in range(len(methods)):
            methods_list.append(methods[i]["name"])
        methods_used = []
        method_id = []
        for method in methods_list:
            for word in method.split():
                if word.lower() in article_methods:
                    methods_used.append(method)
                    method_id.append(db.execute("SELECT id FROM methods WHERE name=:method", method=method)[0]["id"])
        methods_used = list(dict.fromkeys(methods_used))
        method_length = len(methods_used)
        html = db.execute("SELECT summary FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]["summary"]
        soup = BeautifulSoup(html, features="html5lib")
        title_list=[]
        for title in soup.find_all("h2"):
            title_list.append(title.text.strip())
            title["id"] = title.text.strip()
        title_length=len(title_list)
        summary_actual=soup
        # Checks if person is logged in
        # x is a variable that disables liking when true and enables liking when false
        z = "false"
        if len(session) == 0:
            x = "true"
            y = "true"
        else:
            y = "false"
            if db.execute("SELECT admin FROM users WHERE id=:user_id", user_id=session['user_id'])[0]['admin'] == 1:
                z = "true"
            # Checks if person already liked the post
            liked = db.execute("SELECT likes FROM users WHERE id=:user_id", user_id=session["user_id"])[0]["likes"]
            # Checks specifically if the person has liked anything
            if liked == None:
                x = "false"
                db.execute("UPDATE users SET likes = ' ' WHERE id=:user_id", user_id=session["user_id"])
            elif str(summary_id) in liked:
                x = "true"
            else:
                x = "false"
        return render_template("read.html", z=z, all_tags=all_tags, all_tags_len=all_tags_len, tag_length=tag_length, tags=tags, summary_actual=percent_remove(str(summary_actual)), title_length=title_length, titles=title_list, summary_id=summary_id, username=username, method_length=method_length, summary=summary, article=article, link=link, likes=likes, x=x, y=y, comments=comments, citation=citation, methods_used=methods_used, method_id=method_id)
    else:
        flag = request.form.get("flag")
        delete = request.form.get("delete")
        if delete:
            db.execute("DELETE FROM tagitem WHERE tag_id=:tag_id AND item_id=:item_id", tag_id=delete, item_id=summary_id)
            return redirect("/read/{0}".format(summary_id))
        if flag == "flag":
            user = db.execute("SELECT user_id FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]["user_id"]
            db.execute("UPDATE summary SET approved=0 WHERE id=:summary_id", summary_id=summary_id)
            db.execute("UPDATE users SET points = points - 20 WHERE id=:user_id", user_id=user)
            return redirect("/")
        # Handles tagging
        tag = request.form.get("tag")
        if tag:
            tag = tag.lower()
            summary_tags = db.execute("SELECT title FROM tags JOIN tagitem ON tags.id=tagitem.tag_id WHERE tagitem.item_id=:summary_id", summary_id=summary_id)
            summary_tags_list = []
            for i in range(len(summary_tags)):
                summary_tags_list.append(summary_tags[i]['title'])

            tags = db.execute("SELECT title FROM tags")
            tags_list = []
            for i in range(len(tags)):
                tags_list.append(tags[i]['title'])

            if tag in summary_tags_list:
                pass
            elif tag in tags_list:
                tag_id = db.execute("SELECT id FROM tags WHERE title=:tag", tag=tag)[0]['id']
                db.execute("INSERT INTO tagitem (item_id, tag_id) VALUES (:summary_id, :tag_id)", summary_id=summary_id, tag_id=tag_id)
            elif tag not in tags_list:
                db.execute("INSERT INTO tags (title) VALUES (:tag)", tag=tag)
                tag_id = db.execute("SELECT id FROM tags WHERE title=:tag", tag=tag)[0]['id']
                db.execute("INSERT INTO tagitem (item_id, tag_id) VALUES (:summary_id, :tag_id)", summary_id=summary_id, tag_id=tag_id)
            return redirect("/read/{0}".format(summary_id))
        # Handles the liking and disliking action
        author = db.execute("SELECT user_id FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]["user_id"]
        dislike = request.form.get("dislike")
        like = request.form.get("like")
        likes = db.execute("SELECT likes FROM users WHERE id=:user_id", user_id=session["user_id"])[0]["likes"]
        likes = likes + " " + str(summary_id) + " "
        if like:
            db.execute("UPDATE users SET likes = :likes WHERE id=:user_id", likes=likes, user_id=session["user_id"])
        if dislike == "dislike":
            db.execute("UPDATE summary SET likes = likes - 1 WHERE id=:summary_id", summary_id=summary_id)
            db.execute("UPDATE users SET points = points - 1 WHERE id=:user_id", user_id=author)
        elif like == "like":
            db.execute("UPDATE summary SET likes = likes + 1 WHERE id=:summary_id", summary_id=summary_id)
            db.execute("UPDATE users SET points = points + 1 WHERE id=:user_id", user_id=author)
        else:
        # Handles comments
            comment = request.form.get('comment')
            reply = request.form.get('reply')
            if comment == None and reply == None:
                return render_template("apology.html", message="Error, please input text for your post")
            today = date.today()
            today = today.strftime("%B %d, %Y")
            # Comment
            if not reply:
                db.execute("INSERT INTO comments (user_id, summary_id, comment, date, likes, reply) VALUES (:user_id, :summary_id, :comment, :date, :likes, :reply)",
                            user_id=session["user_id"], summary_id=summary_id, comment=comment, date=today, likes=0, reply=0)
                comment_id = db.execute("SELECT id FROM comments WHERE summary_id=:summary_id AND comment=:comment ORDER BY id DESC LIMIT 1", summary_id=summary_id, comment=comment)[0]["id"]
                db.execute("UPDATE comments SET comment_id=:comment_id WHERE summary_id=:summary_id AND comment=:comment ORDER BY id DESC LIMIT 1", comment_id=comment_id, summary_id=summary_id, comment=comment)
            # Reply
            else:
                comment_id = request.form.get('comment_button')
                db.execute("UPDATE comments SET last=0 WHERE (summary_id=:summary_id) AND (comment_id=:comment_id) AND last=1", summary_id=summary_id, comment_id=comment_id)
                db.execute("INSERT INTO comments (user_id, summary_id, comment, date, likes, reply, comment_id, last) VALUES (:user_id, :summary_id, :comment, :date, :likes, :reply, :comment_id, :last)",
                            user_id=session["user_id"], summary_id=summary_id, comment=reply, date=today, likes=0, reply=1, comment_id=comment_id, last=1)
        return redirect("/read/{0}".format(summary_id))

@app.route("/tag/<int:tag_id>")
def tag(tag_id):
    titles = db.execute("SELECT article, summary.id AS summary_id, summary.likes, username, users.id, summary.summary FROM users JOIN summary ON summary.user_id=users.id JOIN tagitem on summary.id=tagitem.item_id WHERE tagitem.tag_id=:tag_id AND summary.approved=1 AND summary.done = CAST(1 AS BIT)", tag_id=tag_id)
    length = len(titles)
    title = db.execute("SELECT title FROM tags WHERE id=:tag_id", tag_id=tag_id)
    print(title[0]['title'])
    tags = db.execute("SELECT id, title FROM tags")
    tags_length = len(tags)
    if length == 0:
        p = "No summaries to show. Please contribute."
        return render_template("tag.html", titles=titles, length=length, p=p, title=title)
    else:
        soup = []
        for i in range(length):
            soup.append(percent_remove(str(BeautifulSoup(titles[i]["summary"], features = "html5lib").get_text()[0:500])))
        return render_template("tag.html", tags=tags, tags_length=tags_length, titles=titles, length=length, title=title, preview=soup)

@app.route("/apa/<int:summary_id>", methods=["GET", "POST"])
@login_required
def apa(summary_id):
    if request.method == "GET":
        info = db.execute("SELECT article, citation, link FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]
        length = len(info)
        return render_template("apa.html", info=info, length=length)
    else:
        citation = request.form.get("citation")
        db.execute("UPDATE summary SET citation=:citation WHERE id=:summary_id", citation=citation, summary_id=summary_id)
        return redirect("/read/{0}".format(summary_id))

@app.route("/doi/<int:summary_id>", methods=["GET", "POST"])
@login_required
def doi(summary_id):
    if request.method == "GET":
        info = db.execute("SELECT article, doi, link FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]
        length = len(info)
        return render_template("doi.html", info=info, length=length)
    else:
        doi = request.form.get("doi")
        db.execute("UPDATE summary SET doi=:doi WHERE id=:summary_id", summary_id=summary_id, doi=doi)
        return redirect("/")

# Displays to the user a list of tasks that they can click on
@app.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    if request.method == "GET":
        # Gets tasks that are not marked as done and orders it by request amount
        tasks = db.execute("SELECT article, doi, id FROM summary WHERE done = CAST(0 AS BIT) AND bookmarked = 0 ORDER BY requests DESC")

        length = len(tasks)
        return render_template("tasks.html", tasks=tasks, length=length)

    else:
        user_id = session["user_id"]
        summary_id = request.form.get("bookmark")
        today = date.today()
        db.execute("UPDATE summary SET bookmarked=:user_id, bookmarked_date=:date WHERE id=:summary_id", user_id=user_id, summary_id=summary_id, date=today)

        tasks = db.execute("SELECT article, id, doi FROM summary WHERE done = CAST(0 AS BIT) AND bookmarked = :user_id ORDER BY requests DESC", user_id=user_id)
        length = len(tasks)

        #return render_template("bookmarks.html", tasks=tasks, length=length)
        return redirect("/bookmarks")

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, "", text)


@app.route("/bookmarks", methods=["GET", "POST"])
@login_required
def bookmarks():
    if request.method == "GET":
        user_id = session["user_id"]
        tasks = db.execute("SELECT article, id, doi FROM summary WHERE done = CAST(0 AS BIT) AND bookmarked = :user_id ORDER BY requests DESC", user_id=user_id)
        length = len(tasks)
        return render_template("bookmarks.html", tasks=tasks, length=length)

    else:
        user_id = session["user_id"]
        summary_id = request.form.get("unbookmark")
        db.execute("UPDATE summary SET bookmarked=0 WHERE id=:summary_id", summary_id=summary_id)

        tasks = db.execute("SELECT article, id, doi FROM summary WHERE done = CAST(0 AS BIT) AND bookmarked = :user_id ORDER BY requests DESC", user_id=user_id)
        length = len(tasks)
        return render_template("bookmarks.html", tasks=tasks, length=length)


# Allows the user to summarize a text
# You get to this route by clicking on a summary type task
@app.route("/edit/<int:summary_id>", methods=["GET", "POST"])
@login_required
def edit(summary_id):
    summary = db.execute("SELECT summary FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]["summary"]
    if summary == None:
        summary = ""
    # else:
        # summary = remove_html_tags(summary_dirty)
    if request.method == "GET":
        # provides contributor with information about the article they are summarizing
        article = db.execute("SELECT article, user_id FROM summary WHERE id=:summary_id", summary_id=summary_id)
        username = db.execute("SELECT username FROM users WHERE id=:user_id", user_id=article[0]["user_id"])
        link = db.execute("SELECT link FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]["link"]
        return render_template("edit.html", article=article, link=link, summary=percent_remove(str(summary)), username=username)
    else:
        # inserts user summary from form into summary table
        summary_new = remove_html_tags(request.form.get("summary"))
        summary_new_html = remove_scripts(request.form.get("summary"))
        user = db.execute("SELECT user_id FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]["user_id"]
        db.execute("UPDATE summary SET summary=:summary, done=CAST(1 AS BIT) WHERE id=:summary_id;",
                   summary=summary_new_html, summary_id=summary_id)
        if not user:
            db.execute("UPDATE summary SET user_id=:user_id WHERE id=:summary_id;",
                   user_id=session["user_id"], summary_id=summary_id)
        # create points bot

        difference = jellyfish.damerau_levenshtein_distance(summary, summary_new)
        if len(summary) > len(summary_new):
            max_diff = len(summary)
        else:
            max_diff = len(summary_new)
        if max_diff == 0:
            diff_ratio = 0
        else:
            diff_ratio = difference/max_diff
        if diff_ratio < 0.05:
            pass
        else:
            if readability(summary_new) - readability(summary) < 0:
                others = db.execute("SELECT others FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]['others']
                print(others)
                if others == None:
                    others = " " + str(session["user_id"])
                else:
                    others = others + " " + str(session["user_id"])
                db.execute("UPDATE summary SET others = :others WHERE id=:summary_id", others=others, summary_id=summary_id)

        existing = db.execute("SELECT id FROM compare WHERE summary_id=:summary_id", summary_id=summary_id)
        if len(existing) == 0:
            db.execute("INSERT INTO compare (summary_id, old, new, user_id) VALUES (:summary_id, :old, :new, :user_id)", summary_id=summary_id, old=summary, new=summary_new_html, user_id=session["user_id"])
        else:
            db.execute("UPDATE compare SET old=new, new=:new WHERE summary_id=:summary_id AND user_id=:user_id", summary_id=summary_id, new=summary_new_html, user_id=session["user_id"])
        return redirect("/")

# Allows user to request an article to be summarized
@app.route("/request", methods=["GET", "POST"])
def requesting():
    if request.method == "GET":
        return render_template("request.html")
    else:
        article = request.form.get("article")
        doi = request.form.get("doi")
        doi = doi.strip()
        link = request.form.get("link")
        citation = request.form.get("citation")
        if not citation:
            citation = "Not avaliable"
        # checks if PMID/DOI is already in the requested list
        if len(db.execute("SELECT doi FROM summary WHERE doi=:doi", doi=doi)) > 0:
            test = db.execute("SELECT article FROM summary WHERE doi=:doi", doi=doi)
            # checks if your PMID/DOI has the correct title if it is already in database
            if article != test[0]["article"]:
                return render_template("apology.html", message="Error, PMID already exists in database: incorrect PMID or title")
            # if already in database, it increases the number of requests by 1
            requests = db.execute("SELECT requests FROM summary WHERE doi=:doi", doi=doi)[0]["requests"] + 1
            db.execute("UPDATE summary SET requests=:requests WHERE doi=:doi", doi=doi, requests=requests)
        else:
            # if it isn't in the database, it adds it as a new task
            db.execute("INSERT INTO summary (requests, article, doi, done, link, citation, likes, approved) VALUES (1, :article, :doi, CAST(0 AS BIT), :link, :citation, 0, 0);",
                       article=article, doi=doi, link=link, citation=citation)
        return redirect("/")

# homepage with a search bar
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        leaderboard = db.execute("SELECT username, id, points FROM users WHERE points > 0 ORDER BY points DESC LIMIT 5")
        lead_length = len(leaderboard)
        # db.execute("CREATE TABLE IF NOT EXISTS summary (id SERIAL PRIMARY KEY, user_id INTEGER, citation TEXT, doi TEXT, background TEXT, aims TEXT, methods TEXT, results TEXT, conclusion TEXT, task_id INTEGER, done BIT, reviewed INTEGER, remove BIT, likes INTEGER, reviewer_1 INTEGER, reviewer_2 INTEGER, FOREIGN KEY(doi) REFERENCES tasks(doi), FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY(task_id) REFERENCES tasks(id));")
        # db.execute("CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY, type TEXT, citation TEXT, requests INTEGER, article TEXT, doi TEXT, done INTEGER, user_id INTEGER, link TEXT, FOREIGN KEY(user_id) REFERENCES users(id));")
        # db.execute("CREATE TABLE IF NOT EXISTS comments (id SERIAL PRIMARY KEY, user_id INTEGER, doi INTEGER, comment TEXT, date DATE);")
        return render_template("index.html", leaderboard=leaderboard, lead_length=lead_length)
    else:
        # search bar
        search = request.form.get("search").lower()
        # gets info on things that have the searched thing in it
        results = db.execute("SELECT DISTINCT summary.id AS summary_id, summary.summary, username, article, users.id FROM summary JOIN tagitem ON summary.id=tagitem.item_id JOIN tags ON tagitem.tag_id=tags.id JOIN users ON summary.user_id = users.id WHERE (LOWER(article) LIKE :search OR summary.doi LIKE :search OR username LIKE :search OR LOWER(summary.summary) LIKE :search OR LOWER(summary.citation) LIKE :search OR LOWER(tags.title) LIKE :search) AND summary.done = CAST(1 AS BIT) AND summary.approved = 1", search="%" + search + "%")
        soup = []
        links = []
        for i in range(len(results)):
            soup.append(percent_remove(str(BeautifulSoup(results[i]["summary"], features="html5lib").get_text()[0:500])))
            links.append("read/{0}".format(results[i]["summary_id"]))
        # creates list of links/routes to display to user so they can click on the result and it takes them to the correct read subroute
        length = len(results)

        return render_template("results.html", results=results, links=links, length=length, search=search, preview=soup)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("apology.html", message="must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("apology.html", message="must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("apology.html", message="invalid username/password combination")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["remember_me"] = True
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/bio/<int:user_id>", methods=["GET", "POST"])
@login_required
def bio(user_id):
    if request.method == "GET":
        bio = db.execute("SELECT bio FROM users WHERE id=:user_id", user_id=user_id)[0]['bio']
        return render_template("bio.html", bio=bio)
    else:
        bio = remove_scripts(request.form.get("bio"))
        db.execute("UPDATE users SET bio=:bio WHERE id=:user_id", user_id=user_id, bio=bio)
        return redirect(url_for("profile", user_id=user_id))

@app.route("/profile/<int:user_id>", methods=["GET", "POST"])
@login_required
def profile(user_id):
    # gets list of articles that the user has written
    articles = db.execute(
        "SELECT article, id FROM summary WHERE user_id=:user_id AND done=CAST(1 AS BIT)", user_id=user_id)
    # gets number of articles they have written
    length = len(articles)
    points = db.execute("SELECT points FROM users WHERE id=:user_id", user_id=session["user_id"])[0]['points']
    # progress bar based on how much the user has summarized
    progress = round(length/60 * 100)
    # gets their username
    info = db.execute("SELECT bio, username FROM users WHERE id=:user_id", user_id=session["user_id"])
    admin = db.execute("SELECT admin FROM users WHERE id=:user_id", user_id=session["user_id"])[0]['admin']
    if info[0]['bio'] == None:
        info[0]['bio'] = "This user has no bio right now."
    if points == None:
        points = 0
    # ranks = db.execute("SELECT id, RANK () OVER (ORDER BY points DESC) as points_rank FROM users")
    # for i in len(ranks):
    #     if ranks[i]["id"] == user_id:
    #         rank = ranks[i]["points_rank"]
    return render_template("profile.html", info=info, articles=articles, length=length, progress=progress, admin=admin, points=points, user_id=user_id)

@app.route("/compare/<int:compare_id>", methods=["GET", "POST"])
@login_required
def compare(compare_id):
    if request.method == "GET":
        articles = db.execute("SELECT compare.id, old, new, summary.id, article, link FROM compare JOIN summary ON compare.summary_id=summary.id WHERE compare.id=:compare_id", compare_id=compare_id)
        return render_template("compare.html", articles=articles)
    else:
        approve = request.form.get("approve")
        disapprove = request.form.get("disapprove")
        summary_id = db.execute("SELECT summary_id FROM compare WHERE id=:compare_id", compare_id=compare_id)[0]['summary_id']
        if not approve:
            old = db.execute("SELECT old FROM compare WHERE summary_id=:summary_id", summary_id=summary_id)[0]['old']
            db.execute("UPDATE summary SET summary=:old WHERE id=:summary_id", old=old, summary_id=summary_id)
            db.execute("DELETE FROM compare WHERE id=:doi", doi=compare_id)
        else:
            new = db.execute("SELECT new FROM compare WHERE summary_id=:summary_id", summary_id=summary_id)[0]['new']
            db.execute("UPDATE summary SET summary=:new WHERE id=:summary_id", summary_id=summary_id, new=new)
            user = db.execute("SELECT user_id FROM compare WHERE id=:doi", doi=compare_id)[0]['user_id']
            if user == None:
                pass
            else:
                db.execute("UPDATE users SET points=points + 10 WHERE id=:user_id", user_id=user)
            db.execute("DELETE FROM compare WHERE id=:doi", doi=compare_id)
        articles = db.execute("SELECT compare.id, article FROM compare JOIN summary ON compare.summary_id=summary.id")
        length = len(articles)
        return render_template("compare_home.html", articles=articles, length=length)



@app.route("/comparehome", methods=["GET"])
@login_required
def comparehome():
        articles = db.execute("SELECT compare.id, article FROM compare JOIN summary ON compare.summary_id=summary.id")
        length = len(articles)
        return render_template("compare_home.html", articles=articles, length=length)


# same as profile route but without the change password and progress bar
# public profile
@app.route("/public/<int:user_id>")
def public(user_id):
    articles = db.execute(
        "SELECT article, id FROM summary WHERE user_id=:user_id AND done = CAST(1 AS BIT)", user_id=user_id)
    length = len(articles)
    info = db.execute("SELECT bio, username, points FROM users WHERE id=:user_id", user_id=user_id)
    if info[0]['points'] == None:
        info[0]['points'] = 0
    if info[0]['bio'] == None:
        info[0]['bio'] = "This user has no bio right now."
    return render_template("public.html", articles=articles, info=info, length=length)



@app.route("/method/<int:method_id>")
def methods(method_id):
    if method_id == 0:
        methods = db.execute("SELECT name, id FROM methods")
        preview = db.execute("SELECT substr(description, 1, 400) FROM methods")
        length = len(methods)
        return render_template("methods.html", methods=methods, preview=preview, length=length)
    else:
        methods = db.execute("SELECT name, description FROM methods WHERE id=:method_id", method_id=method_id)
        return render_template("method_summary.html", methods=methods)

# route to change password
@app.route("/password", methods=["GET", "POST"])
@login_required
def password():
    if request.method == "GET":
        return render_template("password.html")
    else:
        password = request.form.get("password")
        confirm = request.form.get("confirmation")
        if password != confirm:
            return render_template("apology.html", message="Your passwords do not match")
        else:
            hashed = generate_password_hash(password)
            db.execute("UPDATE users SET hash = :hashed WHERE id=:user_id", hashed=hashed, user_id=session["user_id"])
        return render_template("index.html")


# allows user registration
@app.route("/register", methods=["GET", "POST"])
def register():
    # db.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT, hash TEXT, summarized INTEGER, reviewed INTEGER, likes TEXT, email TEXT)")
    if request.method == "GET":
        return render_template("register.html")
    else:
        # gets form inputs
        emailConfirmed = False
        username = request.form.get("username")
        email = request.form.get("email")
        if not email:
            return render_template("apology.html", message="You must enter an email")
        if not username:
            return render_template("apology.html", message="You must enter a username")
        if len(db.execute("SELECT id FROM users WHERE email = :email", email=email)) > 0:
            return render_template("apology.html", message="That email is already registered")
        # checks that it is a valid email
        if not re.match(r"^[A-Za-z0-9\.\+_-]+@", email):
            return render_template("apology.html", message="Not a valid email address")
        # checks if username is taken
        if len(db.execute("SELECT id FROM users WHERE username = :username", username=username)) > 0:
            return render_template("apology.html", message="That username is taken")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        if not password:
            return render_template("apology.html", message="You must enter a password")
        if password != confirm:
            return render_template("apology.html", message="Your passwords do not match")
        else:
            # email_address_info = verifier.verify(email)
            # is_valid = validate_email(email_address=email, check_regex=True, check_mx=True, smtp_timeout=10, dns_timeout=10, use_blacklist=True)
            # generates hash of password which is stored in database
            # is_valid = validate_email(email, check_mx=True, verify=True)
            # print(is_valid)
            hashed = generate_password_hash(password)
            db.execute("INSERT INTO users (username, hash, email) VALUES (:username, :hashed, :email)", username=username, hashed=hashed, email=email)
            return redirect("/login")

# displays search results
@app.route("/results")
def results():
    return render_template("results.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "GET":
        return render_template("contact.html")
    else:
        email = request.form.get("email")
        feedback = request.form.get("feedback")
        db.execute("INSERT INTO feedback (email, feedback) VALUES (:email, :feedback)", email=email, feedback=feedback)



@app.route("/approvals/<int:approval_id>", methods=["GET", "POST"])
@login_required
def approvals(approval_id):
    if request.method == "GET":
        articles = db.execute("SELECT summary, article, link FROM summary WHERE id=:approval_id", approval_id=approval_id)
        return render_template("approvals.html", articles=articles)
    else:
        summary = request.form.get("summary")
        approve = request.form.get("approve")
        summary_id = db.execute("SELECT id FROM summary WHERE id=:approval_id", approval_id=approval_id)[0]['id']
        if not approve:
            db.execute("UPDATE summary SET summary = '', user_id=NULL, done=CAST(0 AS BIT) WHERE id=:summary_id", summary_id=summary_id)
        else:
            user_id = db.execute("SELECT user_id FROM summary WHERE id=:summary_id", summary_id=summary_id)[0]["user_id"]
            points = db.execute("SELECT points FROM users WHERE id=:user_id", user_id=user_id)[0]['points']
            if points == None:
                points = 0
            points = points + 20
            db.execute("UPDATE users SET points=:points WHERE id=:user_id", points=points, user_id=user_id)
            db.execute("UPDATE summary SET summary = :summary, approved=1 WHERE id=:summary_id", summary=summary, summary_id=summary_id)
        articles = db.execute("SELECT id, article FROM summary WHERE approved = 0 AND done = CAST(1 AS BIT)")
        length = len(articles)
        return render_template("approval_home.html", articles=articles, length=length)



@app.route("/approvalhome", methods=["GET"])
@login_required
def approvalhome():
        articles = db.execute("SELECT id, article FROM summary WHERE approved = 0 AND done = CAST(1 AS BIT)")
        length = len(articles)
        return render_template("approval_home.html", articles=articles, length=length)

@app.route("/bookmarking", methods=["GET", "POST"])
@login_required
def bookmarking():
    if request.method == "GET":
        info = db.execute("SELECT article, doi, bookmarked, bookmarked_date, username, summary.id FROM summary JOIN users ON bookmarked = users.id WHERE bookmarked != 0")
        length = len(info)
        return render_template("bookmarking.html", info=info, length=length)
    if request.method == "POST":
        summary_id = request.form.get("unbookmark")
        db.execute("UPDATE summary SET bookmarked=0 WHERE id=:summary_id", summary_id=summary_id)
        info = db.execute("SELECT article, bookmarked, doi, username, summary.id FROM summary JOIN users ON bookmarked = users.id WHERE bookmarked != 0")
        length = len(info)
        return render_template("bookmarking.html", info=info, length=length)


@app.route("/about")
def about():
    # msg = Message("Hello",
    #               sender="jeffzma2000@gmail.com",
    #               recipients=["jeffzma2000@gmail.com"])
    # mail.send(msg)


    # sent_from = 'jeffzma2000@gmail.com'
    # to = ['jeffzma2000@gmail.com', 'jeffzma2000@gmail.com']
    # subject = 'OMG Super Important Message'
    # body = "Hello"

    # email_text = """\
    # From: %s
    # To: %s
    # Subject: %s

    # %s
    # """ % (sent_from, ", ".join(to), subject, body)
    # try:
    #     server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    #     server.ehlo()
    #     server.login("jeffzma2000@gmail.com", "Swimming2000")
    #     server.sendmail(sent_from, to, email_text)
    #     server.close()
    #     print('Email sent!')
    # except:
    #     print('Something went wrong...')
    return render_template("about.html")

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico')

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
