#!/usr/bin/env python

import git
import sqlite3
import os
import sys
import datetime

# check if the directory is a git repo
if not os.path.isdir('.git'):
    print('Not a git repo')
    sys.exit(1)

# connect to the database
conn = sqlite3.connect('git_log.db')
c = conn.cursor()

# create the table
c.execute('''CREATE TABLE IF NOT EXISTS commits
                 (id INTEGER PRIMARY KEY,
                 date TEXT,
                 author TEXT,
                 message TEXT)''')

# get the log of commits
repo = git.Repo('./')
for commit in repo.iter_commits():
    # get the date of the commit
    date = datetime.datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d %H:%M:%S')
    # get the author of the commit
    author = commit.author.name
    # get the message of the commit
    message = commit.message
    # insert the commit into the table
    c.execute("INSERT INTO commits VALUES (NULL, ?, ?, ?)", (date, author, message))

# commit the changes
conn.commit()

# close the connection
conn.close()
