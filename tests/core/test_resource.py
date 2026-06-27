from stonepy._core.resource import ABI_VERSION, BaseResource


def test_base_resource_holds_ctx() -> None:
    sentinel = object()
    r = BaseResource(sentinel)  # type: ignore[arg-type]
    assert r._ctx is sentinel
    assert ABI_VERSION == 1
    assert isinstance(ABI_VERSION, int)
