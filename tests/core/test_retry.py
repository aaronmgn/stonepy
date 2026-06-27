from stonepy._core.endpoint import AuthPolicy, EndpointSpec
from stonepy._core.models import ResponseModel
from stonepy._core.retry import RetryPolicy


class _R(ResponseModel):
    pass


def _spec(idempotent: bool) -> EndpointSpec[_R]:
    return EndpointSpec(
        name="X",
        method="POST" if not idempotent else "GET",
        path="/x",
        idempotent=idempotent,
        auth_policy=AuthPolicy.SESSION,
        rate_limit_bucket="default",
        response_model=_R,
    )


def test_idempotent_get_retried_on_no_response() -> None:
    p = RetryPolicy(max_retries=3)
    assert p.should_retry(spec=_spec(True), response_received=False, status=None, attempt=0)


def test_nonidempotent_post_never_retried_on_timeout() -> None:
    p = RetryPolicy(max_retries=3)
    assert not p.should_retry(spec=_spec(False), response_received=False, status=None, attempt=0)


def test_no_retry_past_budget() -> None:
    p = RetryPolicy(max_retries=1)
    assert not p.should_retry(spec=_spec(True), response_received=False, status=None, attempt=1)


def test_5xx_retried_only_for_idempotent() -> None:
    p = RetryPolicy(max_retries=3)
    assert p.should_retry(spec=_spec(True), response_received=True, status=503, attempt=0)
    assert not p.should_retry(spec=_spec(False), response_received=True, status=503, attempt=0)


def test_rate_limit_retry_has_dedicated_predicate() -> None:
    p = RetryPolicy(max_retries=2)

    assert p.should_retry_rate_limit(spec=_spec(True), attempt=0)
    assert not p.should_retry_rate_limit(spec=_spec(True), attempt=2)
    assert not p.should_retry_rate_limit(spec=_spec(False), attempt=0)
