# Primary-source research checked on 6 November 2026

These notes curate the experiment's source review. Search date, first submission and later revision are different facts. No directly applicable new 5–6 November fixed-edit result was established. The follow-up combines local hypotheses with prior methods; it does not reproduce their complete protocols or establish their results on this checkpoint.

| Primary source | Actual date noted in the source log | Relevance and limit |
|---|---|---|
|[When Can One Neuron Fix Repetition Loops in LLMs?](https://arxiv.org/html/2606.13705v2)|First 9 June 2026; v2 24 August 2026|Static column suppression/scaling is directly relevant. The authors report both resolved and newly introduced loops; a detector exit or natural stop alone is not task success. Different models and decoding prevent importing the headline gain.|
|[Steer2Edit](https://arxiv.org/html/2602.09870v3)|First 10 February 2026; v3 4 November 2026|Converts contrastive steering into component-level fixed edits. Its accuracy/length tradeoff is not accuracy preservation at every dose. Our sparse protected-selector fit is a separate restricted construction, not a full replication.|
|[Where Do Distilled Students Store Thinking?](https://arxiv.org/html/2611.04141)|First 3 November 2026|Removals in distilled LoRA updates can resemble matched random directions. This motivates controls and caution about marker counts. Their adapter-span controls differ from our ambient orthogonal random output vector.|
|[Inherited, Not Invented: Tracing the Provenance of Wait in Reasoning Models](https://arxiv.org/abs/2610.30882)|First 22 October 2026|Reflective markers and actual repair behavior can disagree. This motivates checking state changes and proof validity rather than treating a word count as reasoning quality.|
|[Reflection Steering](https://arxiv.org/html/2608.25542v1)|First 26 August 2026|A raw contrast can mix reflection, reasoning and position. Its runtime projection does not automatically compile into a sparse MLP weight edit. Our productive-response penalty is a proxy, not a discovered reasoning subspace.|
|[The Structure of Quantization Damage in LLMs](https://arxiv.org/abs/2609.01587)|First 1 September 2026|Local weight statistics need not identify a causal repair target. This supports auditing the realized perturbation, not assuming that quantization caused the observed loop.|
|[ThinkEdit](https://aclanthology.org/2025.emnlp-main.861/)|EMNLP,November 2025|Attention-output weight editing is relevant precedent, but the target was overly short thinking. Blindly minimizing length would invert that lesson.|

## Tested local hypotheses

The progress-aware selector uses authored correction/circular pairs, matched rechecking language, tokenwise input penalties and equal-pair weighting. Its success criterion is a completed correct answer plus proof review, not low selector loss. The observed refitted-selector failure makes that distinction concrete.

The EOS and closing-marker variants protect a few **mean local raw-logit gradients** on authored captures. They do not protect each token, probability, output-token gap or propagation through the final block. Their later restoration of particular finalization behavior does not prove that the proxy diagnosed its cause.

Fixed-temperature sampling and numerical representation remain part of the experiment. A small logit shift can change top-k/top-p support at the established temperature 1.3. That possibility is not a reason to retune the temperature in this comparison, and no teacher-forced full-vocabulary causal sampler audit is claimed here.

## Sources found after the candidates were frozen

[The Halt Vector](https://arxiv.org/html/2608.28859v1), first 28 August 2026, was checked later during the run, after the relevant candidate vectors were frozen. Its full-representation reconstruction result suggests that a few local gradient constraints may be too weak. It did not determine these frozen edits and has not been implemented or reproduced here.

[The Shape of Overthinking](https://arxiv.org/abs/2605.27965), first 27 May 2026, distinguishes useful local repairs from persistent later backtracking. This supports future segment annotation; the experiment does not reproduce its annotator or early-exit method.

[Overthinking: Amplifying Reasoning Weights to Extract Learned Secrets](https://arxiv.org/html/2607.08173v1), first 9 July 2026, uses a paired instruct/reasoning checkpoint construction unavailable in this local setup. Its target is model auditing through extraction of learned information, rather than the present repetition task. It remains related work, not a tested task vector.

Next experiments should use independent correction/circular examples, stronger matched random controls, same-history numerical audits and downstream transport/reconstruction constraints. Those are research suggestions, not results of the present pilot.
