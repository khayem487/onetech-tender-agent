BEGIN;

ALTER TABLE documents_ao
    ADD COLUMN IF NOT EXISTS mime_type TEXT,
    ADD COLUMN IF NOT EXISTS taille_octets BIGINT,
    ADD COLUMN IF NOT EXISTS statut_traitement TEXT NOT NULL DEFAULT 'a_traiter',
    ADD COLUMN IF NOT EXISTS erreur_traitement TEXT,
    ADD COLUMN IF NOT EXISTS traite_le TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'documents_ao_taille_octets_check'
          AND conrelid = 'documents_ao'::regclass
    ) THEN
        ALTER TABLE documents_ao
            ADD CONSTRAINT documents_ao_taille_octets_check
            CHECK (taille_octets IS NULL OR taille_octets >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'documents_ao_statut_traitement_check'
          AND conrelid = 'documents_ao'::regclass
    ) THEN
        ALTER TABLE documents_ao
            ADD CONSTRAINT documents_ao_statut_traitement_check
            CHECK (
                statut_traitement IN (
                    'a_traiter',
                    'extrait',
                    'sans_texte',
                    'non_supporte',
                    'echec'
                )
            );
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_documents_ao_statut_traitement
    ON documents_ao (statut_traitement, id);

COMMENT ON COLUMN documents_ao.statut_traitement IS
    'Etat du telechargement et de extraction locale du document.';
COMMENT ON COLUMN documents_ao.chemin_local IS
    'Chemin relatif au workspace vers le fichier public telecharge.';
COMMENT ON COLUMN documents_ao.texte_extrait IS
    'Texte extrait localement du PDF ou DOCX, sans analyse IA.';

COMMIT;
