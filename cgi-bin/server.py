#!/usr/bin/env python3
#  форма для 8-го инд. задания

import cgi
import html
import sqlite3
import cgitb; cgitb.enable()

filename ='./my.db'
db = sqlite3.connect(filename)
cursor = db.cursor()

form = cgi.FieldStorage()
text1 = form.getfirst("TEXT_1", "не задано")
text2 = form.getfirst("TEXT_2", "0")
text1 = html.escape(text1)
text2 = html.escape(text2)

cursor.execute("INSERT INTO architect(name, year) VALUES (?,?)", (text1, int(text2)))
db.commit()

print("Content-type: text/html\n")
print("""<!DOCTYPE HTML>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Обработка данных форм</title>
        </head>
        <body>""")

# выводим всех архитекторов
cursor.execute("SELECT name, year FROM architect")
records = cursor.fetchall()
for i, record in enumerate(records):
    print("{0}) {1} - {2}<br>".format(i + 1, record[0], record[1]))

print("""</body>
        </html>""")

# http://localhost:8000/prog_ind8.html
