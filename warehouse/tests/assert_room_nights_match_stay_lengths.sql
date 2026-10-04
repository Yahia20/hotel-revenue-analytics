-- Exploded nights must equal the sum of stay lengths.
select *
from (select sum(nights) as expected from {{ ref('fct_bookings') }}) as e,
     (select count(*) as actual from {{ ref('fct_room_nights') }}) as a
where e.expected <> a.actual
