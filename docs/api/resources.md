# Resource groups

Each property on a client returns a typed resource group. Generated methods provide one method per
CIAPI endpoint, plus the documented `place_order` alias for the generated `order` method. The
synchronous classes are documented below; every method has an `async` twin on the matching
`Async*Resource` class (for example `AsyncSessionResource.log_on`).

::: stonepy.resources.session.SessionResource

::: stonepy.resources.order.OrderResource

::: stonepy.resources.order_including_closed.OrderIncludingClosedResource

::: stonepy.resources.market.MarketResource

::: stonepy.resources.spread.SpreadResource

::: stonepy.resources.cfd.CfdResource

::: stonepy.resources.margin.MarginResource

::: stonepy.resources.fixedmargin.FixedmarginResource

::: stonepy.resources.price_alert.PriceAlertResource

::: stonepy.resources.watchlist.WatchlistResource

::: stonepy.resources.news.NewsResource

::: stonepy.resources.message.MessageResource

::: stonepy.resources.preference.PreferenceResource

::: stonepy.resources.clientpreference.ClientpreferenceResource

::: stonepy.resources.client_preference.ClientPreferenceResource

::: stonepy.resources.clientapplication.ClientapplicationResource

::: stonepy.resources.user_account.UserAccountResource

::: stonepy.resources.pm.PmResource

::: stonepy.resources.tradingadvisor.TradingadvisorResource


`preference.delete_user_preference`, `preference.save_user_preference`, and `price_alert.save_pa`
return `stonepy._core.models.UnspecifiedResponse` because their catalog contracts document no
response body. Empty bodies and JSON `null` produce an empty model; unexpected object fields
are retained in `model_extra`.
