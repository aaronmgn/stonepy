from datetime import UTC, datetime, timedelta, tzinfo
from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from stonepy._core import codec

BAD_WCF_VALUES: tuple[object, ...] = (
    1.5,
    {},
    b"/Date(0)/",
    "/Date(-62135596800001)/",
)


class DateModel(BaseModel):
    value: codec.StoneXDateTime


class OptionalDateModel(BaseModel):
    value: codec.StoneXDateTime | None


class UnknownOffsetTZ(tzinfo):
    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return None

    def dst(self, dt: datetime | None) -> timedelta | None:
        return None

    def tzname(self, dt: datetime | None) -> str | None:
        return None


@pytest.mark.parametrize(
    ("raw", "expected_ms"),
    [
        ("/Date(1289231327280)/", 1289231327280),
        (r"\/Date(1289231327280)\/", 1289231327280),
        ("/Date(1289231327280+0200)/", 1289231327280),  # offset not parsed as ms
        ("/Date(0)/", 0),
        ("/Date(-1000)/", -1000),
    ],
)
def test_parse_wcf_date(raw: str, expected_ms: int) -> None:
    dt = codec.parse_wcf_date(raw)
    assert dt is not None
    assert dt.tzinfo is UTC
    assert int(dt.timestamp() * 1000) == expected_ms


def test_parse_minvalue_is_none() -> None:
    assert codec.parse_wcf_date("/Date(-62135596800000)/") is None


def test_parse_lower_bound_adjacent_is_exact() -> None:
    assert codec.parse_wcf_date("/Date(-62135596799999)/") == datetime(
        1, 1, 1, 0, 0, 0, 1000, tzinfo=UTC
    )


def test_parse_none_passthrough() -> None:
    assert codec.parse_wcf_date(None) is None


@pytest.mark.parametrize("raw", [False, True])
def test_parse_bool_rejected(raw: bool) -> None:
    with pytest.raises(ValueError):
        codec.parse_wcf_date(raw)


@pytest.mark.parametrize("raw", BAD_WCF_VALUES)
def test_parse_malformed_values_raise_value_error(raw: object) -> None:
    with pytest.raises(ValueError):
        codec.parse_wcf_date(raw)


def test_parse_rejects_embedded_wcf_fragment() -> None:
    with pytest.raises(ValueError):
        codec.parse_wcf_date("xxx/Date(0)/yyy")


def test_format_roundtrip() -> None:
    dt = datetime(2010, 11, 8, 15, 48, 47, 280000, tzinfo=UTC)
    assert codec.format_wcf_date(dt) == "/Date(1289231327280)/"
    assert codec.parse_wcf_date(codec.format_wcf_date(dt)) == dt


def test_format_naive_rejected() -> None:
    with pytest.raises(ValueError):
        codec.format_wcf_date(datetime(2020, 1, 1))  # noqa: DTZ001


def test_format_unknown_offset_rejected() -> None:
    with pytest.raises(ValueError):
        codec.format_wcf_date(datetime(2020, 1, 1, tzinfo=UnknownOffsetTZ()))


def test_stonex_datetime_optional_accepts_minvalue_sentinel() -> None:
    model = OptionalDateModel.model_validate({"value": "/Date(-62135596800000)/"})
    assert model.value is None


def test_stonex_datetime_model_validate_and_dump() -> None:
    dt = datetime(2010, 11, 8, 15, 48, 47, 280000, tzinfo=UTC)
    model = DateModel.model_validate({"value": "/Date(1289231327280)/"})

    assert model.value == dt
    assert model.model_dump() == {"value": "/Date(1289231327280)/"}


def test_stonex_datetime_rejects_bool() -> None:
    with pytest.raises(ValidationError):
        DateModel.model_validate({"value": True})


@pytest.mark.parametrize("raw", BAD_WCF_VALUES)
def test_stonex_datetime_rejects_malformed_values(raw: object) -> None:
    with pytest.raises(ValidationError):
        DateModel.model_validate({"value": raw})


def test_stonex_datetime_rejects_naive_datetime() -> None:
    with pytest.raises(ValidationError):
        DateModel.model_validate({"value": datetime(2020, 1, 1)})


def test_stonex_datetime_rejects_unknown_offset_datetime() -> None:
    with pytest.raises(ValidationError):
        DateModel.model_validate({"value": datetime(2020, 1, 1, tzinfo=UnknownOffsetTZ())})


def test_decimal_json_roundtrip_is_number_not_string() -> None:
    body = {"Quantity": Decimal("1.30")}
    text = codec.dumps(body)
    assert '"1.30"' not in text and "1.30" in text
    assert codec.loads(text)["Quantity"] == Decimal("1.30")
    assert isinstance(codec.loads(text)["Quantity"], Decimal)


@pytest.mark.parametrize("text", ['{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'])
def test_loads_rejects_non_finite_constants(text: str) -> None:
    with pytest.raises(ValueError):
        codec.loads(text)


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_dumps_rejects_non_finite_decimal(value: Decimal) -> None:
    with pytest.raises(ValueError):
        codec.dumps({"x": value})


@pytest.mark.parametrize("key", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_dumps_rejects_non_finite_decimal_key(key: Decimal) -> None:
    with pytest.raises(ValueError):
        codec.dumps({key: "x"})


def test_dumps_rejects_nested_non_finite_decimal_key() -> None:
    with pytest.raises(ValueError):
        codec.dumps({"outer": {Decimal("NaN"): "x"}})
