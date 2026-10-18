-- POPIA retention enforcement (s14)
-- Engineering guidance, not legal advice.
--
-- s14(1): keep personal information no longer than needed for the purpose,
--         unless law, contract, consent or a lawful related function requires it.
-- s14(4): destroy, delete or de-identify as soon as reasonably practicable after that.
-- s14(5): delete in a way that prevents reconstruction in an intelligible form.
-- s14(6): restrict rather than delete in some cases (accuracy contested, proof needed).
--
-- Edit the rules below to match privacy.data_inventory. Each rule logs a row
-- to privacy.retention_runs so you have evidence the job ran.
-- Confirm sector retention periods with your attorney or auditor before you
-- hard-code them (references/01-popia-legal-map.md, section 12).

create or replace function privacy.enforce_retention()
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  n integer;
begin
  -- Example rule 1: unconverted leads, 12 months after creation.
  -- delete from public.leads
  --  where converted = false
  --    and created_at < now() - interval '12 months';
  -- get diagnostics n = row_count;
  -- insert into privacy.retention_runs(rule, rows_affected) values ('leads_unconverted_12m', n);

  -- Example rule 2: closed accounts. De-identify 90 days after closure.
  -- Keep invoice totals for tax (commonly 5 years under the Tax Administration Act: VERIFY for your sector).
  -- update public.profiles
  --    set full_name = null, email = null, phone = null, id_number_enc = null, deidentified_at = now()
  --  where closed_at < now() - interval '90 days'
  --    and deidentified_at is null;
  -- get diagnostics n = row_count;
  -- insert into privacy.retention_runs(rule, rows_affected) values ('profiles_closed_90d', n);

  -- Example rule 3: support tickets, 24 months after last activity.
  -- delete from public.support_tickets where last_activity_at < now() - interval '24 months';
  -- get diagnostics n = row_count;
  -- insert into privacy.retention_runs(rule, rows_affected) values ('support_tickets_24m', n);

  -- Example rule 4: completed DSAR requests. Keep as evidence of handling, then delete.
  -- VERIFY the period with your Information Officer. 3 years is a placeholder.
  -- (dsar_requests is not append-only, so this delete is allowed.)
  -- delete from privacy.dsar_requests
  --  where status in ('completed','rejected')
  --    and completed_at < now() - interval '3 years';
  -- get diagnostics n = row_count;
  -- insert into privacy.retention_runs(rule, rows_affected) values ('dsar_requests_3y', n);

  -- Storage objects (uploads such as CVs or ID copies) need deleting through the
  -- Storage API so the file is removed, not only the metadata row. Do that from
  -- an edge function on a schedule, not from SQL.

  -- Summary row: proves the job ran even when no rule matched anything.
  insert into privacy.retention_runs(rule, rows_affected, details)
  values ('enforce_retention', null, jsonb_build_object('note', 'run completed'));
end;
$$;

revoke all on function privacy.enforce_retention() from public, anon, authenticated;
grant execute on function privacy.enforce_retention() to service_role;

-- Nightly schedule at 02:15 UTC, only if pg_cron is installed.
-- Enable it in Dashboard > Database > Extensions > pg_cron, then re-run this block.
do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    -- Replace an existing job of the same name so this migration is re-runnable.
    perform cron.unschedule(jobid) from cron.job where jobname = 'popia-retention';
    perform cron.schedule('popia-retention', '15 2 * * *', 'select privacy.enforce_retention()');
  else
    raise notice 'pg_cron is not installed. privacy.enforce_retention() is not scheduled. Enable pg_cron and re-run this block.';
  end if;
end;
$$;
