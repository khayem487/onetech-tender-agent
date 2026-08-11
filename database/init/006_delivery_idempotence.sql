BEGIN;

-- Early local test runs used the digest hash as part of their uniqueness key.
-- Keep only the most recent delivery per execution/channel/recipient before
-- installing the stronger invariant below.  A scheduled execution must never
-- notify the same recipient twice merely because a rendered digest changes.
WITH ranked AS (
    SELECT
        id,
        row_number() OVER (
            PARTITION BY execution_id, canal, destinataire_hash
            ORDER BY
                CASE WHEN statut = 'envoyee' THEN 0 ELSE 1 END,
                envoyee_le DESC NULLS LAST,
                mise_a_jour_le DESC,
                id DESC
        ) AS rang
    FROM diffusions_digest
)
DELETE FROM diffusions_digest d
USING ranked r
WHERE d.id = r.id
  AND r.rang > 1;

DO $$
DECLARE
    old_constraint TEXT;
BEGIN
    SELECT conname
      INTO old_constraint
      FROM pg_constraint
     WHERE conrelid = 'public.diffusions_digest'::regclass
       AND contype = 'u'
       AND pg_get_constraintdef(oid) = 'UNIQUE (canal, destinataire_hash, digest_sha256)'
     LIMIT 1;

    IF old_constraint IS NOT NULL THEN
        EXECUTE format(
            'ALTER TABLE public.diffusions_digest DROP CONSTRAINT %I',
            old_constraint
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conrelid = 'public.diffusions_digest'::regclass
           AND conname = 'uq_diffusions_digest_execution_recipient'
    ) THEN
        ALTER TABLE public.diffusions_digest
            ADD CONSTRAINT uq_diffusions_digest_execution_recipient
            UNIQUE (execution_id, canal, destinataire_hash);
    END IF;
END;
$$;

COMMENT ON CONSTRAINT uq_diffusions_digest_execution_recipient
    ON diffusions_digest IS
    'Une execution ne diffuse qu''une fois par canal et destinataire.';

COMMIT;
