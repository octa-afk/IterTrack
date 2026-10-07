def test_get_trucks_empty(client):
    response = client.get("/trucks")
    assert response.status_code == 200
    assert response.json() == []


def test_add_truck_and_list(client):
    response = client.post(
        "/trucks",
        json={"truck": {"id": 1, "plate": "ABC123"}, "location": {"lat": -31.42, "long": -64.18}},
    )
    assert response.status_code == 200
    trucks = client.get("/trucks").json()
    assert len(trucks) == 1
    assert trucks[0]["plate"] == "ABC123"


def test_duplicate_truck_returns_400(client):
    payload = {"truck": {"id": 1, "plate": "ABC123"}, "location": {"lat": -31.42, "long": -64.18}}
    assert client.post("/trucks", json=payload).status_code == 200
    assert client.post("/trucks", json=payload).status_code == 400


def test_invalid_coordinates_rejected(client):
    response = client.post(
        "/trucks",
        json={"truck": {"id": 2, "plate": "XYZ789"}, "location": {"lat": 123, "long": -64.18}},
    )
    assert response.status_code == 422
