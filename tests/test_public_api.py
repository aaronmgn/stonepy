import inspect


def test_public_exports() -> None:
    import stonepy

    expected_exports = {
        "StoneXClient",
        "AsyncStoneXClient",
        "ClientConfig",
        "ConfigurationError",
        "StoneXError",
        "StoneXAPIError",
        "AuthenticationError",
        "RateLimitError",
        "OrderRejectedError",
        "ResponseParseError",
        "TransportError",
        "__version__",
    }

    for name in expected_exports:
        assert hasattr(stonepy, name), name

    assert set(stonepy.__all__) == expected_exports

    assert inspect.isclass(stonepy.StoneXClient)
    assert inspect.isclass(stonepy.AsyncStoneXClient)
    assert inspect.isclass(stonepy.ClientConfig)

    assert issubclass(stonepy.StoneXAPIError, stonepy.StoneXError)
    assert issubclass(stonepy.AuthenticationError, stonepy.StoneXError)
    assert issubclass(stonepy.RateLimitError, stonepy.StoneXError)
    assert issubclass(stonepy.OrderRejectedError, stonepy.StoneXError)
    assert issubclass(stonepy.ResponseParseError, stonepy.StoneXError)
    assert issubclass(stonepy.TransportError, stonepy.StoneXError)


def test_public_errors_module_reexports_exception_hierarchy() -> None:
    from stonepy import errors

    assert errors.StoneXError.__name__ == "StoneXError"
    assert errors.TransportError.__name__ == "TransportError"
    assert "ResponseParseError" in errors.__all__
