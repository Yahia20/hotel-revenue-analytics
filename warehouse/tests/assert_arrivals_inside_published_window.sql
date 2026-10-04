select booking_id, arrival_date
from {{ ref('stg_bookings') }}
where arrival_date not between '{{ var("first_arrival") }}'::date and '{{ var("last_arrival") }}'::date
