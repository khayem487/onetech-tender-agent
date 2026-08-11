BEGIN;

INSERT INTO executions_quotidiennes (
    cle_execution, declencheur, statut, parametres
) VALUES (
    'test:automation-smoke', 'test', 'en_cours', '{"test": true}'::jsonb
)
ON CONFLICT (cle_execution) DO UPDATE
SET parametres = EXCLUDED.parametres
RETURNING id \gset run_

INSERT INTO appels_offres (
    tender_id, source, organisme, titre, url_detail, donnees_brutes
) VALUES (
    'Tender-AUTOMATION-TEST', 'test', 'OneTech Test',
    'AO informatique de test', 'https://example.test/Tender-AUTOMATION-TEST',
    '{"test": true}'::jsonb
)
ON CONFLICT (tender_id) DO NOTHING;

INSERT INTO candidats_execution (
    execution_id, tender_id, contexte_sha256,
    score_pertinence, raisons, statut
) VALUES (
    :run_id, 'Tender-AUTOMATION-TEST', repeat('a', 64),
    10, '["informatique"]'::jsonb, 'a_analyser'
)
ON CONFLICT (execution_id, tender_id) DO UPDATE
SET contexte_sha256 = EXCLUDED.contexte_sha256;

INSERT INTO candidats_execution (
    execution_id, tender_id, contexte_sha256,
    score_pertinence, raisons, statut
) VALUES (
    :run_id, 'Tender-AUTOMATION-TEST', repeat('a', 64),
    10, '["informatique"]'::jsonb, 'a_analyser'
)
ON CONFLICT (execution_id, tender_id) DO UPDATE
SET contexte_sha256 = EXCLUDED.contexte_sha256;

DO $$
DECLARE
    run_count INTEGER;
    candidate_count INTEGER;
BEGIN
    SELECT count(*) INTO run_count
    FROM executions_quotidiennes
    WHERE cle_execution = 'test:automation-smoke';

    SELECT count(*) INTO candidate_count
    FROM candidats_execution c
    JOIN executions_quotidiennes e ON e.id = c.execution_id
    WHERE e.cle_execution = 'test:automation-smoke'
      AND c.tender_id = 'Tender-AUTOMATION-TEST';

    IF run_count <> 1 OR candidate_count <> 1 THEN
        RAISE EXCEPTION 'Automation idempotence failed: runs %, candidates %',
            run_count, candidate_count;
    END IF;
END;
$$;

INSERT INTO diffusions_digest (
    execution_id, canal, destinataire_hash, digest_sha256, statut
) VALUES (
    :run_id, 'mailpit', repeat('b', 64), repeat('c', 64), 'envoyee'
)
ON CONFLICT (execution_id, canal, destinataire_hash) DO NOTHING;

INSERT INTO diffusions_digest (
    execution_id, canal, destinataire_hash, digest_sha256, statut
) VALUES (
    :run_id, 'mailpit', repeat('b', 64), repeat('d', 64), 'envoyee'
)
ON CONFLICT (execution_id, canal, destinataire_hash) DO NOTHING;

DO $$
DECLARE
    delivery_count INTEGER;
BEGIN
    SELECT count(*) INTO delivery_count
    FROM diffusions_digest d
    JOIN executions_quotidiennes e ON e.id = d.execution_id
    WHERE e.cle_execution = 'test:automation-smoke'
      AND d.canal = 'mailpit'
      AND d.destinataire_hash = repeat('b', 64);

    IF delivery_count <> 1 THEN
        RAISE EXCEPTION 'Delivery idempotence failed: %', delivery_count;
    END IF;
END;
$$;

ROLLBACK;
