-- View: Billwise Outstanding Report
-- Purpose: Provides latest pending amounts for each ledger and bill
-- Shows only bills with pending amounts > 0 (outstanding receivables)

create or replace view view_billwise_outstanding as
select
    ledger,
    bill_name,
    bill_date,
    due_date,
    original_amount,
    adjusted_amount,
    pending_amount,
    billtype,
    is_advance,
    last_adjusted_date,
    last_seen_at,
    -- Calculate days overdue (negative means not yet due)
    case
        when due_date is not null
        then current_date - due_date
        else null
    end as days_overdue,
    -- Aging buckets
    case
        when due_date is null then 'No Due Date'
        when current_date <= due_date then 'Not Due'
        when current_date - due_date <= 30 then '0-30 Days'
        when current_date - due_date <= 60 then '31-60 Days'
        when current_date - due_date <= 90 then '61-90 Days'
        else '90+ Days'
    end as aging_bucket
from fact_bills_receivable
where pending_amount > 0  -- Only outstanding bills
order by ledger, bill_date;

-- Summary view: Outstanding by ledger
create or replace view view_ledger_outstanding_summary as
select
    ledger,
    count(*) as bill_count,
    sum(original_amount) as total_original,
    sum(adjusted_amount) as total_adjusted,
    sum(pending_amount) as total_pending,
    max(last_seen_at) as last_updated,
    -- Aging breakdown
    sum(case when due_date is null or current_date <= due_date then pending_amount else 0 end) as not_due,
    sum(case when current_date - due_date between 1 and 30 then pending_amount else 0 end) as overdue_0_30,
    sum(case when current_date - due_date between 31 and 60 then pending_amount else 0 end) as overdue_31_60,
    sum(case when current_date - due_date between 61 and 90 then pending_amount else 0 end) as overdue_61_90,
    sum(case when current_date - due_date > 90 then pending_amount else 0 end) as overdue_90_plus
from fact_bills_receivable
where pending_amount > 0
group by ledger
order by total_pending desc;

-- Comment on views
comment on view view_billwise_outstanding is 'Bill-wise outstanding receivables with aging analysis';
comment on view view_ledger_outstanding_summary is 'Ledger-wise summary of outstanding receivables with aging buckets';



