-- One row per booked night. A 3-night stay is 3 rows. Zero-night (day-use) bookings have no rows.

select
    b.booking_id,
    b.hotel,
    stay.night::date      as stay_date,
    b.is_canceled,
    b.adr_eur
from {{ ref('fct_bookings') }} as b,
     unnest(generate_series(b.arrival_date, b.arrival_date + (b.nights - 1), interval 1 day)) as stay(night)
where b.nights > 0
