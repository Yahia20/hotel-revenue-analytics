-- One row per source booking, typed and renamed. Nothing is dropped here: rows that are unusable for
-- analysis get a data-quality flag, and fct_bookings decides what to keep.

with source as (

    select
        row_number() over () as booking_id,  -- source has no ID; file order is stable
        *
    from {{ source('raw', 'hotel_bookings') }}

),

typed as (

    select
        booking_id,
        hotel,
        is_canceled = 1                                                    as is_canceled,
        reservation_status = 'No-Show'                                     as is_no_show,
        lead_time::int                                                     as lead_time_days,
        make_date(
            arrival_date_year::int,
            month(strptime(arrival_date_month, '%B'))::int,
            arrival_date_day_of_month::int
        )                                                                  as arrival_date,
        stays_in_weekend_nights::int                                       as weekend_nights,
        stays_in_week_nights::int                                          as week_nights,
        adults::int                                                        as adults,
        coalesce(children, 0)::int                                         as children,
        babies::int                                                        as babies,
        -- the dataset documents 'Undefined' and 'SC' as the same thing: no meal package
        case when meal = 'Undefined' then 'SC' else meal end               as meal_plan,
        coalesce(country, 'UNK')                                           as country_code,
        market_segment,
        distribution_channel,
        is_repeated_guest = 1                                              as is_repeated_guest,
        previous_cancellations::int                                        as previous_cancellations,
        previous_bookings_not_canceled::int                                as previous_bookings_not_canceled,
        reserved_room_type,
        assigned_room_type,
        booking_changes::int                                               as booking_changes,
        deposit_type,
        agent::int                                                         as agent_id,
        company::int                                                       as company_id,
        days_in_waiting_list::int                                          as days_in_waiting_list,
        customer_type,
        adr::double                                                        as adr_eur,
        required_car_parking_spaces::int                                   as parking_spaces,
        total_of_special_requests::int                                     as special_requests,
        reservation_status,
        reservation_status_date
    from source

)

select
    *,
    arrival_date - lead_time_days                                          as booking_date,
    weekend_nights + week_nights                                           as nights,
    adults + children + babies                                             as guests,
    adr_eur * (weekend_nights + week_nights)                               as room_revenue_eur,
    case when is_canceled then reservation_status_date end                 as cancellation_date,
    case when is_canceled then arrival_date - reservation_status_date end  as cancelled_days_before_arrival,

    adr_eur < 0                                                            as dq_negative_adr,
    adr_eur > {{ var('adr_ceiling') }}                                     as dq_adr_outlier,
    adults + children + babies = 0                                         as dq_zero_guests,
    count(*) over (
        partition by hotel, is_canceled, lead_time_days, arrival_date, weekend_nights, week_nights,
                     adults, children, babies, meal_plan, country_code, market_segment, distribution_channel,
                     is_repeated_guest, previous_cancellations, previous_bookings_not_canceled,
                     reserved_room_type, assigned_room_type, booking_changes, deposit_type, agent_id,
                     company_id, days_in_waiting_list, customer_type, adr_eur, parking_spaces,
                     special_requests, reservation_status, reservation_status_date
    ) > 1                                                                  as dq_identical_to_another_row
from typed
