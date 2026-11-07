"""Standard-library public CI checks; optional separately authorized source audit.

Public-only: python3 followup_20261106/verify_publication.py
Optional: add --source-root PATH to authenticate withheld source hashes/slices.
Neither mode starts a model, accesses a service, or generates new answers.
"""
import argparse,hashlib,json,re
from pathlib import Path
from urllib.parse import unquote
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
tsha=lambda s:hashlib.sha256(s.encode()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
def public_files():
    return sorted(p for p in P.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
def run_checks(check_manifest=True,source_root=None):
    batches=load(P/'metrics/batches.json');gen=load(P/'metrics/generations.json')
    inventory=load(P/'metrics/inventory.json')['counts'];ex=load(P/'examples/selected_excerpts.json')['records']
    assert len(batches)==46 and sum(b['completed'] for b in batches)==45
    assert len(gen)==248 and sum(g['total_tokens'] for g in gen)==933411
    assert inventory['additional_weight_variants']==14 and inventory['isolated_server_launch_attempts']==20
    assert inventory['saved_response_records_including_interrupted']==248
    assert inventory['observed_generated_tokens_including_interrupted']==933411
    for b in batches:
        chosen=[g for g in gen if g['source_locator']==b['source_locator']]
        assert len(chosen)==b['response_records']
        assert sum(g['total_tokens'] for g in chosen)==b['observed_generated_tokens']
        assert all(g['source_sha256']==b['source_sha256'] for g in chosen)
    interrupted=[g for g in gen if not g['batch_completed']]
    assert len(interrupted)==2
    assert sorted(g['total_tokens'] for g in interrupted)==[10631,14199]
    assert {g['finish_reason'] for g in interrupted}=={'stop','operator_interrupted'}
    assert len(ex)==7
    for r in ex:
        assert r['end']-r['start']==len(r['text']) and tsha(r['text'])==r['excerpt_sha256']
        assert re.fullmatch('[a-f0-9]{64}',r['source_sha256'])
        if r['output_id'].startswith('hle:'):
            assert len(r['text'])<=220
            assert not re.search(r'[0-9$=<>\\]',r['text'])
            assert not re.search(r'\b(?:answer|option|choice)\s*[:=]',r['text'],re.I)
    # Structured data is allowlisted; do not accidentally add raw output fields.
    prohibited={'prompt','token_ids','prompt_token_ids','initial_prompt_token_ids','answer','official_key',
        'gold','raw_answer','predicted','expected','rationale','reference_rationale','extracted_answer','final_answer'}
    def keys(obj):
        if isinstance(obj,dict):
            assert not (set(obj)&prohibited),set(obj)&prohibited
            for v in obj.values():keys(v)
        elif isinstance(obj,list):
            for v in obj:keys(v)
    text_files=[p for p in public_files() if p.suffix in {'.py','.json','.md','.txt','.csv','.svg'}]
    for p in text_files:
        text=p.read_text()
        assert ('/'+'home/') not in text and ('/'+'Users/') not in text
        assert not re.search(r'\b(?:hf|ghp)_[A-Za-z0-9]{20,}\b',text)
        assert not re.search(r'https?://(?:localhost|127\.0\.0\.1|(?:\d{1,3}\.){3}\d{1,3})',text)
        assert not any(s in text for s in ['Main'+'PID=','/system'+'.slice/','Control'+'Group='])
        if p.suffix=='.json':keys(json.loads(text))
    links=0
    for p in P.rglob('*.md'):
        for m in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text(),re.S):
            target=m.group(1).split('#',1)[0]
            if not target or target.startswith(('https://','http://','mailto:')):continue
            resolved=(p.parent/unquote(target)).resolve()
            if not check_manifest and resolved==P/'PUBLICATION_MANIFEST.json':
                links+=1;continue
            assert resolved.exists(),(p.name,target);links+=1
    if check_manifest:
        manifest=load(P/'PUBLICATION_MANIFEST.json')
        for r in manifest['outputs']:assert sha(P/r['path'])==r['sha256'],r['path']
        expected={r['path'] for r in manifest['outputs']}
        actual={str(p.relative_to(P)) for p in public_files() if p.name!='PUBLICATION_MANIFEST.json'}
        assert expected==actual,(sorted(actual-expected),sorted(expected-actual))
    source_inputs=0
    if source_root is not None:
        source_root=Path(source_root)
        for r in load(P/'metrics/source_manifest.json')['inputs']:
            assert sha(source_root/r['locator'])==r['sha256'];source_inputs+=1
        for r in ex:
            source=load(source_root/r['source_locator'])
            o=next(o for o in source['outputs'] if o['id']==r['output_id']);text=o[r['field']]
            assert tsha(text)==r['source_text_sha256']
            assert text[r['start']:r['end']]==r['text']
    return {'status':'passed','standard_library_only':True,'batches':46,'response_records':248,
        'observed_generated_tokens':933411,'selected_literal_spans':7,'local_links_checked':links,
        'host_and_raw_field_screens_passed':True,'manifest_hashes_checked':check_manifest,
        'authorized_source_inputs_checked':source_inputs,'scope_limit':'Public checks authenticate the reduced package; source access is required for raw slice verification. Manual content review, not these checks alone, establishes the excerpt publication scope.'}
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-root',type=Path);a=ap.parse_args()
    print(json.dumps(run_checks(source_root=a.source_root),indent=2))
if __name__=='__main__':main()
