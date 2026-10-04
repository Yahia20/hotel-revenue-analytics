-- Rooms sold and lost per hotel per night. This is what a revenue manager plans overbooking on.

select
    hotel,
    stay_date,
    count(*) filter (where not is_canceled)                    as rooms_sold,
    count(*) filter (where is_canceled)                        as rooms_cancelled,
    count(*)                                                   as rooms_booked,
    coalesce(sum(adr_eur) filter (where not is_canceled), 0)   as realized_revenue_eur,
    coalesce(sum(adr_eur) filter (where is_canceled), 0)       as cancelled_revenue_eur
from {{ ref('fct_room_nights') }}
group by hotel, stay_date
