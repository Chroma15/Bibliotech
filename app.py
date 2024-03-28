from flask import Flask, request, jsonify
import json
import os
from datetime import datetime,timedelta
import hashlib

app=Flask(__name__)

def error(msg: str):
    return jsonify({"success": False, "message": msg})

def generate_auth_token(email):
    # Am adaugat un cod secret ca sa fie spre imposibil de hasit token-ul 
    secret_cod="BOOM"
    data_to_hash=f"{email}{secret_cod}".encode('utf-8')
    hashed_token=hashlib.sha256(data_to_hash).hexdigest()

    return hashed_token

def is_admin(auth_token):
    for user in users:
        if generate_auth_token(user.get("email")) == auth_token and user.get("type") == "1":
            return True
    return False

def is_authenticated(auth_token):
    user_email = get_email(auth_token)
    return user_email is not None

def calculate_remaining_time(return_date,extend_time=0):
    max_duration=20
    current_date=datetime.now()
    if type(return_date)!="datetime.datetime":
        return_date = datetime.strptime(return_date, "%Y-%m-%d")
    remaining_time = (return_date - current_date).days
    remaining_time += extend_time
    return remaining_time

def extend_transaction(transaction, extend_time):
    max_extensions = 2
    max_extend_time = 5

    if transaction["number_of_extensions"] >= max_extensions:
        return error("Maximum number of extensions reached."),400
    return_date=transaction["return_date"]
    if type(return_date)!="datetime.datetime":
        return_date = datetime.strptime(return_date, "%Y-%m-%d")

    if extend_time < 1 or extend_time > max_extend_time:
        return error(f"Invalid extend time. It should be between 1 and 5.")
    new_return_date = return_date + timedelta(days=extend_time)

    transaction["return_date"] = new_return_date.strftime("%Y-%m-%d")
    transaction["number_of_extensions"] += 1
    print(transaction)
    
    return {"success": f"Transaction extended by {extend_time} days." }


def get_book_name(book_id):
    for book in biblioteca:
        if book["id"]==book_id:
            return book["book_name"]
    return error("Book not found"),404

def get_email(auth_token):
    for user in users:
        if generate_auth_token(user.get("email")) == auth_token:
            return user.get("email")

def get_user_transactions(email):
    user_transactions = [t for t in transactions if t.get("email") == email]
    if user_transactions:
        return user_transactions
    return error("The user did not make any transactions"),404

def calculate_transaction_status(transaction):
    return_date = transaction.get("return_date")
    if type(return_date)!="datetime.datetime":
        return_date = datetime.strptime(return_date, "%Y-%m-%d")
    if return_date:
        current_date = datetime.now()

        if current_date > return_date:
            transaction["status"]="in intarziere"
            return "in intarziere"
        elif current_date == return_date:
            transaction["status"]="incheiata"
            return "incheiata"
        else:
            transaction["status"]="in desfasurare"
            return "in desfasurare"
    else:
        transaction["status"]="incheiata"
        return "incheiata"

def format_transactions(transactions):
    formatted_transactions=[]

    for transaction in transactions:
        book_id = transaction.get("book_id", "")
        book_name = get_book_name(book_id)
        status = calculate_transaction_status(transaction)

        formatted_transaction = {
            "transaction_id": transaction.get("transaction_id", ""),
            "book_id": book_id,
            "book_name": book_name,
            "status": status,
        }

        formatted_transactions.append(formatted_transaction)

    if not formatted_transactions:
        return error("No transactions found"),404
        
    return formatted_transactions

def get_user_transactions(user_email):
    user_transactions = [t for t in transactions if t["email"] == user_email]

    if not user_transactions:
        return error("User has no transactions"), 404

    transactions_data = []

    for transaction in user_transactions:
        book_id = transaction["book_id"]
        book_name = get_book_name(book_id)
        status = calculate_transaction_status(transaction)

        transaction_data = {
            "transaction_id": transaction["transaction_id"],
            "book_id": book_id,
            "book_name": book_name,
            "status": status
        }

        transactions_data.append(transaction_data)

    return transactions_data



def is_user_limited(email):
    user_transactions = [t for t in transactions if t["email"] == email]
    return len(user_transactions) >= 5


users=[]
biblioteca=[]
id=0

@app.route("/register", methods=['POST'])
def register():
    first_name=request.form.get("first_name","")
    last_name=request.form.get("last_name","")
    email=request.form.get("email","")
    password=request.form.get("password","")
    type=request.form.get("type","")

    if any(user['email']==email for user in users):
        return error("User already exists"),400

    new_user= {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password": password,
        "type": type
    }

    users.append(new_user)

    return jsonify(new_user),201


@app.route("/login", methods=['POST'])
def login():
    email=request.form.get("email","")
    password=request.form.get("password","")

    for user in users:
        if email==user["email"] and password==user["password"]:
            auth_token=generate_auth_token(user["email"])
            return jsonify({"auth_token": auth_token}),200
        
    return error("User does not exist"), 404

