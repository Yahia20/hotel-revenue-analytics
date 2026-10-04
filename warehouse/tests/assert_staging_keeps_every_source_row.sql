-- Staging must not drop or duplicate rows. Returns a row (= failure) if the counts differ.
select src.n as source_rows, stg.n as staging_rows
from (select count(*) as n from {{ source('raw', 'hotel_bookings') }}) as src,
     (select count(*) as n from {{ ref('stg_bookings') }}) as stg
where src.n <> stg.n
