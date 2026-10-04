-- Monthly KPIs per hotel, by arrival month.

select
    hotel,
    arrival_month,
    count(*)                                                   as bookings,
    count(*) filter (where is_canceled)                        as cancellations,
    count(*) filter (where is_no_show)                         as no_shows,
    avg(is_canceled::int)                                      as cancellation_rate,
    sum(nights) filter (where not is_canceled)                 as room_nights_sold,
    sum(realized_revenue_eur)                                  as realized_revenue_eur,
    sum(cancelled_revenue_eur)                                 as cancelled_revenue_eur,
    sum(realized_revenue_eur)
        / nullif(sum(nights) filter (where not is_canceled), 0) as realized_adr_eur
from {{ ref('fct_bookings') }}
group by hotel, arrival_month
