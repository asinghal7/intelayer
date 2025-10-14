-- Create pincode dimension table
create table if not exists dim_pincode (
  pincode  text primary key,
  city     text,
  state    text,
  lat      numeric,   -- centroid latitude
  lon      numeric    -- centroid longitude
);

-- Create index on state for faster lookups
create index if not exists idx_dim_pincode_state on dim_pincode(state);

