import sqlite3 as sql


con = sql.connect("voithea_user_base.db")
cur = con.cursor()


def add_user(user_id, username, first_name):
    query = "INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)"
    cur.execute(query, (user_id, username, first_name, '', '', 0, None))
    con.commit()

def get_user_data(user_id):
    query = "SELECT * FROM users WHERE user_id = ?"
    res = cur.execute(query, (user_id,))
    user_data = res.fetchone()
    print(user_data)

def add_user_payment(payment_method, payment_data):
    query = "UPDATE users SET payment_method = ?, payment_data = ?"
    cur.execute(query, (payment_method, payment_data))
    con.commit()