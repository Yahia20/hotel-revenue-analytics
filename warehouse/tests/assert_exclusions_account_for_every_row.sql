-- Every staging row is either in fct_bookings or excluded by exactly the documented rules.
with counts as (
    select
        (select count(*) from {{ ref('stg_bookings') }}) as staged,
        (select count(*) from {{ ref('fct_bookings') }}) as kept,
        (select count(*) from {{ ref('stg_bookings') }}
          where dq_negative_adr or dq_adr_outlier or dq_zero_guests) as excluded
)
select * from counts where staged <> kept + excluded
