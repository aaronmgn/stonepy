from stonepy._core.endpoint import AuthPolicy, EndpointSpec, Param
from stonepy._core.models import ResponseModel


class _R(ResponseModel):
    pass


def test_spec_is_frozen_and_holds_metadata() -> None:
    spec = EndpointSpec(
        name="GetOrder",
        method="GET",
        path="/order/{OrderId}",
        idempotent=True,
        auth_policy=AuthPolicy.SESSION,
        rate_limit_bucket="default",
        response_model=_R,
        params=(Param("OrderId", "path", "order_id"),),
    )
    assert spec.idempotent is True
    assert spec.params[0].location == "path"
    try:
        spec.name = "x"  # type: ignore[misc]
    except Exception as exc:  # frozen dataclass raises FrozenInstanceError
        assert "FrozenInstanceError" in type(exc).__name__
    else:
        raise AssertionError("spec should be frozen")


def test_spec_is_generic_over_response_model() -> None:
    assert EndpointSpec[_R] is not None
