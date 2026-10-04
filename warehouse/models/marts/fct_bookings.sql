-- Bookings used for analysis: everything in staging except rows with an impossible price or no guests.

select
    booking_id,
    hotel,
    booking_date,
    arrival_date,
    date_trunc('month', arrival_date)::date                    as arrival_month,
    dayname(arrival_date)                                      as arrival_weekday,
    lead_time_days,
    case
        when lead_time_days <= 7   then '0-7 days'
        when lead_time_days <= 30  then '8-30 days'
        when lead_time_days <= 90  then '31-90 days'
        when lead_time_days <= 180 then '91-180 days'
        when lead_time_days <= 365 then '181-365 days'
        else '365+ days'
    end                                                        as lead_time_band,
    nights,
    weekend_nights,
    week_nights,
    adults,
    children,
    babies,
    guests,
    meal_plan,
    country_code,
    market_segment,
    distribution_channel,
    customer_type,
    deposit_type,
    is_repeated_guest,
    previous_cancellations,
    previous_bookings_not_canceled,
    reserved_room_type,
    assigned_room_type,
    booking_changes,
    agent_id,
    company_id,
    days_in_waiting_list,
    parking_spaces,
    special_requests,
    adr_eur,
    room_revenue_eur,
    is_canceled,
    is_no_show,
    reservation_status,
    cancellation_date,
    cancelled_days_before_arrival,
    case when is_canceled then 0 else room_revenue_eur end     as realized_revenue_eur,
    case when is_canceled then room_revenue_eur else 0 end     as cancelled_revenue_eur,
    dq_identical_to_another_row
from {{ ref('stg_bookings') }}
where not dq_negative_adr
  and not dq_adr_outlier
  and not dq_zero_guests
