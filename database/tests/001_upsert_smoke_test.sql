\set ON_ERROR_STOP on

BEGIN;

DELETE FROM appels_offres WHERE tender_id = 'Tender-TEST-UPSERT';

INSERT INTO appels_offres (
    tender_id,
    plan_id,
    organisme,
    titre,
    date_publication,
    date_limite,
    reserve_pme,
    url_detail,
    donnees_brutes
) VALUES (
    'Tender-TEST-UPSERT',
    'PLAN-TEST',
    'Organisme test',
    'Version initiale',
    '2026-07-20T08:00:00+02:00',
    '2026-08-20T10:00:00+02:00',
    FALSE,
    'https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-TEST-UPSERT',
    '{"version": 1}'::jsonb
)
ON CONFLICT (tender_id) DO UPDATE SET
    plan_id = EXCLUDED.plan_id,
    organisme = EXCLUDED.organisme,
    titre = EXCLUDED.titre,
    date_publication = EXCLUDED.date_publication,
    date_limite = EXCLUDED.date_limite,
    reserve_pme = EXCLUDED.reserve_pme,
    url_detail = EXCLUDED.url_detail,
    donnees_brutes = EXCLUDED.donnees_brutes,
    derniere_collecte_le = clock_timestamp();

INSERT INTO appels_offres (
    tender_id,
    plan_id,
    organisme,
    titre,
    date_publication,
    date_limite,
    reserve_pme,
    url_detail,
    donnees_brutes
) VALUES (
    'Tender-TEST-UPSERT',
    'PLAN-TEST',
    'Organisme test mis a jour',
    'Version mise a jour',
    '2026-07-20T08:00:00+02:00',
    '2026-08-21T10:00:00+02:00',
    TRUE,
    'https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-TEST-UPSERT',
    '{"version": 2}'::jsonb
)
ON CONFLICT (tender_id) DO UPDATE SET
    plan_id = EXCLUDED.plan_id,
    organisme = EXCLUDED.organisme,
    titre = EXCLUDED.titre,
    date_publication = EXCLUDED.date_publication,
    date_limite = EXCLUDED.date_limite,
    reserve_pme = EXCLUDED.reserve_pme,
    url_detail = EXCLUDED.url_detail,
    donnees_brutes = EXCLUDED.donnees_brutes,
    derniere_collecte_le = clock_timestamp();

DO $$
DECLARE
    ligne_count INTEGER;
    titre_actuel TEXT;
    version_actuelle INTEGER;
BEGIN
    SELECT COUNT(*), MAX(titre), MAX((donnees_brutes ->> 'version')::INTEGER)
    INTO ligne_count, titre_actuel, version_actuelle
    FROM appels_offres
    WHERE tender_id = 'Tender-TEST-UPSERT';

    IF ligne_count <> 1 THEN
        RAISE EXCEPTION 'Echec anti-doublon: % lignes trouvees', ligne_count;
    END IF;

    IF titre_actuel <> 'Version mise a jour' OR version_actuelle <> 2 THEN
        RAISE EXCEPTION 'Echec upsert: les nouvelles valeurs ne sont pas stockees';
    END IF;
END;
$$;

INSERT INTO documents_ao (tender_id, libelle, url)
VALUES (
    'Tender-TEST-UPSERT',
    'Document initial',
    'https://www.marchespublics.gov.tn/storage/tender/test.pdf'
)
ON CONFLICT (tender_id, url) DO UPDATE SET
    libelle = EXCLUDED.libelle,
    derniere_collecte_le = clock_timestamp();

INSERT INTO documents_ao (tender_id, libelle, url)
VALUES (
    'Tender-TEST-UPSERT',
    'Document mis a jour',
    'https://www.marchespublics.gov.tn/storage/tender/test.pdf'
)
ON CONFLICT (tender_id, url) DO UPDATE SET
    libelle = EXCLUDED.libelle,
    derniere_collecte_le = clock_timestamp();

DO $$
DECLARE
    document_count INTEGER;
    libelle_actuel TEXT;
BEGIN
    SELECT COUNT(*), MAX(libelle)
    INTO document_count, libelle_actuel
    FROM documents_ao
    WHERE tender_id = 'Tender-TEST-UPSERT';

    IF document_count <> 1 OR libelle_actuel <> 'Document mis a jour' THEN
        RAISE EXCEPTION 'Echec anti-doublon document';
    END IF;
END;
$$;

ROLLBACK;

\echo 'OK: upsert appels_offres et documents_ao valide sans donnees de test persistantes.'
