from test_pilot import client, setup_campus, sign_in


HELP = "/v1/ardi-help"


def test_help_routes_spanish_questions_and_exposes_no_personal_data(client):
    student, _ = sign_in(client, "demo-student")
    assert client.get(HELP).status_code == 401
    assert client.post(HELP, json={"question": "¿Cómo pago?"}).status_code == 401
    choices = client.get(HELP, headers=student)
    assert choices.headers["cache-control"] == "private, no-store"
    assert {"attendance", "nuts", "payments", "grades", "points"}.issubset(
        topic["id"] for topic in choices.json()["topics"]
    )

    questions = [
        ("¿Cómo uso el QR de ASISTÉNCIA?", "attendance", "agenda"),
        ("¿Dónde veo mi código de pago?", "payments", "wallet"),
        ("Quiero canjear Coins por Ardi Points.", "conversion", "wallet"),
        ("¿Cómo gano Ardi Points?", "points", "agenda"),
        ("¿Puedo canjear puntos para la nota?", "grades", "groups"),
        ("¿Cómo abro una nuez con Coins?", "nuts", "ardy"),
        ("¿Cómo registrar resultado del cuadro del torneo?", "events", "events"),
    ]
    for question, topic, action in questions:
        response = client.post(HELP, headers=student, json={"question": question})
        assert response.is_success, response.text
        result = response.json()
        assert result["topic"] == topic and result["action"] == action
        assert set(result) == {"topic", "answer", "action"}
    unknown = "La contraseña de prueba es secreta"
    fallback = client.post(HELP, headers=student, json={"question": unknown}).json()
    assert fallback["action"] is None and fallback["topic"] is None
    assert unknown not in fallback["answer"]
    assert client.post(HELP, headers=student, json={"question": " "}).status_code == 422
    assert client.post(HELP, headers=student, json={"question": "x" * 301}).status_code == 422


def test_help_offers_only_relevant_actions_for_the_current_role(client):
    student, _ = sign_in(client, "demo-student")
    admin, faculty, _ = setup_campus(client)
    staff, _ = sign_in(client, "external-staff")

    def selected(headers, topic):
        response = client.post(HELP, headers=headers, json={"topic": topic, "question": "Ver guía"})
        assert response.is_success, response.text
        return response.json()

    assert selected(student, "budgets")["topic"] is None
    assert selected(admin, "budgets")["action"] == "groups"
    assert "Administración" in selected(admin, "budgets")["answer"]
    assert "Mis grupos" in selected(faculty, "budgets")["answer"]
    assert selected(faculty, "workshops")["action"] == "calls"
    assert selected(admin, "posts")["action"] == "posts"
    assert "Revisar reportes" in selected(admin, "posts")["answer"]
    assert selected(staff, "payments")["action"] is None
    assert selected(staff, "grades")["topic"] is None
    assert selected(staff, "access")["action"] is None
