-- Revenue summed night by night must equal revenue summed booking by booking (to the cent).
with by_booking as (
    select sum(realized_revenue_eur) as realized, sum(cancelled_revenue_eur) as cancelled
    from {{ ref('fct_bookings') }}
),
by_night as (
    select sum(realized_revenue_eur) as realized, sum(cancelled_revenue_eur) as cancelled
    from {{ ref('mart_daily_occupancy') }}
)
select *
from by_booking, by_night
where abs(by_booking.realized - by_night.realized) > 0.01
   or abs(by_booking.cancelled - by_night.cancelled) > 0.01
