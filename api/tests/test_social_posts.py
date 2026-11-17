from io import BytesIO
from uuid import uuid4

from PIL import Image

from test_evidence import sample_photo
from test_pilot import client, setup_campus, sign_in
from wallnut.database import connect


def test_social_post_creation_and_photo_follow_the_owner_permissions(client):
    student, maria = sign_in(client, "demo-student")
    viewer, _ = sign_in(client, "demo-second-student")
    staff, _ = sign_in(client, "external-staff")
    posts = "/v1/posts"
    post_id = str(uuid4())
    url = f"{posts}/{post_id}"
    photo_url = f"{url}/photo"
    image = ("campus.png", sample_photo(), "image/png")
    data = {"id": post_id, "body": "  Actividad en el campus.  "}

    assert client.get(posts).status_code == 401
    assert client.post(posts, headers=staff, data=data).status_code == 403
    assert client.post(posts, headers=student, data={"id": post_id}).status_code == 422
    invalid_photo = client.post(posts, headers=student, data=data,
                                files={"photo": ("fake.png", b"<html>not a photo", "image/png")})
    assert invalid_photo.status_code == 415

    response = client.post(posts, headers=student, data=data, files={"photo": image})
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["id"] == post_id and created["author_id"] == maria["id"]
    assert created["mine"] and created["has_photo"] and created["updated_at"] is None
    assert created["body"] == "Actividad en el campus." and not created["hidden"]
    assert not created["author_profile_visible"]
    assert client.post(posts, headers=student, data=data, files={"photo": image}).json() == created
    assert client.post(posts, headers=viewer, data=data, files={"photo": image}).status_code == 409
    assert client.put(url, headers=viewer, data={"body": "Otro texto"}).status_code == 403
    assert client.delete(url, headers=viewer).status_code == 403

    assert client.put("/v1/my-campus-profile", headers=student, json={"visible": True}).is_success
    feed = client.get(posts, headers=viewer)
    assert feed.headers["cache-control"] == "private, no-store"
    assert feed.json() == [{**created, "mine": False, "author_profile_visible": True}]
    assert client.get(f"{posts}?offset=1", headers=viewer).json() == []
    assert client.get(photo_url).status_code == 401
    photo = client.get(photo_url, headers=viewer)
    assert photo.headers["content-type"] == "image/jpeg"
    assert photo.headers["cache-control"] == "private, no-store"
    with Image.open(BytesIO(photo.content)) as decoded:
        assert decoded.size == (1600, 960)
        assert "location" not in decoded.info and not decoded.getexif()

    only_photo = client.put(url, headers=student, data={"body": ""})
    assert only_photo.status_code == 200, only_photo.text
    assert only_photo.json()["body"] == "" and only_photo.json()["has_photo"]
    assert client.put(url, headers=student, data={"remove_photo": "true"}).status_code == 422
    edited = client.put(url, headers=student, data={"body": "Actualización", "remove_photo": "true"}).json()
    assert edited["updated_at"] and not edited["has_photo"] and edited["body"] == "Actualización"
    assert client.get(photo_url, headers=viewer).status_code == 404
    assert client.post(posts, headers=student, data=data, files={"photo": image}).json() == edited
    assert client.delete(url, headers=student).status_code == 204
    assert client.delete(url, headers=student).status_code == 204
    assert client.get(posts, headers=student).json() == []
    assert client.post(posts, headers=student, data=data, files={"photo": image}).status_code == 409


def test_review_queue_deduplicates_reports_and_guards_hidden_photo(client):
    admin, _, _ = setup_campus(client)
    student, _ = sign_in(client, "demo-student")
    viewer, _ = sign_in(client, "demo-second-student")
    staff, _ = sign_in(client, "external-staff")
    posts = "/v1/posts"
    reports = "/v1/post-reports"
    post_id = str(uuid4())
    url = f"{posts}/{post_id}"
    report_url = f"{url}/report"
    photo_url = f"{url}/photo"
    moderation = f"{url}/moderation"
    response = client.post(posts, headers=student, data={"id": post_id},
                           files={"photo": ("campus.png", sample_photo(), "image/png")})
    assert response.status_code == 201, response.text

    assert client.get(reports, headers=viewer).status_code == 403
    assert client.put(moderation, headers=viewer, json={"reason": "Ocultar", "hidden": True}).status_code == 403
    report = {"reason": "La foto necesita revisión."}
    assert client.post(report_url, headers=student, json=report).status_code == 403
    assert client.post(report_url, headers=viewer, json=report).status_code == 204
    assert client.post(report_url, headers=viewer, json=report).status_code == 204
    assert client.post(report_url, headers=staff, json=report).status_code == 204
    assert client.get(posts, headers=viewer).json()[0]["reported"]
    queued = client.get(reports, headers=admin).json()
    assert len(queued) == 1 and queued[0]["report_count"] == 2
    assert queued[0]["post"]["id"] == post_id and queued[0]["latest_reason"] == report["reason"]

    hidden = {"reason": "Ocultada tras revisar la foto.", "hidden": True}
    assert client.put(moderation, headers=admin, json=hidden).json()["hidden"]
    assert client.put(moderation, headers=admin, json=hidden).json()["hidden"]
    assert client.get(reports, headers=admin).json() == []
    assert client.get(f"{reports}?hidden=true", headers=admin).json()[0]["post"]["hidden"]
    assert client.get(posts, headers=viewer).json() == []
    assert client.get(posts, headers=student).json()[0]["moderation_reason"] == hidden["reason"]
    assert client.get(photo_url, headers=viewer).status_code == 404
    assert client.get(photo_url, headers=student).status_code == 200
    assert client.get(photo_url, headers=admin).status_code == 200
    assert client.post(report_url, headers=staff, json=report).status_code == 404

    restored = client.put(moderation, headers=admin, json={"reason": "Revisión completa", "hidden": False})
    assert restored.is_success and not restored.json()["hidden"]
    assert client.get(photo_url, headers=viewer).status_code == 200
    assert client.get(f"{reports}?hidden=true", headers=admin).json() == []
    assert client.post(report_url, headers=viewer, json=report).status_code == 204
    assert client.get(reports, headers=admin).json() == []
    assert client.put(url, headers=student, data={"body": "Nueva versión del contenido."}).is_success
    assert not client.get(posts, headers=viewer).json()[0]["reported"]
    assert client.post(report_url, headers=viewer, json=report).status_code == 204
    assert client.get(reports, headers=admin).json()[0]["report_count"] == 1
    with connect() as db:
        audit = db.execute(
            "SELECT hidden FROM social_post_moderation WHERE post_id = %s ORDER BY created_at", (post_id,)
        ).fetchall()
    assert audit == [{"hidden": True}, {"hidden": False}]
