select
    cast(pickup_datetime as timestamp) as pickup_datetime,
    cast(dropoff_datetime as timestamp) as dropoff_datetime,
    cast("PULocationID" as integer) as pickup_zone_id,
    cast("DOLocationID" as integer) as dropoff_zone_id,
    cast(trip_distance as double precision) as trip_distance
from {{ source('raw', 'trips') }}
where pickup_datetime is not null
  and "PULocationID" > 0
  and "DOLocationID" > 0
