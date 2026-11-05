#!/usr/bin/env python3
"""Verify independently authorized HLE source locally; no downloads or uploads.

Optional private reconstructed records contain benchmark text/keys. Keep them
outside the public repository. Tokenizer/template must match the experiment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

SYSTEM = ('Your response should be in the following format:\n'
          'Explanation: {your explanation for your answer choice}\n'
          'Answer: {your chosen answer}\n'
          'Confidence: {your confidence score between 0% and 100% for your answer}')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parquet',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,default=Path(__file__).with_name('hle_record_hashes.json'))
    parser.add_argument('--tokenizer-dir',type=Path)
    parser.add_argument('--private-output',type=Path)
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text())
    with args.parquet.open('rb') as f:
        assert hashlib.file_digest(f,'sha256').hexdigest()==manifest['parquet_sha256'],'Source parquet differs'
    import pyarrow.parquet as pq
    rows=pq.read_table(args.parquet,columns=['id','question','answer','rationale','raw_subject','category']).to_pylist()
    by_id={r['id']:r for r in rows}
    tokenizer=template=None
    if args.tokenizer_dir:
        from transformers import AutoTokenizer
        tokenizer=AutoTokenizer.from_pretrained(str(args.tokenizer_dir),local_files_only=True)
        template=(args.tokenizer_dir/'chat_template.jinja').read_text()
    reconstructed=[]
    for expected in manifest['records']:
        r=by_id[expected['dataset_id']]
        assert digest_text(r['question'])==expected['question_utf8_sha256'],'Question bytes differ: '+expected['id']
        if tokenizer is None:
            continue
        labels=re.findall(r'(?m)^\s*[\[(]?([A-Z])[\]).]\s+',r['question'])
        messages=[dict(role='system',content=SYSTEM),dict(role='user',content=r['question'])]
        prompt=tokenizer.apply_chat_template(messages,tokenize=False,chat_template=template,
                                             add_generation_prompt=True,enable_thinking=True,reasoning_effort='medium')
        record=dict(id='hle:'+r['id'],hle_id=r['id'],source='hle_text_mcq',kind='hle_mcq',
                    problem=r['question'],answer=r['answer'].strip(),choices=sorted(set(labels)),
                    category=r['category'],subject=r['raw_subject'],reference_rationale=r['rationale'],
                    messages=messages,prompt=prompt,
                    prompt_tokens_estimate=len(tokenizer.encode(prompt,add_special_tokens=False)),reasoning_effort='medium')
        assert digest_text(canonical(record))==expected['canonical_record_sha256'],'Frozen record/template differs: '+expected['id']
        reconstructed.append(record)
    if args.private_output:
        assert tokenizer is not None,'Private exact records require --tokenizer-dir'
        assert not args.private_output.exists(),'Refusing to overwrite output'
        public_root=Path(__file__).resolve().parent
        assert public_root not in args.private_output.resolve().parents,'Write private benchmark records outside public evidence'
        args.private_output.parent.mkdir(parents=True,exist_ok=True)
        args.private_output.write_text(json.dumps(reconstructed,indent=2)+'\n')
        args.private_output.chmod(0o600)
    print(json.dumps(dict(source_verified=True,questions_verified=len(manifest['records']),
                          exact_records_verified=len(reconstructed),private_output_written=bool(args.private_output))))


if __name__=='__main__':main()
