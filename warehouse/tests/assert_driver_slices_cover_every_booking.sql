-- Each dimension in the drivers mart must partition all bookings: no booking lost or counted twice.
select d.dimension, d.bookings, f.bookings as expected
from (select dimension, sum(bookings) as bookings from {{ ref('mart_cancellation_drivers') }} group by 1) as d,
     (select count(*) as bookings from {{ ref('fct_bookings') }}) as f
where d.bookings <> f.bookings
