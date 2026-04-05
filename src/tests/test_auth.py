auth_prefix = f"/api/v1/auth"


def test_user_creation(fake_session, fake_user_service, test_client):
    signup_data = {
        "username": "tj2332",
        "email": "1111@gmail.com",
        "password": "12345",
        "first_name": "www",
        "last_name": "ttt",
    }
    response = test_client.post(
        url=f"{auth_prefix}/signup",
        json=signup_data,
    )

    assert fake_user_service.user_exists_called_once()
    assert fake_user_service.user_exists_called_once_with(signup_data["email"], fake_session)
