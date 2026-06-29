from __future__ import annotations

import subprocess
from pathlib import Path

from stonepy._generator.__main__ import main
from stonepy._generator.catalog import Catalog, EndpointRecord, TypeRecord
from stonepy._generator.scaffold import scaffold


def _endpoint(
    *,
    name: str = "ChangePassword",
    logical_name: str | None = "ChangePassword",
    method: str | None = "POST",
    target: str | None = "session",
    path: str = "/session/changePassword",
    parameters: list[dict[str, object]] | None = None,
    request_type: str | None = "ApiChangePasswordRequestDTO",
    response_type: str | None = "ApiChangePasswordResponseDTO",
    description: str | None = "Change the password for the current session.",
) -> EndpointRecord:
    return EndpointRecord(
        name=name,
        logical_name=logical_name,
        version="v1",
        description=description,
        method=method,
        target=target,
        uri_template=path,
        path=path,
        content_type="application/json",
        envelope="JSON",
        parameters=(
            parameters
            if parameters is not None
            else [
                {
                    "name": "apiChangePasswordRequest",
                    "type": "ApiChangePasswordRequestDTO",
                    "ref": "ApiChangePasswordRequestDTO",
                    "in": "body",
                }
            ]
        ),
        request_type=request_type,
        response_type=response_type,
        source_url=None,
        source_file=None,
        last_updated=None,
        raw={"name": name},
    )


def _datatype(name: str) -> TypeRecord:
    return TypeRecord(
        name=name,
        catalog_name=name,
        version="v1",
        description=None,
        properties=[],
        source_url=None,
        source_file=None,
        last_updated=None,
        raw={"name": name, "properties": []},
    )


def _catalog(
    endpoints: list[EndpointRecord] | None = None,
    datatypes: list[TypeRecord] | None = None,
    unresolved: set[str] | None = None,
) -> Catalog:
    return Catalog(
        endpoints=endpoints or [_endpoint()],
        datatypes=(
            datatypes
            if datatypes is not None
            else [
                _datatype("ApiChangePasswordRequestDTO"),
                _datatype("ApiChangePasswordResponseDTO"),
            ]
        ),
        lookups={},
        unresolved=unresolved or set(),
    )


def test_scaffold_writes_resource_mixin_and_test_stub(tmp_path: Path) -> None:
    package_root = tmp_path / "stonepy"
    project_root = tmp_path / "project"

    scaffold(
        _catalog(),
        "session",
        "ChangePassword",
        package_dir=package_root,
        project_root=project_root,
    )

    resource = package_root / "resources" / "session" / "change_password.py"
    test_file = project_root / "tests" / "resources" / "session" / "test_change_password.py"
    resource_text = resource.read_text(encoding="utf-8")
    test_text = test_file.read_text(encoding="utf-8")

    assert "class _ChangePasswordMixin(BaseResource):" in resource_text
    assert "async def change_password(" in resource_text
    assert "request: ApiChangePasswordRequestDTO" in resource_text
    assert ") -> ApiChangePasswordResponseDTO:" in resource_text
    assert "return await _ep.achange_password(self._ctx, request)" in resource_text
    assert "def test_change_password_returns_response() -> None:" in test_text
    assert 'respx.post("https://api.example/session/changePassword")' in test_text
    assert "client.session.change_password(" in test_text


def test_scaffold_drops_dangling_http_service_docstring_fragment(tmp_path: Path) -> None:
    package_root = tmp_path / "stonepy"
    project_root = tmp_path / "project"
    endpoint = _endpoint(
        name="GetOpenPosition",
        logical_name="GetOpenPosition",
        target="order",
        path="/order/{OrderId}/openposition",
        parameters=[{"name": "OrderId", "type": "string", "ref": None, "in": "path"}],
        request_type=None,
        response_type="GetOpenPositionResponseDTOv2",
        description=(
            "Queries for a trade. For a more comprehensive order response, see the HTTP service ."
        ),
    )

    scaffold(
        _catalog(
            endpoints=[endpoint],
            datatypes=[_datatype("GetOpenPositionResponseDTOv2")],
        ),
        "order",
        "GetOpenPosition",
        package_dir=package_root,
        project_root=project_root,
    )

    resource_text = (package_root / "resources" / "order" / "get_open_position.py").read_text(
        encoding="utf-8"
    )

    assert "HTTP service ." not in resource_text
    assert "For a more comprehensive order response" not in resource_text
    assert "Queries for a trade." in resource_text


