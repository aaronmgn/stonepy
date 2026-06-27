# Pagination

Paginated API methods return the page DTO documented by StoneX. For example,
`client.market.list_market_search_paginated(...)` accepts `page`, `page_size`, and `order_by`
keyword arguments and returns a `ListMarketSearchPaginatedResponseDTO`:

```python
page = client.market.list_market_search_paginated(
    "gold",
    search_by_market_code=False,
    search_by_market_name=True,
    spread_product_type=True,
    cfd_product_type=True,
    binary_product_type=False,
    ascending_order=True,
    include_options=False,
    client_account_id=12345,
    page=0,
    page_size=100,
)
print(page.total_number_of_results)
```

Request the next page by incrementing `page`. The response DTO exposes the total result count so
you can decide when to stop.
