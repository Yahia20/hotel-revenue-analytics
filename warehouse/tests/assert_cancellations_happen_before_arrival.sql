-- A cancellation recorded after the arrival date would mean the dates are mis-parsed.
select booking_id, arrival_date, cancellation_date
from {{ ref('stg_bookings') }}
where reservation_status = 'Canceled' and cancellation_date > arrival_date
