BEGIN;

INSERT INTO collectes_haicop (source, statut, parametres)
VALUES ('haicop', 'terminee', '{"test": "document_processing"}'::jsonb)
RETURNING id \gset test_collection_

INSERT INTO appels_offres (
    tender_id,
    organisme,
    titre,
    url_detail,
    collecte_id
) VALUES (
    'Tender-SMOKE-DOCUMENT',
    'Organisme test',
    'Test traitement document',
    'https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-SMOKE-DOCUMENT',
    :test_collection_id
);

INSERT INTO documents_ao (
    tender_id,
    libelle,
    type_document,
    url
) VALUES (
    'Tender-SMOKE-DOCUMENT',
    'Document test',
    'pdf',
    'https://www.marchespublics.gov.tn/storage/tender/test-smoke.pdf'
)
RETURNING id \gset test_document_

UPDATE documents_ao
SET chemin_local = 'data/documents/Tender-SMOKE-DOCUMENT/test.pdf',
    empreinte_sha256 = repeat('a', 64),
    taille_octets = 1234,
    mime_type = 'application/pdf',
    texte_extrait = 'Texte de test',
    statut_traitement = 'extrait',
    traite_le = clock_timestamp()
WHERE id = :test_document_id;

DO $$
DECLARE
    row_count INTEGER;
BEGIN
    SELECT count(*)
    INTO row_count
    FROM documents_ao
    WHERE tender_id = 'Tender-SMOKE-DOCUMENT'
      AND statut_traitement = 'extrait'
      AND empreinte_sha256 = repeat('a', 64)
      AND texte_extrait = 'Texte de test';

    IF row_count <> 1 THEN
        RAISE EXCEPTION 'Le traitement documentaire de test est invalide';
    END IF;
END;
$$;

ROLLBACK;
