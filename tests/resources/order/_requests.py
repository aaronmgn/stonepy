"""Validated order requests shared by synchronous and asynchronous wire tests."""

from decimal import Decimal

from stonepy.models import ExecutionVenueRequestDTO, NewTradeOrderRequestDTO

MALFORMED_ACK_BODIES = [
    b"",
    b"{}",
    b"null",
    b'{"Status":null}',
    b'{"Status":true}',
    b'{"Status":1.5}',
    b'{"Status":[]}',
    b'{"Status":{}}',
    b'{"Status":"abc"}',
]


def valid_trade_request() -> NewTradeOrderRequestDTO:
    """Build a complete market trade with one attached IfDone stop."""
    return NewTradeOrderRequestDTO.model_validate(
        {
            "MarketId": 456,
            "Currency": "USD",
            "AutoRollover": False,
            "Direction": "Buy",
            "Quantity": Decimal("1.23456789123456789"),
            "QuoteId": 0,
            "PositionMethodId": 1,
            "BidPrice": Decimal("123.456789123456789"),
            "OfferPrice": Decimal("123.456789123456799"),
            "AuditId": "tick-audit",
            "TradingAccountId": 123,
            "IfDone": [
                {
                    "Stop": {
                        "Guaranteed": False,
                        "TriggerPrice": Decimal("120.123456789123456789"),
                        "Applicability": "GTC",
                    }
                }
            ],
            "Close": [],
            "Reference": "StoneX API",
            "AllocationProfileId": 0,
            "OrderReference": "unit-trade",
            "Source": "unit-test",
            "PriceTolerance": 0,
        }
    )


def valid_execution_venue_request() -> ExecutionVenueRequestDTO:
    """Build a venue request with a parent trade and an attached stop request.

    This contract represents attachments through ParentOrderRequestToken, not an IfDone field.
    """
    return ExecutionVenueRequestDTO.model_validate(
        {
            "ClientAccountId": 789,
            "AppKey": "unit-key",
            "RequestId": "unit-request",
            "QuoteId": 0,
            "MarketId": 456,
            "OrderRequests": [
                {
                    "OrderRequestToken": "parent",
                    "OrderTypeId": 1,
                    "OrderDirectionId": 1,
                    "TradingAccountId": 123,
                    "MarketId": 456,
                    "Quantity": Decimal("1.23456789123456789"),
                    "Level": Decimal("123.456789123456799"),
                    "CurrencyId": 1,
                    "PositionMethodId": 1,
                    "Reference": "StoneX API",
                },
                {
                    "OrderRequestToken": "stop",
                    "ParentOrderRequestToken": "parent",
                    "OrderTypeId": 2,
                    "OrderDirectionId": 2,
                    "TradingAccountId": 123,
                    "MarketId": 456,
                    "Quantity": Decimal("1.23456789123456789"),
                    "Level": Decimal("120.123456789123456789"),
                    "Guaranteed": False,
                    "ExpiryTypeId": 1,
                },
            ],
            "RequestTypeId": 1,
            "TradingAccountId": 123,
            "UserName": "alice",
            "Simulation": True,
            "TransactionId": "unit-transaction",
            "Bid": Decimal("123.456789123456789"),
            "Ask": Decimal("123.456789123456799"),
            "AuditId": "tick-audit",
        }
    )
