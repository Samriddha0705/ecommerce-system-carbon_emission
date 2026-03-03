from flask import Flask, request, render_template, redirect, url_for, session
import mysql.connector

print("APP FILE LOADED")

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- DATABASE CONNECTION ----------------

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Sam@1907",
    database="ecommerce_system"
)

cursor = db.cursor()

# ---------------- ROOT (Login/Signup Page) ----------------

@app.route('/')
def root():
    if 'user_id' in session:
        return redirect(url_for('products'))
    return render_template('auth.html')


# ---------------- SIGNUP ----------------

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    query = "INSERT INTO Users (name, email, password) VALUES (%s, %s, %s)"
    cursor.execute(query, (name, email, password))
    db.commit()

    session['user_id'] = cursor.lastrowid
    return redirect(url_for('products'))


# ---------------- LOGIN ----------------

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    query = "SELECT user_id FROM Users WHERE email=%s AND password=%s"
    cursor.execute(query, (email, password))
    user = cursor.fetchone()

    if user:
        session['user_id'] = user[0]
        return redirect(url_for('products'))
    else:
        return "Invalid Credentials"


# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('root'))


# ---------------- PRODUCTS PAGE ----------------

@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect(url_for('root'))

    user_id = session['user_id']

    cursor.execute("SELECT product_id, name, description, price, stock FROM Products")
    products = cursor.fetchall()

    # Get cart count
    cursor.execute("""
        SELECT SUM(quantity) 
        FROM Cart_Items ci
        JOIN Cart c ON ci.cart_id = c.cart_id
        WHERE c.user_id = %s
    """, (user_id,))
    
    cart_count = cursor.fetchone()[0]
    if cart_count is None:
        cart_count = 0

    return render_template('products.html', products=products, cart_count=cart_count)



# ---------------- ADD TO CART ----------------

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return redirect(url_for('root'))

    user_id = session['user_id']
    product_id = int(request.form['product_id'])
    quantity = int(request.form['quantity'])

    cursor.execute("SELECT cart_id FROM Cart WHERE user_id=%s", (user_id,))
    cart = cursor.fetchone()

    if cart:
        cart_id = cart[0]
    else:
        cursor.execute("INSERT INTO Cart (user_id) VALUES (%s)", (user_id,))
        db.commit()
        cart_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO Cart_Items (cart_id, product_id, quantity) VALUES (%s, %s, %s)",
        (cart_id, product_id, quantity)
    )
    db.commit()

    return redirect(url_for('products'))

#------------Cart-------------------------
@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        return redirect(url_for('root'))

    user_id = session['user_id']

    cursor.execute("""
        SELECT ci.product_id, p.name, p.price, ci.quantity
        FROM Cart_Items ci
        JOIN Cart c ON ci.cart_id = c.cart_id
        JOIN Products p ON ci.product_id = p.product_id
        WHERE c.user_id = %s
    """, (user_id,))

    items = cursor.fetchall()

    total = sum(item[2] * item[3] for item in items)

    return render_template('cart.html', items=items, total=total)

# ---------------- PLACE ORDER ----------------

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return redirect(url_for('root'))

    user_id = session['user_id']

    cursor.execute("SELECT cart_id FROM Cart WHERE user_id=%s", (user_id,))
    cart = cursor.fetchone()

    if not cart:
        return "Cart is empty"

    cart_id = cart[0]

    cursor.execute("""
        SELECT product_id, quantity 
        FROM Cart_Items 
        WHERE cart_id=%s
    """, (cart_id,))
    items = cursor.fetchall()

    total = 0

    for product_id, quantity in items:
        cursor.execute("SELECT price FROM Products WHERE product_id=%s", (product_id,))
        price = cursor.fetchone()[0]
        total += price * quantity

    cursor.execute(
        "INSERT INTO Orders (user_id, total_amount, status) VALUES (%s, %s, %s)",
        (user_id, total, "Placed")
    )
    db.commit()

    order_id = cursor.lastrowid

    for product_id, quantity in items:
        cursor.execute("SELECT price FROM Products WHERE product_id=%s", (product_id,))
        price = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO Order_Items (order_id, product_id, quantity, price)
            VALUES (%s, %s, %s, %s)
        """, (order_id, product_id, quantity, price))

        cursor.execute("""
            UPDATE Products
            SET stock = stock - %s
            WHERE product_id = %s
        """, (quantity, product_id))

    cursor.execute("DELETE FROM Cart_Items WHERE cart_id=%s", (cart_id,))
    db.commit()

    return "Order placed successfully!"


# ---------------- RUN APP ----------------

if __name__ == '__main__':
    app.run(debug=True)
