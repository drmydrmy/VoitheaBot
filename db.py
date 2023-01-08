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
    user_data_tuple = res.fetchone()
    user_data = {
        'user_id' : user_data_tuple[0],
        'username' : user_data_tuple[1],
        'first_name' : user_data_tuple[2],
        'payment_method' : user_data_tuple[3],
        'payment_data' : user_data_tuple[4],
        'invited_users_amount' : user_data_tuple[5],
        'invited_by' : user_data_tuple[6]
    }
    return(user_data)

def add_user_payment(payment_method, payment_data, user_id):
    query = "UPDATE users SET payment_method = ?, payment_data = ? WHERE user_id = ?"
    cur.execute(query, (payment_method, payment_data, user_id))
    con.commit()

def change_user_payment_method(payment_method, user_id):
    query = "UPDATE users SET payment_method = ? WHERE user_id = ?"
    cur.execute(query, (payment_method, user_id))
    con.commit()

def change_user_payment_data(payment_data, user_id):
    query = "UPDATE users SET payment_data = ? WHERE user_id = ?"
    cur.execute(query, (payment_data, user_id))
    con.commit()

def add_user_invited_by(invited_by, user_id):
    inviter_user_data = get_user_data(invited_by)
    query = "UPDATE users SET invited_users_amount = ? WHERE user_id = ?"
    cur.execute(query, (inviter_user_data['invited_users_amount'] + 1, invited_by))
    query = "UPDATE users SET invited_by = ? WHERE user_id = ?"
    cur.execute(query, (invited_by, user_id))
    con.commit()

def check_user_exists(user_id):
    query = "SELECT * FROM users WHERE user_id = ?"
    res = cur.execute(query, (user_id,))
    return not (res.fetchone() is None)

def check_inviter_is_invited(user_id, inviter_user_id):
    inviter_user_data = get_user_data(inviter_user_id)
    return user_id == inviter_user_data['invited_by']
