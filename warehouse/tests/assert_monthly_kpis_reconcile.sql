-- Monthly KPIs must add back up to the booking-level totals.
select *
from (select count(*) as bookings, sum(is_canceled::int) as cancellations, sum(realized_revenue_eur) as revenue
        from {{ ref('fct_bookings') }}) as f,
     (select sum(bookings) as bookings, sum(cancellations) as cancellations, sum(realized_revenue_eur) as revenue
        from {{ ref('mart_monthly_kpis') }}) as m
where f.bookings <> m.bookings
   or f.cancellations <> m.cancellations
   or abs(f.revenue - m.revenue) > 0.01