@app.route("/book",methods=['POST'])
def book():
    auth_token=request.form.get("auth_token","")
    book_name=request.form.get("book_name","")
    book_author=request.form.get("book_author","")
    book_description=request.form.get("book_description","")

    # if not is_admin(auth_token):
    #     return error("Unauthorized"),401

    if any(carte["book_name"]==book_name for carte in biblioteca):
        return error("User already exists"),400
    
    global id
    id+=1

    new_book= {
        "id": id,
        "book_name": book_name,
        "book_author": book_author,
        "book_description": book_description,
    }

    biblioteca.append(new_book)

    return jsonify(new_book),201

@app.route("/books", methods=['POST'])
def books():
    imput_data=request.json
    auth_token=imput_data["auth_token"]
    books_data=imput_data["books"]

    if not is_admin(auth_token):
        return error("Unauthorized"),401
    
    added_books=[]
    
    for book in books_data:
        global id
        id += 1
        book_name = book.get("book_name", "")
        book_author = book.get("book_author", "")
        book_description = book.get("book_description", "")

        if any(carte["book_name"] == book_name for carte in biblioteca):
            return error(f"Book '{book_name}' already exists"), 400

        new_book = {
            "id": id,
            "book_name": book_name,
            "book_author": book_author,
            "book_description": book_description,
        }
        biblioteca.append(new_book)
        added_books.append(new_book)
    
    response_data = {"books": added_books}
    return jsonify(response_data), 201

@app.route("/book", methods=['GET'])
def get_book():
    id = int(request.args.get("id", 0))
    auth_token = request.args.get("auth_token", "")

    book = next((book for book in biblioteca if book["id"] == id), None)

    if book is None:
        return error("Book not found"), 404
    
    status = book.get("status", "disponibila")
    rating = book.get("rating", "")
    reviews = book.get("reviews", [])

    if auth_token:
        book["status"] = status
        book["rating"] = rating
        book["reviews"] = [{"rating": r.get("rating", ""), "review": r.get("review", ""), "author": r.get("author", "")} for r in reviews]
        
        return jsonify({
            "id": book["id"],
            "book_name": book["book_name"],
            "book_author": book["book_author"],
            "book_description": book["book_description"],
            "status": status,
            "rating": rating,
            "reviews": book["reviews"]
        }), 200
    else:
        book["status"] = status
        book["rating"] = rating
        book["reviews"] = [{"rating": r.get("rating", ""), "review": r.get("review", ""), "author": r.get("author", "")} for r in reviews]
        
        return jsonify({
            "id": book["id"],
            "book_name": book["book_name"],
            "book_author": book["book_author"],
            "book_description": book["book_description"],
            "status": status,
            "rating": rating,
            "reviews": book["reviews"]
        }), 200

@app.route("/books", methods=['GET'])
def get_books():
    if not biblioteca:
        return error("No books available"), 404
    
    books_data=[]
    for book in biblioteca:
        status = book.get("status", "disponibila")
        rating=book.get("rating","")
        books_data.append({
            "id": book["id"],
            "book_name": book["book_name"],
            "book_author": book["book_author"],
            "book_description": book["book_description"],
            "status": status,
            "rating": rating,
        })
        book["status"] = status
        book["rating"] = rating
    return jsonify({"books": books_data}),200

transaction_id=0
transactions=[]

@app.route("/transaction", methods=['POST'])
def transaction():
    auth_token=request.form.get("auth_token","")
    book_id=int(request.form.get("book_id",0))
    borrow_time=int(request.form.get("borrow_time",""))

    email = None

    for user in users:
        email = user.get("email")
        if generate_auth_token(email) == auth_token:
            if is_user_limited(email):
                return error("User reached maximum transaction limit"), 400

    if email is None:
        return error("User not found"), 404

    selected_book= next((book for book in biblioteca if book["id"] == book_id), None)
    
    if selected_book is None:
        return error("Book not found"), 404
    
    print(selected_book.get("status"))
    if selected_book.get("status")!="disponibila":
        return error("Book not available for borrowing"), 400
    
    selected_book["status"]="imprumutata"

    return_date=datetime.now()+timedelta(days=borrow_time)

    global transaction_id
    transaction_id+=1
    
    new_transaction={
        "transaction_id": transaction_id,
        "email": email,
        "book_id":book_id,
        "borrow_time":borrow_time,
        "return_date":return_date.strftime("%Y-%m-%d"),
        "number_of_extensions":0,
        "status":"in desfasurare"
    }

    transactions.append(new_transaction)

    return jsonify({
        "success": "Transaction created",
        "transaction_id":transaction_id
    })

@app.route("/transaction", methods=["GET"])
def get_transaction():
    auth_token=request.args.get("auth_token","")
    transaction_id=int(request.args.get("transaction_id",0))

    transaction = next((t for t in transactions if t["transaction_id"] == transaction_id), None)

    if transaction:
        
        return_date=transaction["return_date"]
        print(type(return_date))
        borrow_time=transaction["borrow_time"]
        extension_count=transaction["number_of_extensions"]
        remaining_time=calculate_remaining_time(return_date)

            
        if remaining_time==0:
            status="incheiata"
        elif remaining_time>0:
            status="in desfasurare"
        else:
            status="in intarziere"
        
        response_data={
            "book_id":transaction["book_id"],
            "borrow_time":borrow_time,
            "remaining_time":remaining_time,
            "number_of_extensions":extension_count,
            "status":status
        }

        transaction["status"]=status

        return jsonify(response_data),200
    
    else:
        return error("Transaction with ID {transaction_id} not found"),404

