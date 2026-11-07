"""Refresh the curated subtree's checks and output hashes; no external writes."""
from datetime import datetime,timezone
import json
from pathlib import Path
import verify_publication as verify
P=Path(__file__).resolve().parent
checks=verify.run_checks(check_manifest=False)
(P/'PUBLICATION_CHECKS.json').write_text(json.dumps(checks,indent=2)+'\n')
manifest={'schema_version':1,'created_at_utc':datetime.now(timezone.utc).isoformat(),
 'scope':'Curated public derived observations and separately reviewed nonsolution excerpts; no raw benchmark archive.',
 'source_manifest':'metrics/source_manifest.json','policy':'RIGHTS_AND_SCOPE.md',
 'manual_excerpt_review':'examples/selected_excerpts.json: content_review per span; formula-free HLE metareasoning or punctuation only.',
 'excluded':['Full benchmark questions/options/images','Official answer labels and reference rationales','Complete HLE solutions or full raw traces','Reversible token arrays','Private host/endpoint/process/service/authentication information'],
 'transformations':['Numerical fields copied through explicit allowlists.','All46 isolated batches retained, including one interrupted batch.','Current operational selection reduced to safe status, timestamp and profile hash; smoke is not benchmark evidence.','Figures rebuilt solely from public metrics.','Source-relative locators and whole-source hashes retained without rehosting private bytes.'],
 'public_ci_command':'python3 followup_20261106/verify_publication.py',
 'outputs':[{'path':str(p.relative_to(P)),'sha256':verify.sha(p),'bytes':p.stat().st_size} for p in verify.public_files() if p.name!='PUBLICATION_MANIFEST.json']}
(P/'PUBLICATION_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(verify.run_checks(),indent=2))
