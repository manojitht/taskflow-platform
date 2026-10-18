def signup(client, email):
    return client.post("/signup", data={"email": email, "password": "password123"}, follow_redirects=False)


def test_signup_and_create_task(client):
    assert signup(client, "a@example.com").status_code == 303
    r = client.post("/tasks", data={"title": "Write tests"}, follow_redirects=True)
    assert "Write tests" in r.text


def test_wrong_password_rejected(client):
    signup(client, "a@example.com")
    client.post("/logout")
    r = client.post("/login", data={"email": "a@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_users_cannot_see_each_others_tasks(client):
    signup(client, "a@example.com")
    client.post("/tasks", data={"title": "Secret task"})
    client.post("/logout")
    signup(client, "b@example.com")
    r = client.get("/")
    assert "Secret task" not in r.text