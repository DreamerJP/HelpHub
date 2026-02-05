from flask import url_for


def test_login_logout(client, app, admin_user):
    """Test login and logout flow."""
    # Login Page loads
    response = client.get(url_for("auth.login"))
    assert response.status_code == 200
    assert b"Acessar Plataforma" in response.data

    # Valid Login (No follow redirects)
    response = client.post(
        url_for("auth.login"),
        data={"username": "admin_test", "password": "123456"},
        follow_redirects=False,
    )

    print(f"DEBUG POST STATUS: {response.status_code}")
    print(f"DEBUG POST LOCATION: {response.headers.get('Location')}")
    print(f"DEBUG POST COOKIE: {response.headers.get('Set-Cookie')}")

    # Manually verify redirect
    if response.status_code != 302:
        print(f"DEBUG RESPONSE BODY: {response.data.decode('utf-8')}")
    assert response.status_code == 302

    # Follow redirect manually
    next_url = response.headers.get("Location")
    response = client.get(next_url)

    print(f"DEBUG FOLLOW STATUS: {response.status_code}")
    with client.session_transaction() as sess:
        print(f"DEBUG SESSION AFTER FOLLOW: {sess}")

    # Access Protected Page
    response = client.get(url_for("layout.index"))
    if response.status_code == 302:
        print(f"DEBUG AUTH: Redirect to {response.headers.get('Location')}")
    assert response.status_code == 200, "Should be accessible after login"

    # Logout
    response = client.get(url_for("auth.logout"), follow_redirects=True)
    assert response.status_code == 200
    assert b"Acessar Plataforma" in response.data