def test_cli_scaffold_writes_files_from_catalog_root(tmp_path: Path) -> None:
    docs_root = tmp_path / "Docs"
    catalog_root = docs_root / "catalog"
    catalog_root.mkdir(parents=True)
    (catalog_root / "endpoints.json").write_text(
        '[{"name":"ChangePassword","logical_name":"ChangePassword","version":"v1",'
        '"description":"Change the password for the current session.","method":"POST",'
        '"target":"session","uri_template":"/session/changePassword",'
        '"path":"/session/changePassword","content_type":"application/json",'
        '"envelope":"JSON","parameters":[{"name":"apiChangePasswordRequest",'
        '"type":"ApiChangePasswordRequestDTO","ref":"ApiChangePasswordRequestDTO",'
        '"in":"body"}],"request_type":"ApiChangePasswordRequestDTO",'
        '"response_type":"ApiChangePasswordResponseDTO"}]',
        encoding="utf-8",
    )
    (catalog_root / "data-types.json").write_text(
        '[{"name":"ApiChangePasswordRequestDTO","properties":[]},'
        '{"name":"ApiChangePasswordResponseDTO","properties":[]}]',
        encoding="utf-8",
    )
    (catalog_root / "lookup-codes.json").write_text("{}", encoding="utf-8")
    package_root = tmp_path / "stonepy"
    project_root = tmp_path / "project"

    assert (
        main(
            [
                "scaffold",
                "session",
                "ChangePassword",
                "--catalog-root",
                str(docs_root),
                "--package-dir",
                str(package_root),
                "--project-root",
                str(project_root),
                "--allow-unfrozen-catalog",
            ]
        )
        == 0
    )

    assert (package_root / "resources" / "session" / "change_password.py").exists()
    assert (project_root / "tests" / "resources" / "session" / "test_change_password.py").exists()


def test_scaffold_imports_core_response_models(tmp_path: Path) -> None:
    catalog = _catalog(
        endpoints=[
            # Synthetic endpoint name (not the real DeletePA, which the generator maps to a scalar
            # bool response): this exercises the generic response_type=None -> ResponseModel path.
            _endpoint(
                name="DeleteThing",
                logical_name="DeleteThing",
                target="thing",
                path="/thing/delete",
                parameters=[],
                request_type=None,
                response_type=None,
            ),
            _endpoint(
                name="GetNewsHeadlines",
                logical_name="GetNewsHeadlines",
                method="GET",
                target="news",
                path="/news/newsheadlines",
                parameters=[],
                request_type=None,
                response_type="NewsHeadlinesResponseDTO",
            ),
        ],
        datatypes=[],
    )
    package_root = tmp_path / "stonepy"
    project_root = tmp_path / "project"

    scaffold(catalog, "thing", "DeleteThing", package_dir=package_root, project_root=project_root)
    scaffold(
        catalog, "news", "GetNewsHeadlines", package_dir=package_root, project_root=project_root
    )

    delete_text = (package_root / "resources" / "thing" / "delete_thing.py").read_text(
        encoding="utf-8"
    )
    news_text = (package_root / "resources" / "news" / "get_news_headlines.py").read_text(
        encoding="utf-8"
    )

    assert "from stonepy._core.models import ResponseModel" in delete_text
    assert ") -> ResponseModel:" in delete_text
    assert "from stonepy._endpoints.news import NewsHeadlinesResponseDTO" in news_text
    assert ") -> NewsHeadlinesResponseDTO:" in news_text


def test_scaffold_imports_decimal_defaults(tmp_path: Path) -> None:
    catalog = _catalog(
        endpoints=[
            _endpoint(
                name="FindPrices",
                logical_name="FindPrices",
                method="GET",
                target="market",
                path="/market/prices",
                parameters=[
                    {
                        "name": "minPrice",
                        "type": "decimal required false default 1.5",
                        "ref": None,
                        "in": "query",
                    }
                ],
                request_type=None,
                response_type="FindPricesResponseDTO",
            )
        ],
        datatypes=[_datatype("FindPricesResponseDTO")],
    )
    package_root = tmp_path / "stonepy"

    scaffold(catalog, "market", "FindPrices", package_dir=package_root, project_root=tmp_path)

    resource_text = (package_root / "resources" / "market" / "find_prices.py").read_text(
        encoding="utf-8"
    )

    assert "from decimal import Decimal" in resource_text
    assert 'min_price: Decimal | None = Decimal("1.5")' in resource_text


