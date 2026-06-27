def test_version_exposed() -> None:
    import stonepy

    assert isinstance(stonepy.__version__, str)
    assert stonepy.__version__