@app.route("/transactions", methods=['GET'])
def get_transactions():
    auth_token=request.args.get("auth_token","")

    if is_admin(auth_token):
        all_transactions=transactions
        response_data=format_transactions(all_transactions)
        return jsonify(response_data),200

    else:
        user_email=get_email(auth_token)
        user_transactions=get_user_transactions(user_email)
        response_data = format_transactions(user_transactions)
        return jsonify(response_data), 200

@app.route("/extend", methods=['POST'])
def extend():
    auth_token=request.form.get("auth_token","")
    transaction_id=int(request.form.get("transaction_id",0))
    extend_time=int(request.form.get("extend_time",0))

    user_email = get_email(auth_token)
    if user_email is None:
        return error("Invalid auth_token."), 401

    transaction = next((t for t in transactions if t["transaction_id"] == transaction_id), None)

    if transaction is None:
        return error("Transaction not found."), 404

    if transaction["email"] != user_email:
        return error("Unauthorized. The transaction doesn't belong to the user."), 401
    
    result=extend_transaction(transaction,extend_time)

    return jsonify(result)

return_requests = []
return_id=0
@app.route("/return", methods=["POST"])
def return_book():
    auth_token=request.form.get("auth_token","")
    transaction_id=int(request.form.get("transaction_id",0))

    transaction = next((t for t in transactions if t["transaction_id"] == transaction_id), None)

    if transaction is None:
        return error("Transaction not found."), 404
    global return_id
    return_id+=1
    return_requests.append({"id": return_id, "transaction_id": transaction_id})

    user = next((u for u in users if generate_auth_token(u.get("email")) == auth_token), None)

    if not user:
        return error("User not found"), 404
    
    return_date=datetime.strptime(transaction["return_date"],"%Y-%m-%d")
    overdue_days = (datetime.now() -return_date ).days
    penalty_count = transaction.get("penalty_count", 0)

    if overdue_days > 0:
        penalty_count += 1  

        if penalty_count == 1:
            return jsonify({"success": "First offense - Warning"}), 200
        elif penalty_count == 2:
            transaction["number_of_extensions"] = 1
            return jsonify({"success": "Second offense - Reduced extensions to 1"}), 200
        elif penalty_count == 3:
            transaction["number_of_extensions"] = 0
            return jsonify({"success": "Third offense - Extensions removed"}), 200
        elif penalty_count == 4:
            user["blocked_until"] = datetime.now() + timedelta(days=30)
            return jsonify({"success": "Fourth offense - User blocked for 30 days"}), 200
        else:
            return error("Invalid penalty count"), 400

    if "blocked_until" in user and datetime.now() > user["blocked_until"]:
        penalty_count -=1
        if penalty_count==0:
            del user["blocked_until"]

    transaction["penalty_count"] = penalty_count

    return jsonify({"success": "Return request created"}), 200


@app.route("/returns", methods=["GET"])
def returns():
    auth_token=request.args.get("auth_token","")

    if not is_admin(auth_token):
        return error("Unauthorized"),401

    if return_requests:
        return jsonify({"return_requests": return_requests}), 200
    else:
        return error("No return requests available"), 404

@app.route("/return/end", methods=["POST"])
def return_end():
    auth_token=request.form.get("auth_token","")
    return_id=int(request.form.get("return_id",0))

    if not is_admin(auth_token):
        return error("Unauthorized"),401
    
    return_request = next((r for r in return_requests if r["id"] == return_id), None)

    if return_request:
        transaction_id = return_request["transaction_id"]
        transaction = next((t for t in transactions if t["transaction_id"] == transaction_id), None)

        if transaction:
            transaction["status"] = "incheiata"
            return_requests.remove(return_request)

            return jsonify({"success": "You successfully returned the book"}), 200
        else:
            return error(f"Transaction with ID {transaction_id} not found"), 404
    else:
        return error(f"Return request with ID {return_id} not found"), 404

@app.route("/review", methods=["POST"])
def review():
    auth_token=request.form.get("auth_token","")
    book_id=int(request.form.get("book_id",0))
    rating=float(request.form.get("rating",0))
    text=request.form.get("text","")

    if not is_authenticated(auth_token):
        return error("Unauthorized"), 401
    
    book = next((book for book in biblioteca if book["id"] == book_id), None)
    if not book:
        return error("Book not found"), 404
    
    if 'reviews' not in book:
        book['reviews'] = []

    if not (1 <= rating <= 5):
        return error("Invalid rating. Rating should be between 1 and 5"), 400
    
    new_review = {"rating": rating, "text": text, "author": get_email(auth_token)}
    book["reviews"].append(new_review)
    print(book)
    return jsonify({"success": "Review added successfully"}), 200


if __name__=='__main__':
    app.run(debug=True)