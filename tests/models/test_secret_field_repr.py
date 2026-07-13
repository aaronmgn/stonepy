from __future__ import annotations

from stonepy.models import (
    ApiChangePasswordRequestDTO,
    ApiLogOnRequestDTO,
    ApiLogOnResponseDTOv2,
)


def test_logon_request_repr_hides_credentials() -> None:
    dto = ApiLogOnRequestDTO(
        UserName="me", Password="hunter2", AppKey="key-123", AppVersion="v", AppComments=""
    )
    for rendered in (repr(dto), str(dto)):
        assert "hunter2" not in rendered
        assert "key-123" not in rendered
        assert "me" in rendered  # non-secret fields stay visible


def test_logon_response_repr_hides_session_and_two_fa_token() -> None:
    dto = ApiLogOnResponseDTOv2.model_validate({"Session": "tok-abc", "TwoFAToken": "tfa-xyz"})
    for rendered in (repr(dto), str(dto)):
        assert "tok-abc" not in rendered
        assert "tfa-xyz" not in rendered


def test_change_password_request_repr_hides_both_passwords() -> None:
    dto = ApiChangePasswordRequestDTO.model_construct(password="old-pw", new_password="new-pw")
    for rendered in (repr(dto), str(dto)):
        assert "old-pw" not in rendered
        assert "new-pw" not in rendered
