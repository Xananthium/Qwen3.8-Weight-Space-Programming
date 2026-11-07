"""Curate an allowlisted public numerical export from an authorized local archive.

Usage: python3 prepare_public_metrics.py --source-root /path/to/private/archive
Never copies prompts, answer keys, raw traces, tokens, launch settings or host data.
Raw files are read only to calculate metrics and authenticate reviewed excerpts.
"""
import argparse,csv,hashlib,json,re
from pathlib import Path

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tsha(s):return hashlib.sha256(s.encode()).hexdigest()
def dump(name,data):(HERE/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def csvout(name,rows):
    with (HERE/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-root',type=Path,required=True);a=ap.parse_args()
    source=a.source_root.resolve();seen={};loaded={}
    def read(rel):
        p=source/rel;seen[rel]=sha(p)
        if rel not in loaded:loaded[rel]=json.loads(p.read_text())
        return loaded[rel]
    for d in ['metrics','examples','figures','research']:(HERE/d).mkdir(exist_ok=True)
    inventory=read('experiment_inventory.json');ledger=read('results_ledger.json')
    phase={(r['file'],r['id']):r for r in read('phase_structure_ledger.json')['rows']}
    timings={r['file']:r for r in read('timing_ledger.json')['rows']}
    experiments=[]
    for r in ledger['experiments']:
        if not r['file'].startswith('serving_runs/'):continue
        g=r['groups'];p=r['proof_review'] or {};ctx=r['request_context'] or {}
        experiments.append({'source_locator':r['file'],'run':r['file'].split('/')[1],
          'panel':Path(r['file']).name.removesuffix('.result.json'),'seed':r['seed'],'cap':r['cap'],
          'batch_position':ctx.get('batch_position'),'exact_prompt_replays':ctx.get('exact_prompt_replays'),
          'HLE_correct':g.get('HLE',{}).get('correct',0),'HLE_n':g.get('HLE',{}).get('n',0),
          'GSM_correct':g.get('GSM',{}).get('correct',0),'GSM_n':g.get('GSM',{}).get('n',0),
          'sound_core_arguments':p.get('sound_core_arguments'),'error_free_finals':p.get('error_free_final_explanations'),
          'reviewed_HLE_cases':p.get('reviewed_cases'),'total_tokens':r['total_tokens'],
          'thinking_tokens':r['thinking_tokens'],'cutoffs':r['cutoffs'],'wait_occurrences':r['wait_occurrences']})
    batches=[];generations=[]
    loop_sentence='Wait, I should check that again. The calculation seems right, but perhaps I missed something. Let me go back and verify the same steps before I give the answer.'
    for item in inventory['result_files']:
        rel=item['file'];raw=read(rel);assert seen[rel]==item['sha256']
        scorepath=rel.removesuffix('.json')+'.validation_scores.json'
        scorepath2=rel.removesuffix('.json')+'.scores.json'
        if (source/scorepath).exists():grades={r['id']:r['strict_status'] for r in read(scorepath)['rows']}
        elif (source/scorepath2).exists():grades={r['id']:r['status'] for r in read(scorepath2)['rows']}
        else:grades={}
        ident=raw.get('profile_identity',{});candidate=ident.get('candidate') or {}
        batch={'source_locator':rel,'source_sha256':seen[rel],'run':rel.split('/')[1],
          'panel':Path(rel).name.removesuffix('.result.json'),'completed':item['completed_batch'],
          'seed':raw['job']['seed'],'cap':raw['job']['max_tokens'],'temperature':raw['job']['temperature'],
          'response_records':len(raw['outputs']),'observed_generated_tokens':sum(o['tokens'] for o in raw['outputs']),
          'client_elapsed_s':raw.get('elapsed_s'),'profile_manifest_sha256':ident.get('manifest_sha256'),
          'candidate_sha256':candidate.get('sha256'),'runner_sha256':raw.get('runner_sha256')}
        batches.append(batch)
        for o in raw['outputs']:
            text=o['text'];thinking=text.split('</think>',1)[0];words=len(re.findall(r'\b\w+\b',thinking))
            waits=len(re.findall(r'\bwait\b',thinking,re.I));ph=phase[(rel,o['id'])]
            t=next((x for x in timings.get(rel,{}).get('outputs',[]) if x['id']==o['id']),{})
            finish=o['finish_reason'];status=grades.get(o['id'])
            if not item['completed_batch']:status='operator_interrupted' if finish is None else 'natural_stop_without_final'
            generations.append({'source_locator':rel,'source_sha256':seen[rel],'run':batch['run'],
              'panel':batch['panel'],'case_id':o['id'],'domain':'HLE' if o['id'].startswith('hle:') else 'GSM' if 'gsm8k' in o['id'] else 'authored',
              'seed':batch['seed'],'cap':batch['cap'],'batch_completed':batch['completed'],
              'status':status,'finish_reason':'operator_interrupted' if finish is None else finish,
              'output_text_sha256':tsha(text),'total_tokens':o['tokens'],
              'thinking_tokens_before_first_close':ph['initial_thinking_tokens'],
              'tokens_after_first_close':ph['tokens_after_first_close'],'tokens_after_last_close':ph['tokens_after_last_close'],
              'closing_marker_count':ph['text_closing_count'],'phase_classification':ph['classification'],
              'thinking_words':words,'wait_occurrences':waits,'wait_per_1000_thinking_words':1000*waits/words if words else None,
              'exact_cookie_sentence_copies':thinking.count(loop_sentence) if o['id']=='primed_gsm8k_train:2079' else None,
              'max_consecutive_exclamation_characters':max((len(m.group()) for m in re.finditer(r'!+',text)),default=0),
              'client_finished_elapsed_s':t.get('finished_elapsed_s')})
    assert len(batches)==46 and len(generations)==248
    assert sum(r['observed_generated_tokens'] for r in batches)==933411
    assert sum(r['completed'] for r in batches)==45
    dump('metrics/batches.json',batches);dump('metrics/generations.json',generations)
    csvout('metrics/batches.csv',batches);csvout('metrics/generations.csv',generations)
    dump('metrics/experiments.json',experiments);csvout('metrics/experiments.csv',experiments)
    dump('metrics/retention.json',ledger['validation_panel']);csvout('metrics/retention.csv',ledger['validation_panel'])
    counts=dict(inventory['counts']);counts['additional_weight_variants']=14
    dump('metrics/inventory.json',{'scope':'Isolated compiled observations only; repeated development records, not unique questions. Initial busy/eager runs and replay captures excluded.',
      'counts':counts,'attempt_ids':inventory['attempts'],'profile_manifest_sha256':sorted(inventory['profiles']),
      'missing_confirmation':{'warm_seed06':'startup infrastructure failure before any answer','seed08_candidate':'not run','GSM24_candidate':'not run'},
      'operator_interruption':'One expanded batch incomplete; topology stopped naturally at 10,631, hats saved 14,199 tokens without finish reason. Neither produced a final answer.',
      'startup_failure':'016 failed before readiness; no answer-quality evidence.','deferred':'017 did not launch during the experiment.'})
    selected=[]
    def excerpt(label,run,panel,cid,needle,phase_name,review):
        rel=f'serving_runs/{run}/{panel}.result.json';raw=read(rel);o=next(x for x in raw['outputs'] if x['id']==cid)
        text=o['text'];i=text.index(needle);assert text[i:i+len(needle)]==needle
        cut=text.find('</think>')
        assert (phase_name=='thinking' and (cut<0 or i+len(needle)<=cut)) or (phase_name=='post_first_close' and cut>=0 and i>=cut+8)
        selected.append({'id':label,'source_locator':rel,'source_sha256':seen[rel],'output_id':cid,
          'source_text_sha256':tsha(text),'field':'text','phase':phase_name,'start':i,'end':i+len(needle),
          'text':needle,'excerpt_sha256':tsha(needle),'content_review':review})
    for run,label in [('000_calmer','calmer_cookie_recheck'),('013_mlp18_005pct','pilot_cookie_recheck')]:
        excerpt(label,run,'validation6_seed06','primed_gsm8k_train:2079',loop_sentence,'thinking','Supplied synthetic recheck sentence continued by the model; no benchmark question, calculation or answer shown.')
    editor='Wait, no. Inserting at position 2 means the new character goes at index 2, and everything from index 2 onwards shifts right.\n\nText was: C(0), A(1), I(2)\nInsert T at position 2: C(0), A(1), T(2), I(3)\nText: "CTAI", cursor = 3'
    excerpt('pilot_editor_rule_and_literal_conflict','013_mlp18_005pct','validation6_seed06','state_holdout_v1_04',editor,'thinking','Locally authored editor diagnostic. The rule is correct but the literal CTAI conflicts with the shown index sequence; retain this error.')
    excerpt('pilot_editor_correct_final_content','013_mlp18_005pct','validation6_seed06','state_holdout_v1_04','- **Final text:** `CARTI`\n- **Characters left of the cursor:** 3','post_first_close','Locally authored diagnostic; correct final prose, while the box contains only the cursor count.')
    excerpt('pilot_generic_game_recheck','013_mlp18_005pct','fast5_seed06','hle:673722c82bfc8ab579ed111f','Wait, I think I need to be more careful.','thinking','Formula-free generic metareasoning only. No game definition, option, construction, answer or solution revealed.')
    excerpt('pilot_hat_reconsideration','013_mlp18_005pct','expansion2_seed06','hle:66fb931a089552943999ce86','Actually, you know what, let me reconsider one more time. I realize that I should think about this problem more carefully in terms of information asymmetry.','thinking','Generic metareasoning only; no puzzle premises, category assignment, answer or solution revealed.')
    excerpt('interrupted_hat_punctuation','012b_l62_adaptive_selector','expansion2_seed06','hle:66fb931a089552943999ce86','!'*96,'thinking','Punctuation only; 96-character excerpt of an 8,044-character run. No benchmark content or answer revealed.')
    dump('examples/selected_excerpts.json',{'selection':'Post-hoc, separately content-reviewed language examples; not representative samples or extra tests.',
      'offset_convention':'Python Unicode-codepoint half-open [start,end) in raw output.text; UTF-8 SHA256, no normalization.',
      'source_access':'Source locators identify withheld private evidence, not public download paths. Verification requires separately authorized source access.',
      'phase_convention':'First generated closing-think marker separates initial thinking from subsequent content; truncated/unclosed text is not a completed final.',
      'records':selected})
    activation=read('production_trial_20261106/activation_attestation.json')
    dump('metrics/operational_status.json',{'status':'User-selected Calmer V2 hands-on pilot; active after authorized reboot.',
      'verified_utc':activation['verified_utc'],'profile_manifest_sha256':activation['profile_manifest_sha256'],
      'startup_and_smoke_passed':bool(activation['health_http_200'] and activation['smoke_passed']),
      'benchmark_confirmation':False,'limits':'Startup binding checks and a small readiness response are not warm/second-seed/GSM24 benchmark confirmation. Operational selection does not revise experimental grades.'})
    language=[]
    for run in sorted({g['run'] for g in generations}):
        rows=[g for g in generations if g['run']==run and g['panel']=='fast5_seed06']
        if not rows:continue
        n=sum(g['thinking_words'] for g in rows);w=sum(g['wait_occurrences'] for g in rows)
        language.append({'run':run,'panel':'fast5_seed06','n':len(rows),'thinking_words':n,'wait_occurrences':w,'wait_per_1000_thinking_words':1000*w/n if n else None,'total_tokens':sum(g['total_tokens'] for g in rows)})
    dump('metrics/language_summary.json',language);csvout('metrics/language_summary.csv',language)
    fit=read('protected_mlp/candidate_manifest.json')
    pilot=next(c for c in fit['candidates'] if c['added_layer']==18 and c['target_productive_p95_ratio']==.005)
    keep=['sha256','added_layer','support_size','selected_columns','global_alpha_required','target_productive_p95_ratio',
      'productive_ratio','circular_ratio','base_arrays_byte_identical','base_layers_retained','added_output_direction_norm',
      'protected_subspace_projection_applied','gram_condition']
    dump('metrics/pilot_construction.json',{'candidate':{k:pilot[k] for k in keep},
      'fit_examples':'Six authored pairs; 12 endpoints; 32 tail tokens each, captured under Calmer. No HLE traces or keys used for fitting.',
      'objective':'mean((X_c a-1)^2)+8*mean((X_p a)^2)+0.1*norm(a_standardized)^2; no intercept',
      'output_direction':'Equal-weight mean of normalized circular-minus-productive residual contrasts; no output-space protected-subspace projection.',
      'protection_limit':'Productive-token covariance penalty only; not a validated causal reasoning subspace or a guarantee of retention.',
      'selection_limit':'Layer/support selected on the same six pairs; leave-one-pair-out diagnostics are exploratory, not an independent accuracy test.'})
    scanrel='protected_mlp/all_layers_lopo_scan.csv';seen[scanrel]=sha(source/scanrel)
    with (source/scanrel).open() as stream:scan=list(csv.DictReader(stream))
    fields=['layer','support','cv_loss','cv_gap_min','cv_positive_gap_pairs','cv_productive_rms','cv_circular_rms','cv_support_overlap_min']
    csvout('metrics/mlp_layer_scan.csv',[{k:r[k] for k in fields} for r in scan])
    dump('metrics/source_manifest.json',{'policy':'Hash-inventory only; full prompts, answers, rationales, traces, token arrays and private operations are withheld.',
      'transformations':['Allowlisted numerical fields only.','Aggregate strict choice correctness retained without answer labels.','Raw text read transiently for counts/hashes; only separately reviewed spans emitted.','Operational attestation reduced to selection/date/pass booleans and model-profile hash.','No host paths, endpoints, process identifiers, authentication or launch configuration copied.'],
      'inputs':[{'locator':rel,'sha256':h} for rel,h in sorted(seen.items())]})
    print(json.dumps({'batches':len(batches),'responses':len(generations),'tokens':sum(g['total_tokens'] for g in generations),'excerpts':len(selected)}))

if __name__=='__main__':main()
