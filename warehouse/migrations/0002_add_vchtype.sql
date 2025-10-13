alter table fact_invoice
  add column if not exists vchtype text;

create index if not exists idx_fact_invoice_vchtype on fact_invoice(vchtype);

