-- Checked-out bookings should leave on arrival + nights. The source has a handful that do not
-- (early departures); warn instead of failing so a sudden jump still shows up in the run log.
{{ config(severity = 'warn') }}
select booking_id, arrival_date, nights, reservation_status_date
from {{ ref('stg_bookings') }}
where reservation_status = 'Check-Out'
  and reservation_status_date <> arrival_date + nights
