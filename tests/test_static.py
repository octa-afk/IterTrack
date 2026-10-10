def test_root_serves_login_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="login-form"' in response.text


def test_map_serves_map_page(client):
    response = client.get("/map")
    assert response.status_code == 200
    assert 'id="map"' in response.text
