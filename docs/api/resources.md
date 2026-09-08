# Resource groups

Each property on a client returns a typed resource group. Generated methods provide one method per
CIAPI endpoint, plus the documented `place_order` alias for the generated `order` method and
`order.get_order_including_closed` for querying active and closed orders. The
synchronous classes are documented below; every method has an `async` twin on the matching
`Async*Resource` class (for example `AsyncSessionResource.log_on`).

## `session`

::: stonepy.resources.session.SessionResource

## `order`

::: stonepy.resources.order.OrderResource

## `order_including_closed` (deprecated)

Deprecated aliases: `client.order_including_closed.get_order_including_closed` emits
`DeprecationWarning`; use `client.order.get_order_including_closed`.

::: stonepy.resources.order_including_closed.OrderIncludingClosedResource

## `market`

::: stonepy.resources.market.MarketResource

## `spread`

::: stonepy.resources.spread.SpreadResource

## `cfd`

::: stonepy.resources.cfd.CfdResource

## `margin`

::: stonepy.resources.margin.MarginResource

## `fixed_margin`

Deprecated aliases: `fixedmargin` emits `DeprecationWarning`; use `client.fixed_margin`.

::: stonepy.resources.fixedmargin.FixedmarginResource

## `price_alert`

::: stonepy.resources.price_alert.PriceAlertResource

## `watchlist`

::: stonepy.resources.watchlist.WatchlistResource

## `news`

::: stonepy.resources.news.NewsResource

## `message`

::: stonepy.resources.message.MessageResource

## `preference`

::: stonepy.resources.preference.PreferenceResource

## `clientpreference`

::: stonepy.resources.clientpreference.ClientpreferenceResource

## `client_preference`

::: stonepy.resources.client_preference.ClientPreferenceResource

## `client_application`

Deprecated aliases: `clientapplication` emits `DeprecationWarning`; use `client.client_application`.

::: stonepy.resources.clientapplication.ClientapplicationResource

## `user_account`

::: stonepy.resources.user_account.UserAccountResource

## `pm`

::: stonepy.resources.pm.PmResource

## `trading_advisor`

Deprecated aliases: `tradingadvisor` emits `DeprecationWarning`; use `client.trading_advisor`.

::: stonepy.resources.tradingadvisor.TradingadvisorResource

## Unspecified responses

`preference.delete_user_preference`, `preference.save_user_preference`, and `price_alert.save_pa`
return `stonepy._core.models.UnspecifiedResponse` because their catalog contracts document no
response body. Empty bodies and JSON `null` produce an empty model; unexpected object fields
are retained in `model_extra`.
