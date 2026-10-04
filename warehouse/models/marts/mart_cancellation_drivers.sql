-- Cancellation rate and cancelled revenue sliced by every attribute known when the booking is made.
-- Long format (dimension, value) so the dashboard can chart any slice from one table.

{% set dims = {
    'hotel': 'hotel',
    'market_segment': 'market_segment',
    'distribution_channel': 'distribution_channel',
    'deposit_type': 'deposit_type',
    'customer_type': 'customer_type',
    'lead_time_band': 'lead_time_band',
    'repeat_guest': "case when is_repeated_guest then 'Repeat guest' else 'First stay' end",
    'previous_cancellations': "case when previous_cancellations = 0 then 'None' else '1 or more' end",
    'special_requests': "case when special_requests = 0 then 'None' else '1 or more' end",
    'arrival_month': "strftime(arrival_date, '%m-%b')",
} %}

{% for name, expr in dims.items() %}
select
    '{{ name }}'                         as dimension,
    {{ expr }}                           as value,
    count(*)                             as bookings,
    count(*) filter (where is_canceled)  as cancellations,
    avg(is_canceled::int)                as cancellation_rate,
    sum(cancelled_revenue_eur)           as cancelled_revenue_eur
from {{ ref('fct_bookings') }}
group by 1, 2
{% if not loop.last %}union all{% endif %}
{% endfor %}
