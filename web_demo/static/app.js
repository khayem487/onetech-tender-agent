const $ = (id) => document.getElementById(id);
const classificationLabels = {avis:'Avis d’appel d’offres',dossier_de_fond:'Dossier de fond',annexe_technique:'Annexe technique',annexe_administrative:'Annexe administrative',autre:'Autre document'};
let capability = null, result = null, qualification = null, requestController = null, requestSequence = 0, busy = false;

function feedback(id, message, kind = '') {
  const target = $(id);
  target.textContent = message;
  target.classList.remove('is-error', 'is-busy');
  if (kind) target.classList.add(`is-${kind}`);
}
function controls() {
  $('document-fields').disabled = busy || !capability;
  $('document-file').disabled = busy || !capability?.uploads_enabled;
  $('process-file').disabled = busy || !capability?.uploads_enabled;
  $('cancel-process').hidden = !busy;
  $('reviewed').disabled = busy || !result?.document.text.trim();
  $('decision-fields').disabled = busy || !result?.document.text.trim() || !$('reviewed').checked;
  $('download-result').disabled = busy || !result;
  $('clear-result').disabled = busy;
}
function clearQualification() {
  qualification = null;
  $('decision-form').reset();
  $('reviewed').checked = false;
  $('decision-result').hidden = true;
  feedback('decision-status', result ? 'Relisez les sources, puis renseignez vos quatre notes.' : 'Traitez un document pour accéder au barème.');
}
function render(data) {
  if (!data?.document || typeof data.document.text !== 'string' || !Array.isArray(data.sources) || !Array.isArray(data.warnings) || !data.relevance || data.processing?.ai !== false) throw new Error('Le serveur a renvoyé un résultat incomplet.');
  result = data;
  clearQualification();
  $('result-empty').hidden = true;
  $('result-content').hidden = false;
  $('processing-badge').hidden = false;
  $('document-name').textContent = data.document.name;
  $('document-details').textContent = `${String(data.document.type).toUpperCase()} · ${data.document.pages == null ? 'Repères par passages' : `${data.document.pages} page${data.document.pages > 1 ? 's' : ''}`} · ${data.document.text.length.toLocaleString('fr-FR')} caractères extraits`;
  $('document-hash').textContent = data.document.sha256;
  $('document-classification').textContent = classificationLabels[data.classification] || 'Autre document';
  $('relevance-score').textContent = `${data.relevance.score} point${Math.abs(data.relevance.score) === 1 ? '' : 's'}`;
  $('relevance-explanation').textContent = 'Classement lexical du projet sur le texte extrait : +3 par terme recherché trouvé, −4 par terme exclu du filtre d’origine. Ce score n’est pas une décision Go/No-Go.';
  $('relevance-reasons').replaceChildren();
  for (const reason of data.relevance.reasons || []) {
    const item = document.createElement('li'); item.textContent = reason; $('relevance-reasons').append(item);
  }
  if (!(data.relevance.reasons || []).length) {
    const item = document.createElement('li'); item.textContent = 'Aucun signal lexical repéré'; $('relevance-reasons').append(item);
  }
  $('warning-list').replaceChildren();
  for (const warning of data.warnings) { const item = document.createElement('li'); item.textContent = warning; $('warning-list').append(item); }
  $('warnings').hidden = !data.warnings.length;
  $('sources').replaceChildren();
  for (const [index, source] of data.sources.entries()) {
    const item = document.createElement('article'); item.className = 'source';
    const label = document.createElement('span'); label.textContent = source.page == null ? `Passage ${index + 1}` : `Page ${source.page}`;
    const quote = document.createElement('blockquote'); quote.textContent = source.quote;
    item.append(label, quote); $('sources').append(item);
  }
  if (!data.sources.length) { const empty = document.createElement('p'); empty.className = 'muted'; empty.textContent = 'Aucun passage natif exploitable. Vérifiez les limites indiquées ci-dessus.'; $('sources').append(empty); }
  $('extracted-text').textContent = data.document.text || 'Aucun texte natif extrait.';
  $('reviewed').disabled = !data.document.text.trim();
  feedback('process-status', data.partial ? 'Extraction terminée · contexte partiel à compléter.' : 'Extraction terminée · consultez les passages avant de qualifier.');
}
async function readResponse(response) {
  let data;
  try { data = await response.json(); } catch { throw new Error('Le serveur est indisponible pour le moment. Réessayez dans un instant.'); }
  if (!response.ok) throw new Error(typeof data.message === 'string' ? data.message : 'Le document n’a pas pu être traité. Vérifiez son format et sa taille.');
  return data;
}
function getKeywords() {
  const terms = $('keywords').value.split(',').map(word => word.trim()).filter(Boolean);
  if (terms.length > 12 || terms.some(word => word.length > 40)) throw new Error('Utilisez au maximum 12 mots-clés de 40 caractères chacun.');
  return terms;
}
async function processDocument(sample = null) {
  if (busy || !capability) return;
  let form;
  try {
    form = new FormData(); form.set('keywords', JSON.stringify(getKeywords()));
    if (sample) form.set('sample', sample);
    else {
      const file = $('document-file').files[0];
      if (!file) throw new Error('Choisissez un PDF ou un DOCX, ou utilisez l’un des exemples.');
      if (!/\.(pdf|docx)$/i.test(file.name)) throw new Error('Choisissez un fichier PDF ou DOCX.');
      if (file.size > capability.limits.file_bytes) throw new Error('Le fichier dépasse la taille autorisée de 2 Mo.');
      form.set('file', file);
    }
  } catch (error) { feedback('process-status', error.message, 'error'); return; }
  busy = true; const ticket = ++requestSequence; const controller = new AbortController(); requestController = controller;
  const timer = setTimeout(() => controller.abort('timeout'), 30000);
  result = null; clearQualification(); $('result-content').hidden = true; $('result-empty').hidden = false; $('processing-badge').hidden = true;
  feedback('process-status', 'Extraction en cours… Le premier accès peut prendre quelques secondes.', 'busy'); controls();
  try {
    const data = await readResponse(await fetch('/api/process', {method:'POST',body:form,signal:controller.signal,credentials:'omit'}));
    if (ticket === requestSequence) render(data);
  } catch (error) {
    if (ticket === requestSequence) feedback('process-status', controller.signal.aborted ? (controller.signal.reason === 'timeout' ? 'Le serveur a mis trop de temps à répondre. Réessayez dans un instant.' : 'Attente arrêtée. Un traitement déjà reçu par le serveur peut encore se terminer ; son fichier temporaire sera supprimé.') : error.message, 'error');
  } finally {
    clearTimeout(timer);
    if (ticket === requestSequence) { busy = false; requestController = null; controls(); }
  }
}
async function connect() {
  $('retry-service').hidden = true;
  feedback('service-status','Connexion à l’atelier…');
  try {
    capability = await readResponse(await fetch('/api/capabilities', {signal:AbortSignal.timeout(20000),credentials:'omit'}));
    if (!capability?.limits || capability.ai !== false) throw new Error('Les capacités du service sont indisponibles.');
    feedback('service-status','Moteur documentaire disponible · aucun modèle IA appelé');
    $('upload-availability').textContent = capability.uploads_enabled ? 'PDF natifs et DOCX. Les scans sans texte nécessitent un OCR, absent de cet atelier.' : 'Les fichiers personnels sont désactivés dans cet environnement. Les exemples PDF/DOCX restent disponibles.';
  } catch { capability = null; feedback('service-status','Connexion au serveur indisponible. Vous pouvez réessayer.', 'error'); $('retry-service').hidden = false; }
  controls();
}
$('document-form').addEventListener('submit', event => {event.preventDefault(); processDocument();});
$('sample-pdf').addEventListener('click', () => processDocument('pdf'));
$('sample-docx').addEventListener('click', () => processDocument('docx'));
$('retry-service').addEventListener('click', connect);
$('reviewed').addEventListener('change', () => {if (!result?.document.text.trim()) $('reviewed').checked = false; controls();});
$('cancel-process').addEventListener('click', () => requestController?.abort('cancel'));
function clearReading() {
  result = null; $('document-file').value = ''; clearQualification();
  for (const id of ['document-name','document-details','document-hash','document-classification','relevance-score','relevance-explanation','extracted-text']) $(id).textContent = '';
  for (const id of ['sources','warning-list','relevance-reasons']) $(id).replaceChildren();
  $('result-content').hidden = true; $('result-empty').hidden = false; $('processing-badge').hidden = true;
  feedback('process-status','Lecture effacée de cette page. Vous pouvez traiter un autre document.'); controls();
}
$('clear-result').addEventListener('click', clearReading);
$('decision-form').addEventListener('submit', async event => {
  event.preventDefault(); if (busy || !result || !$('reviewed').checked || !$('decision-form').reportValidity()) return;
  const payload = Object.fromEntries([...new FormData(event.currentTarget)].map(([key, value]) => [key, Number(value)]));
  payload.partial = Boolean(result.partial);
  const ticket = ++requestSequence, controller = new AbortController(); requestController = controller;
  const timer = setTimeout(() => controller.abort('timeout'), 20000);
  busy = true; controls(); $('decision-result').hidden = true; qualification = null;
  feedback('decision-status','Vérification de vos quatre notes…','busy');
  try {
    const data = await readResponse(await fetch('/api/decision', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal,credentials:'omit'}));
    if (ticket !== requestSequence) return;
    qualification = data;
    $('decision-label').textContent = {GO:'GO',A_DISCUTER:'À DISCUTER',NO_GO:'NO-GO'}[data.decision] || data.decision;
    $('decision-total').textContent = `${data.total} / 100`;
    $('decision-result').hidden = false;
    feedback('decision-status','Barème vérifié à partir de vos notes. Aucune note n’a été générée par une IA.');
  } catch (error) { if (ticket === requestSequence) feedback('decision-status', controller.signal.aborted ? 'La vérification a été interrompue. Vous pouvez réessayer.' : error.message, 'error'); }
  finally { clearTimeout(timer); if (ticket === requestSequence) {busy = false; requestController = null; controls();} }
});
$('download-result').addEventListener('click', () => {
  if (!result || busy) return;
  const blob = new Blob([JSON.stringify({...result,qualification_manuelle:qualification},null,2)],{type:'application/json;charset=utf-8'});
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = 'onetech-lecture-documentaire.json'; link.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
});
window.addEventListener('pagehide', () => {requestSequence++; requestController?.abort('navigation'); requestController = null; busy = false; clearReading();});
window.addEventListener('pageshow', event => {if (event.persisted) connect();});
controls(); connect();