def test_scaffold_long_description_resource_is_ruff_clean(tmp_path: Path) -> None:
    package_root = tmp_path / "stonepy"
    project_root = tmp_path / "project"
    catalog = _catalog(
        endpoints=[
            _endpoint(
                description=(
                    "This endpoint description is intentionally long enough to exceed the "
                    "project line length limit when emitted as a one-line docstring in a "
                    "generated resource scaffold."
                )
            )
        ]
    )

    scaffold(
        catalog,
        "session",
        "ChangePassword",
        package_dir=package_root,
        project_root=project_root,
    )

    result = subprocess.run(
        [
            "uv",
            "run",
            "ruff",
            "check",
            str(package_root / "resources" / "session" / "change_password.py"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_scaffold_generated_test_stub_is_ruff_clean(tmp_path: Path) -> None:
    package_root = tmp_path / "stonepy"
    project_root = tmp_path / "project"
    scaffold(
        _catalog(),
        "session",
        "ChangePassword",
        package_dir=package_root,
        project_root=project_root,
    )

    result = subprocess.run(
        [
            "uv",
            "run",
            "ruff",
            "check",
            str(project_root / "tests" / "resources" / "session" / "test_change_password.py"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_scaffold_samples_list_arguments_as_empty_lists(tmp_path: Path) -> None:
    catalog = _catalog(
        endpoints=[
            _endpoint(
                name="DeleteUserPreference",
                logical_name="DeleteUserPreference",
                target="preference",
                path="/preference/delete",
                parameters=[
                    {
                        "name": "Preferences",
                        "type": "string[]",
                        "ref": None,
                        "in": "body",
                    }
                ],
                request_type=None,
                response_type=None,
            )
        ],
        datatypes=[],
    )
    project_root = tmp_path / "project"

    scaffold(
        catalog,
        "preference",
        "DeleteUserPreference",
        package_dir=tmp_path,
        project_root=project_root,
    )

    test_text = (
        project_root / "tests" / "resources" / "preference" / "test_delete_user_preference.py"
    ).read_text(encoding="utf-8")

    # Empty-list samples carry an explicit annotation so the stub passes mypy --strict.
    assert "preferences: list[str] = []" in test_text


def test_scaffold_samples_model_list_arguments_as_empty_lists_and_keeps_stub_ruff_clean(
    tmp_path: Path,
) -> None:
    catalog = _catalog(
        endpoints=[
            _endpoint(
                name="SubmitParties",
                logical_name="SubmitParties",
                target="party",
                path="/party/submit",
                parameters=[
                    {
                        "name": "Parties",
                        "type": "LegalPartyDTO[]",
                        "ref": "LegalPartyDTO",
                        "in": "body",
                    }
                ],
                request_type=None,
                response_type=None,
            )
        ],
        datatypes=[_datatype("LegalPartyDTO")],
    )
    project_root = tmp_path / "project"

    scaffold(catalog, "party", "SubmitParties", package_dir=tmp_path, project_root=project_root)

    test_file = project_root / "tests" / "resources" / "party" / "test_submit_parties.py"
    test_text = test_file.read_text(encoding="utf-8")
    result = subprocess.run(
        ["uv", "run", "ruff", "check", str(test_file)],
        check=False,
        capture_output=True,
        text=True,
    )

    # The annotated empty list imports its element model and stays both ruff- and mypy-clean.
    assert "parties: list[LegalPartyDTO] = []" in test_text
    assert "from stonepy.models import LegalPartyDTO" in test_text
    assert result.returncode == 0, result.stdout + result.stderr


def test_scaffold_samples_optional_model_list_arguments_as_empty_lists(
    tmp_path: Path,
) -> None:
    catalog = _catalog(
        endpoints=[
            _endpoint(
                name="SearchParties",
                logical_name="SearchParties",
                method="GET",
                target="party",
                path="/party/search",
                parameters=[
                    {
                        "name": "Parties",
                        "type": "LegalPartyDTO[] required false",
                        "ref": "LegalPartyDTO",
                        "in": "query",
                    }
                ],
                request_type=None,
                response_type=None,
            )
        ],
        datatypes=[_datatype("LegalPartyDTO")],
    )
    project_root = tmp_path / "project"

    scaffold(catalog, "party", "SearchParties", package_dir=tmp_path, project_root=project_root)

    test_file = project_root / "tests" / "resources" / "party" / "test_search_parties.py"
    test_text = test_file.read_text(encoding="utf-8")
    result = subprocess.run(
        ["uv", "run", "ruff", "check", str(test_file)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert "parties: list[LegalPartyDTO] | None = []" in test_text
    assert "from stonepy.models import LegalPartyDTO" in test_text
    assert result.returncode == 0, result.stdout + result.stderr


def test_scaffold_refuses_to_overwrite_existing_files(tmp_path: Path) -> None:
    package_root = tmp_path / "stonepy"
    project_root = tmp_path / "project"
    resource = package_root / "resources" / "session" / "change_password.py"
    resource.parent.mkdir(parents=True)
    resource.write_text("# hand authored\n", encoding="utf-8")

    try:
        scaffold(
            _catalog(),
            "session",
            "ChangePassword",
            package_dir=package_root,
            project_root=project_root,
        )
    except FileExistsError as exc:
        assert str(resource) in str(exc)
    else:
        raise AssertionError("scaffold should refuse to overwrite existing resource")

    assert resource.read_text(encoding="utf-8") == "# hand authored\n"


def test_scaffold_force_overwrites_existing_files(tmp_path: Path) -> None:
    package_root = tmp_path / "stonepy"
    project_root = tmp_path / "project"
    resource = package_root / "resources" / "session" / "change_password.py"
    resource.parent.mkdir(parents=True)
    resource.write_text("# hand authored\n", encoding="utf-8")

    scaffold(
        _catalog(),
        "session",
        "ChangePassword",
        package_dir=package_root,
        project_root=project_root,
        force=True,
    )

    assert "class _ChangePasswordMixin(BaseResource):" in resource.read_text(encoding="utf-8")
