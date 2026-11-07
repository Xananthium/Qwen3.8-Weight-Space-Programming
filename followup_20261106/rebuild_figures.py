"""Generate scientific figures using only this public subtree's numeric inputs."""
import csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'calmer-v2-followup-20261106'})
load=lambda n:json.loads((P/n).read_text())
def save(fig,name):
    fig.tight_layout()
    fig.savefig(P/f'figures/{name}.png',dpi=170,metadata={'Software':'Matplotlib; public numerical inputs'})
    fig.savefig(P/f'figures/{name}.svg',metadata={'Date':None,'Creator':'Public follow-up plotting script'})
    plt.close(fig)
exp=[r for r in load('metrics/experiments.json') if r['panel']=='fast5_seed06' and r['cap']==16384 and r['batch_position']==1]
# Keep the 16K budget here; all 32K comparisons remain in the complete table.
names={'000_calmer':'Calmer reference','001_original':'Original weights','002_l62_01pct':'MLP62: old RMS1%',
 '003_l62_03pct':'MLP62: old RMS3%','004_attention55_005pct':'Attention55: productive p95 0.5%',
 '005_mlp53_005pct':'MLP53: productive p95 0.5%','006_neuron18_zero':'MLP18: single-neuron zeroing',
 '007_mlp53_random_u':'MLP53: random output direction','009_l62_02pct':'MLP62: old RMS2%',
 '010_l61_01pct':'MLP61: old RMS1%','012_l62_03pct_eosprotected':'MLP62: EOS protection',
 '012a_l62_eosclosingprotected':'MLP62: EOS + closing protection','012b_l62_adaptive_selector':'MLP62: refitted selector',
 '013_mlp18_005pct':'MLP18 pilot: productive p95 0.5%','014_attention63_005pct':'Attention63: productive p95 0.5%'}
labels=[names[r['run']] for r in exp]
colors=['#268078' if r['run']=='013_mlp18_005pct' else '#52718c' if r['run']=='000_calmer' else '#c7a879' if r['HLE_correct']<2 else '#a8b5c0' for r in exp]
fig,ax=plt.subplots(figsize=(11,8));ax.barh(range(len(exp)),[r['total_tokens'] for r in exp],color=colors)
ax.set_yticks(range(len(exp)),labels);ax.invert_yaxis();ax.set_xlabel('Generated tokens, whole five-case batch')
for i,r in enumerate(exp):ax.text(r['total_tokens']+220,i,f"{r['HLE_correct']}/2 HLE; {r['cutoffs']} cutoff",va='center',fontsize=8)
ax.set_xlim(0,max(r['total_tokens'] for r in exp)*1.37);ax.set_title('First-batch 16K fast comparisons: shorter is not sufficient')
fig.text(.99,.01,'Three GSM answers accompany each batch; proof and retention results are separate.',ha='right',fontsize=8)
save(fig,'fast_panel_outcomes')
gen=load('metrics/generations.json');get=lambda run,cid:next(r for r in gen if r['run']==run and r['case_id']==cid)
runs=['000_calmer','002_l62_01pct','003_l62_03pct','012_l62_03pct_eosprotected','012a_l62_eosclosingprotected','013_mlp18_005pct','014_attention63_005pct']
cookie=[get(run,'primed_gsm8k_train:2079') for run in runs]
short=['Calmer','L62 1%','L62 3%','EOS guard','EOS+close','MLP18 pilot','Attention63']
fig,axs=plt.subplots(1,2,figsize=(11,4.6))
for ax,key,title in zip(axs,['total_tokens','exact_cookie_sentence_copies'],['Whole-completion tokens','Exact generated sentence copies']):
    ax.bar(range(len(cookie)),[r[key] for r in cookie],color=['#52718c']+['#a8b5c0']*4+['#268078','#c7a879'])
    ax.set_xticks(range(len(cookie)),short,rotation=35,ha='right');ax.set_title(title)
    for i,r in enumerate(cookie):ax.text(i,r[key],str(r[key]),ha='center',va='bottom',fontsize=8)
fig.suptitle('Cookie continuation: repetition and completion quality are different')
fig.text(.5,.01,'L62 3% is unstable; Attention63 is a malformed cutoff. Fewer copies do not make either a success.',ha='center',fontsize=8)
save(fig,'cookie_tokens_and_repeats')
with (P/'metrics/mlp_layer_scan.csv').open() as f:scan=[r for r in csv.DictReader(f) if int(r['support'])==32]
scan.sort(key=lambda r:int(r['layer']))
fig,ax=plt.subplots(figsize=(10,4));ax.plot([int(r['layer']) for r in scan],[float(r['cv_loss']) for r in scan],color='#52718c',lw=1.5)
ax.axvspan(48.5,51.5,color='#ddd',label='existing patch (ineligible)')
for layer,label,color in [(18,'selected early pilot','#268078'),(53,'best late fit','#b47747')]:
    r=next(r for r in scan if int(r['layer'])==layer);y=float(r['cv_loss']);ax.scatter([layer],[y],color=color,zorder=3);ax.annotate(label,(layer,y),xytext=(5,12),textcoords='offset points',color=color)
ax.set(xlabel='Zero-based MLP layer',ylabel='Leave-one-pair-out selector loss',title='Exploratory six-pair selection; lower fit loss is not an accuracy result')
ax.legend(loc='upper left');save(fig,'mlp_layer_scan')
