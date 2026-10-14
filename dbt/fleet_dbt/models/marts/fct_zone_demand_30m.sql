with base as (
    select
        date_trunc('hour', pickup_datetime)
          + floor(extract(minute from pickup_datetime) / 30) * interval '30 minutes' as window_start,
        pickup_zone_id as zone_id
    from {{ ref('stg_trips') }}
)
select
    window_start,
    zone_id,
    count(*) as demand
from base
group by 1, 2
