import sqlite3 as sql
from datetime import date


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

def check_user_is_admin(user_id):
    query = "SELECT * FROM admins WHERE user_id = ?"
    res = cur.execute(query, (user_id,))
    return not (res.fetchone() is None)

def get_super_admin_value(user_id):
    query = "SELECT is_super_admin FROM admins WHERE user_id = ?"
    res = cur.execute(query, (user_id,))
    return res.fetchone()[0]

def add_order(name, executor, client, handler, system_percent, executor_cost):
    query = "INSERT INTO orders (name, executor, client, handler, system_percent, executor_cost, inviter, date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    query_to_get_inviter = "SELECT invited_by FROM users WHERE username = ?"
    res = cur.execute(query_to_get_inviter, (client[1::],))
    today_date = date.today()
    str_date = today_date.strftime("%d.%m.%Y")
    res = res.fetchone()
    if res is None:
        inviter = None
    else:
        inviter = res[0]
    cur.execute(query, (name, executor[1::], client[1::], handler[1::], float(system_percent.replace(',', '.')), executor_cost, inviter, str_date))
    con.commit()

def get_user_id_by_username(username):
    query = "SELECT user_id FROM users WHERE username = ?"
    res = cur.execute(query, (username[1::],))
    res = res.fetchone()
    if res is None:
        return -1
    else:
        return res[0]

def add_admin(user_id, is_superadmin, user_info):
    query = "INSERT OR IGNORE INTO admins VALUES (?, ?, ?)"
    cur.execute(query, (user_id, is_superadmin, user_info))
    con.commit()

def get_page_db_admins(limit, offset):
    query = "SELECT * FROM admins LIMIT ? OFFSET ?"
    res = cur.execute(query, (limit, offset))
    res = res.fetchall()
    if res is None:
        return -1
    else:
        return res

def get_count_all_rows_admins():
    query = "SELECT COUNT(*) FROM admins"
    res = cur.execute(query)
    res = res.fetchone()[0]
    return res

def change_info_admins(user_id, user_info):
    query = "UPDATE admins SET user_info = ? WHERE user_id = ?"
    cur.execute(query, (user_info, user_id))
    con.commit()

def delete_admin(user_id):
    query = "DELETE FROM admins WHERE user_id = ?"
    cur.execute(query, (user_id,))
    con.commit()

def get_count_all_rows_orders():
    query = "SELECT COUNT(*) FROM orders"
    res = cur.execute(query)
    res = res.fetchone()[0]
    return res

def get_page_db_orders(limit, offset):
    query = "SELECT * FROM orders LIMIT ? OFFSET ?"
    res = cur.execute(query, (limit, offset))
    res = res.fetchall()
    if res is None:
        return -1
    else:
        return res

def check_order_exists(order_id):
    query = "SELECT * FROM orders WHERE id = ?"
    res = cur.execute(query, (order_id,))
    res = res.fetchone()
    return not (res is None)

def get_order_data(order_id):
    query = "SELECT * FROM orders WHERE id = ?"
    res = cur.execute(query, (order_id,))
    res = res.fetchone()
    return res

def delete_order(order_id):
    query = "DELETE FROM orders WHERE id = ?"
    cur.execute(query, (order_id,))
    con.commit()

def alias_to_id(alias):
    query = "SELECT * FROM aliases WHERE alias = ?"
    res = cur.execute(query, (alias,))
    res = res.fetchone()
    if res is None:
        return(-1)
    else: 
        return(res[0])

def change_alias(user_id, new_alias):
    query = "SELECT * FROM aliases WHERE user_id = ?"
    res = cur.execute(query, (user_id,))
    res = res.fetchone()
    if res is None:
        query = "INSERT OR IGNORE INTO aliases VALUES (?, ?)"
        cur.execute(query, (user_id, new_alias))
    else: 
        query = "UPDATE aliases SET alias = ? WHERE user_id = ?"
        cur.execute(query, (new_alias, user_id))
    con.commit()

def id_to_alias(user_id):
    query = "SELECT * FROM aliases WHERE user_id = ?"
    res = cur.execute(query, (user_id,))
    res = res.fetchone()
    if res is None:
        return -1
    else:
        return res[1]

def fetch_all_prices():
    query = "SELECT * FROM prices"
    res = cur.execute(query)
    res = res.fetchall()
    if res is None:
        return -1
    else:
        return(res)

def get_count_orders_by(username):
    query = "SELECT COUNT(*) FROM orders WHERE client = ?"
    res = cur.execute(query, (username,))
    res = res.fetchone()[0]
    return res

def init_payout_orders(username):
    query = "INSERT OR IGNORE INTO payout_orders VALUES (?, ?, ?, ?)"
    cur.execute(query, (username, 0, "NO", 0))
    con.commit()

def get_payout_order_data(username):
    query = "SELECT * FROM payout_orders WHERE username = ?"
    res = cur.execute(query, (username,))
    payout_order_data_tuple = res.fetchone()
    return {
        "username" : payout_order_data_tuple[0],
        "invited" : payout_order_data_tuple[1],
        "open" : payout_order_data_tuple[2],
        "new_invited" : payout_order_data_tuple[3]                                   
    }

def update_payout_order_data(username, invited, open, new_invited):
    query = "UPDATE payout_orders SET invited = ?, open = ?, new_invited = ? WHERE username = ?"
    cur.execute(query,(invited, open, new_invited, username))
    con.commit()