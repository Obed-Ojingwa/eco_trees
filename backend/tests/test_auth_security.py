from uuid import uuid4

from app.core.security import decode_token, hash_secret, issue_token, verify_secret
from app.modules.plots.schemas import PlantingInput
from pydantic import ValidationError


def test_argon2_secret_hash_verifies_only_matching_secret() -> None:
    password_hash = hash_secret("2468")

    assert verify_secret("2468", password_hash)
    assert not verify_secret("wrong", password_hash)


def test_jwt_round_trips_user_identity_and_role() -> None:
    user_id = uuid4()

    claims = decode_token(issue_token(user_id, "farmer"))

    assert claims["sub"] == str(user_id)
    assert claims["role"] == "farmer"


def test_unknown_species_is_rejected() -> None:
    try:
        PlantingInput(
            species_code="UNKNOWN",
            trees_planted=10,
            planted_on="2025-01-01",
        )
    except ValidationError as error:
        assert "species list" in str(error)
    else:
        raise AssertionError("Unknown species should fail validation.")
