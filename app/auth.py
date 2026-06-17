def fake_login(username, password):
    if username == "admin" and password == "admin": #-> replace with the database and exception
        return {"message": "Login successful"}
    return {"message": "Invalid credentials"}