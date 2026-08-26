# Resumable 100-Question G2 Failure Audit

## Scope

This is the optimized-8B low-resource baseline running the official G2 online
Planning Graph, Worker, sufficiency, refinement, and synthesis path. It is not
silently relabeled as the original 32B baseline. Suspected failures require
trace inspection and, where feasible, teacher validation.

## Live status

- Updated Unix time: `1787701948.175`
- Graphs complete: **100/100**
- Queries complete: **98/100**
- Queries currently failed after retries: **2**
- Parsed predictions missing: **18**
- Strict normalized exact matches: **5**
- Mean newly built graph time: **160.85 s**
- Mean completed query time: **71.82 s**

Strict string matching is only a triage signal. Long-form semantic correctness
and failure attribution are determined from the complete traces after execution.

## Preliminary review queue

- `spiqa_58`: pred="The filter generation module creates context-sensitive filters by encoding the input sentence into a fixed-length vector and generating filters via a deconvolutional layer. The convolution module then uses these filters to adaptively encode the input sentence, enabling adaptation to different sentences because the filters are sample-specific and context-dependent."; reference="The ACNN framework learns context-sensitive filters through two modules: the filter generation module and the adaptive convolution module. The filter generation module produces a set of filters conditioned on the input sentence, while the adaptive convolution module applies the generated filters to an input sentence. The two modules are jointly differentiable, and the overall architecture can be trained in an end-to-end manner."
- `spiqa_108`: pred="ESMM-NS and ESMM outperform all other models at every sampling rate for both CVR and CTCVR tasks."; reference="ESMM-NS and ESMM outperform all other models consistently across different training set sizes on both the CVR and CTCVR tasks."
- `spiqa_378`: pred="DLA achieved the highest scores with nDCG@10 = 0.421 and ERR@10 = 0.582, representing improvements of 0.063 and 0.082 over the NoCorrect baseline, respectively."; reference="The DNN trained with DLA achieved the best performance in terms of both nDCG@10 (0.421) and ERR@10 (0.582). Compared to not using any correction method (NoCorrect), DLA shows a significant improvement in both metrics, with nDCG@10 being higher by 0.063 and ERR@10 being higher by 0.082."
- `spiqa_48`: pred="GeoCUTS performs comparably to both DMA and Grid for highly active users, as all three have identical B-metric values of 1.5."; reference="GeoCUTS performs comparably to other clusterings for highly active users."
- `spiqa_39`: pred=null; reference="TRPO generally converges faster to the true gradient than PPO."
- `spiqa_37`: pred="The QoU and IoU decoys are designed to eliminate selection bias by ensuring that the correct answer and decoys are equally likely to be selected based on either the question or the image alone, forcing the model to integrate both modalities to make correct predictions. QoU-decoys are generated from triplets with similar questions, making them linguistically plausible without relying on visual context. IoU-decoys are generated from other triplets of the same image, making them visually plausible without relying on question context. This design prevents models from exploiting shortcuts based on either modality alone, thereby requiring them to combine both image and question information for accurate answers."; reference="The shortcuts in the Visual7W dataset can be remedied by creating alternative decoys that are more likely to be correct, based on either the image or the question alone. This forces the machine to consider all of the information together in order to select the correct answer."
- `spiqa_4`: pred="16198"; reference="There are approximately 9,719 negative samples in the training set of the CNSE dataset."
- `spiqa_234`: pred="For both r-RNTNs and RNTNs, increasing K from 1 to 10000 causes the test PPL to decrease significantly from around 150 to approximately 128.8, with minimal further improvement after K=100."; reference="The test PPL of all the models decreases as K increases."
- `spiqa_110`: pred=null; reference="The performance of LSTNet-attn generally improves as the horizon increases on the Solar-Energy dataset. This is evident from the fact that both the RMSE and correlation values improve with increasing horizon."
- `spiqa_196`: pred="The proximity of sentence embeddings reflects semantic similarity because the model learns high-level structure, causing semantically similar sentences to cluster together in the embedding space, regardless of their position in the document. The color-coding by position is a visual aid to show document structure, not semantic similarity."; reference="Sentences that are closer together in the embedding space are more semantically similar than those that are farther apart."
- `spiqa_337`: pred="ZDDA leverages the task-irrelevant gray-RGB pairs from Fashion-MNIST by training a joint network supervised by the digit classification task in the source domain (gray scale), which learns to simulate the target-domain (RGB) representation, enabling classification in the RGB domain without access to task-relevant RGB training data."; reference="The task-irrelevant data is used to simulate the RGB representation using the gray scale image. This allows ZDDA to learn a joint network that can be used to classify digits in both the gray scale and RGB domains."
- `spiqa_338`: pred="The temperature t scales the exponentiation of the similarity score in the unnormalized distribution by $1/t$, reducing the acceptance probability of suboptimal solutions as t decreases over time, thereby shifting the search from exploration to exploitation."; reference="The temperature variable t controls the probability of accepting a new candidate solution y. As t decreases, the probability of accepting a worse solution decreases."
- `spiqa_172`: pred="YTF, 31.9%"; reference="The gRCC* algorithm achieved the largest relative improvement over the RCC algorithm on the YTF dataset, with a relative improvement of approximately 31.9%."
- `spiqa_145`: pred="Figure 6 demonstrates that accurate visual grounding requires perfect alignment between the selected concept, predicted common concept, and the real entity. When all concepts align (e.g., first row with \"headlight\"), the heatmap accurately localizes the entity. When alignment is poor (e.g., fourth row with \"lighter\" misaligned with \"meal\"), the heatmap is inaccurate, showing that alignment directly determines heatmap quality."; reference="When the selected concept, predicted concept, and the real entity to be grounded are all aligned, the generated heatmap produces a good localization of the phrase."
- `spiqa_181`: pred="The embedded vector $E$ from the part encoding network and the generated mask $G_{\\mathcal{M}}(x)$ from the mask prediction network."; reference="The inputs to the image generation network are the observed images (x) and a random noise vector (z)."
- `spiqa_156`: pred="DMRNet has a lower training loss than ResNet."; reference="The training loss of DMRNet is lower than that of ResNet on the CIFAR-10 dataset with L = 30."
- `spiqa_461`: pred="COPA demonstrates faster performance than Helwig on both the CHOA and CMS datasets, with Helwig failing on CMS due to memory constraints at R=40, while COPA successfully completed iterations."; reference="COPA is faster than Helwig."
- `spiqa_381`: pred=null; reference="The VIDXL dataset contains the most interactions (events) in the training set with 69,312,698 events. This is roughly 7.7 times larger than the RSC15 dataset, which has the least interactions (9,011,321) in the training set. "
- `spiqa_368`: pred=null; reference="The most effective attack method at reducing the accuracy of the Resnet-32 model on the MNIST dataset is BIM/CE."
- `spiqa_0`: pred="Figure 9 illustrates the transformation by reorganizing the original Subject-Predicate-Object structure into a pre-processed format where POI properties are inverted or restructured to link entities, facilitating better disentanglement of language and knowledge."; reference=" \n\nThe pre-processed SMD Navigate data combines all the properties (such as distance, address) of a point of interest (POI) into a single subject with the object being \"poi\". The original data had separate entries for each property. "
- `spiqa_119`: pred="Yes"; reference="The PE-N=5 sampler performs better than the HMC sampler."
- `spiqa_586`: pred="GroundSent-Both achieves the highest accuracy on the MRPC task, surpassing the ST-LN model by 1.3 points."; reference="GroundSent-Cap appears to be most beneficial for the MRPC task, achieving an accuracy of 72.9/82.2 compared to the baseline model ST-LN's 69.6/81.2."
- `spiqa_245`: pred=null; reference="The Hamilton-based PCB is the electronic control board of the anemometer. It houses the microcontroller, sensors, and other electronic components that are necessary for the anemometer to function."
- `spiqa_130`: pred="The predicted mean return decreases to a minimum at θ = 0.5, and the uncertainty is highest at this point."; reference="The predicted return decreases as θ increases, with a minimum at around θ = 0.5."
- `spiqa_527`: pred="KEHNN achieves the highest scores across all four metrics (R2@1: 0.786, R10@1: 0.460, R10@2: 0.591, R10@5: 0.819), and its superiority is justified by statistically significant performance gains (p-value ≤ 0.01) and alignment with the paper's findings that LSTM-based models and models incorporating multiple channels and prior knowledge perform better."; reference="The KEHNN model performs the best for response selection. This is evident because it achieves the highest scores across all metrics (R$2$@1, R${10}$@1, R${10}$@2, and R${10}$@5) compared to all other models in the table."
- `spiqa_434`: pred="No method achieves 77.4% accuracy for Italian data in the provided figures."; reference="Variational J^var (7)"
- `spiqa_135`: pred="The proposed method is more accurate in generating different hair colors when facial attributes are swapped compared to icGAN."; reference="The proposed method is able to generate images with different hair colors more accurately than icGAN."
- `spiqa_522`: pred=null; reference="The Conv-KNRM model performs best when trained on the NYT dataset and evaluated on the WT14 dataset, achieving an nDCG@20 score of 0.3215. This performance is significantly better than all the baselines: BM25 (B), WT10 (W), and AOL (A)."
- `spiqa_392`: pred="HUMBI"; reference="MPII-Gaze"
- `spiqa_215`: pred="The depth-exclusive model (Fig. 1b) produces cleaner, silhouette-based filter responses in conv1, conv2, and conv3, which are more robust to appearance changes, compared to the RGB-based model (Fig. 1a) that shows complex, texture-dependent patterns sensitive to lighting and clothing."; reference="The filter responses from the “conv1”, “conv2” and “conv3” layers for a given frame from the TUM GAID data using a framework for person re-identification from RGB are more detailed and contain more information than the filter responses from the fCNN of a framework that utilizes depth data. This is because RGB images contain more information than depth images."
- `spiqa_36`: pred="The telescoping architecture implements the rank-and-prune process by sequentially applying ranking and pruning at stages L1 and L2. After documents are matched in L0, they are passed to L1 for initial ranking and pruning, and then to L2 for a subsequent re-ranking and pruning, refining the candidate set at each stage."; reference="Documents are first matched using a pre-defined match plan. Then, they are passed through additional rank-and-prune stages, which are implemented as a cascade of machine learning models."
- `spiqa_44`: pred="The only correct answer is that COPA correctly captures the temporal pattern with a sharp increase at the second visit, Helwig incorrectly suggests the condition was present at the first visit, and SPARTan produces a noisy, low-magnitude, non-periodic pattern that fails to capture the significant change."; reference="The temporal patterns of phenotype magnitude differ between sickle cell anemia and leukemia patients in terms of both shape and magnitude. For sickle cell anemia patients, the patterns are generally smoother and more periodic, with lower overall magnitude. For leukemia patients, the patterns are more erratic and have higher overall magnitude."
- `spiqa_396`: pred=null; reference="HUMBI performs best when used alone for training, with an average AUC of 0.399. While this is lower than the average AUC of models trained on combined datasets (0.433 for H36M+HUMBI and 0.413 for MI3D+HUMBI), HUMBI still achieves the highest score among the individual datasets."
- `spiqa_235`: pred="Increasing the budget in FLOPS reduces the test Top-1 error rates for both models, but the small ANN with adaptive loss weighting (AdaLoss, orange curve) consistently achieves lower error rates than the large ANN with non-adaptive weights (CONST, green curve) across all budget levels."; reference="The test Top-1 error rate decreases as the budget in FLOPS increases for all three training strategies."
- `spiqa_468`: pred="82.72, 1.11"; reference="The Conv. Self-Corr. method achieved the highest performance on the PASCAL VOC 2012 test set with a score of 82.72. This is approximately 1.11 points higher than the baseline model (\"No Self-Corr.\") which achieved a score of 81.61."
- `spiqa_73`: pred="US-BS-MQ achieves higher accuracy than S-MQ when more SST examples are incorporated."; reference="The US-BS-MQ method achieves higher accuracy than the S-MQ method when adding SST examples."
- `spiqa_205`: pred="In overlapping cases, the model correctly locates shared opinion words for multiple aspects, leading to accurate classification. In error cases, the model fails to correctly identify sentiment because it does not give sufficient attention to critical negation words, resulting in misclassification."; reference="An overlapping case is when multiple aspects share the same opinion snippet, while an error case is when the model incorrectly identifies an aspect or opinion."
- `spiqa_334`: pred="In RippleNet, a user's preferences are propagated iteratively through the knowledge graph via ripple sets. Starting from the user's click history (seeds), the 1-hop ripple set $S_u^1$ is generated by selecting all knowledge triples where the head entity is one of the clicked items. For each subsequent hop $k$ (up to $H$), the preference propagation is applied to the $k$-hop ripple set $S_u^k$ to generate the k-order response $\\mathbf{o}_u^k$ by computing a weighted average of tail embeddings. The final user embedding is formed by summing all order-specific responses: $\\mathbf{u} = \\mathbf{o}_u^1 + \\mathbf{o}_u^2 + \\ldots + \\mathbf{o}_u^H$. This embedding is then combined with the item embedding to predict the clicking probability."; reference="The ripple sets are used to propagate a user's preferences from his or her click history to his or her relevant entities."
- `spiqa_40`: pred="The proposed methods generate faces with significantly higher visual clarity and more detailed facial features than the baseline."; reference="The baseline method generates faces that are blurry and unrealistic, while the other methods generate faces that are more realistic."
- `spiqa_34`: pred="The improved detection accuracy provides better localization, which enhances tracking performance (AP, MOTA, MOTP) but also increases sensitivity to object movement, leading to more frequent identity switches (IDS)."; reference="While the model trained on both MOT and detection sets shows improved performance in detection and tracking metrics (AP, MOTA, MOTP), it also exhibits a higher number of identity switches (IDS). This can be attributed to the increased diversity of instances introduced by the detection set. Although the MOT set provides a larger number of bounding boxes for training, the detection set adds varied examples that may lead to more frequent identity switches during tracking, even as it improves the model's overall performance."
- `spiqa_116`: pred="The proposed RGB-to-Depth transfer method outperforms Yosinski et al. [90] by approximately 10 percentage points at x=7 in the right panel (finetuning scenario)."; reference="The proposed RGB-to-Depth transfer performs slightly better than Yosinski et al. [90] in terms of top-1 accuracy on DPI-T when all layers are fine-tuned."
- `spiqa_164`: pred="3"; reference="5 hops"
- `spiqa_281`: pred="The curve follows Luhn's hypothesis, which states that the norm is inversely proportional to the log frequency, with mid-rank terms being most significant."; reference="The $L_2$-norm of a word vector is inversely proportional to its frequency."
- `spiqa_452`: pred="ENet"; reference="TecoGAN."
- `spiqa_84`: pred="As average path length increases, classification error increases for both 3 and 6 residual block networks on CIFAR-10, with the 6-block network generally achieving lower error at shorter path lengths and showing a more gradual increase compared to the 3-block network."; reference="The classification error of a residual network generally increases as the average path length increases."
- `spiqa_52`: pred="Batching reduces both the radio duty cycle and the CPU duty cycle for TCP. Specifically, the radio duty cycle drops from 2.29% (No Batching) to 0.734% (Batching), and the CPU duty cycle drops from 0.973% (No Batching) to 0.30% (Batching)."; reference="Batching reduces both the radio duty cycle and CPU duty cycle."
- `spiqa_195`: pred=null; reference="The training curves for the ACGAN show that the generator and discriminator losses both decrease over time. This indicates that the ACGAN is able to learn to generate realistic images."
- `spiqa_578`: pred="SCHOLAR"; reference="The topic with the highest internal coherence value is \"turks armenian armenia turkish roads escape soviet muslim mountain soul\"."
- `spiqa_80`: pred="The average number of inter-word semantic connections per word increases monotonically from 0.39 at κ=0 to 5.58 at κ=5."; reference="The average number of inter-word semantic connections per word increases as the value of κ increases."
- `spiqa_212`: pred="In the two-level attention model, attention weights for \"rest_3_str\" and \"rating 3\" are more focused and selective, shown by darker shading in Figure 7a, compared to the one-level attention model (Figure 7b), where the weights are more diffuse and less selective, indicated by lighter shading."; reference=" The two-level attention model has higher attention weights on the relevant information in the memory, while the one-level attention model has more uniform attention weights."
- `spiqa_269`: pred="The second-stage decoder $D_2$ takes the soft edge maps $x_G$ as input to reconstruct the non-key frames ($X_G$). Its purpose is to reconstruct these frames using the soft edge maps, which contain only edge information, based on its training with key frames and their corresponding soft edge maps."; reference="The second-stage decoder $D_2$ takes soft edges $x_G$ as input and produces reconstructed frames."
- `spiqa_272`: pred=null; reference="The user study is designed to test which of two images is closer to a reference video."
- `spiqa_55`: pred=null; reference="Increasing the training set size generally leads to improved performance for both lane marking and drivable area segmentation tasks."
- `spiqa_18`: pred="FlowNet2 (ft) achieves a lower error (3.14) than Devon (ft) (6.35) on the Sintel \"Final\" test set."; reference="PWC-Net (ft) performs best on the Sintel \"Final\" test set with an error of 5.04. Devon (ft) has a higher error of 6.35 on the same set. "
- `spiqa_66`: pred="Bitmaps, encoded with semantic labels of places, are used as masks to isolate and extract features specific to each place, enabling the spatial decomposition of video representations into distinct place-based regions. This decomposition encourages the network to learn generic, layout-independent place-based features."; reference="The LIVR framework decomposes semantic features into different places by utilizing bitmaps encoded with the semantic labels of places. This decomposition encourages the network to learn features of generic place-based motion patterns that are independent of scene layouts."
- `spiqa_510`: pred=null; reference="The Transfer + MTSA model performed best on the SNLI test set with an accuracy of 86.9%."
- `spiqa_98`: pred=null; reference="As the maximum link delay increases, the segment loss rate increases and the goodput decreases."
- `spiqa_163`: pred="The Hilbert curve recursively subdivides a square into four smaller squares and applies the same pattern to each, but the specific drawing rule for the path within each subdivision is not described in the text or explicitly inferable from the visual pattern alone."; reference="The Hilbert space-filling curve is constructed recursively. The curve starts with a simple square, and then at each subsequent iteration, the curve is subdivided into four smaller squares. The curve is then drawn through each of these squares in a specific order."
- `spiqa_571`: pred=null; reference="Step 4, Reason disambiguation."
- `spiqa_440`: pred="EDVR"; reference="DUF"
- `spiqa_26`: pred=null; reference="No, adversarial examples generated with the 2-keyword constraint deviate significantly from the original syntactic structure."
- `spiqa_61`: pred=null; reference="The BDD100K dataset is significantly larger and more complex than both the KITTI and MOT17 datasets. It contains roughly 40 times more frames, 16 times more sequences, and 13 times more identities than KITTI. Compared to MOT17, BDD100K has about 10 times more frames, 80 times more sequences, and 8 times more identities. This increase in size and complexity makes BDD100K a more challenging and comprehensive benchmark for multiple object tracking algorithms. "
- `spiqa_47`: pred="GBI reduces the average disagreement rate by 19.93%, while A* reduces it by 10.94%. Therefore, GBI’s reduction is 8.99 percentage points greater than A*'s reduction."; reference="GBI is more effective than A* in reducing the disagreement rate on the SRL-100 network's failure set. After applying GBI, the average disagreement rate drops to 24.92%, while A* only reduces it to 33.91%. This represents an 19.93% greater reduction in disagreement rate when using GBI compared to A*."
- `spiqa_5`: pred="The warped triplets leverage motion information to improve frame alignment by providing the discriminator with cues about how frames should be temporally aligned, enabling it to guide the generator to produce more accurate and temporally coherent super-resolution results."; reference=" The warped triplets provide additional information about the motion and appearance of the scene, which helps the VSR Ds,t to generate more accurate and realistic results."
- `spiqa_249`: pred=null; reference="The key difference lies in the availability of target-domain training data. While UDA and MVL methods require T-R training data from the target domain, ZDDA does not. ZDDA only requires T-R training data from a single source domain."
- `spiqa_143`: pred="Consistency (average pairwise cosine similarity) improves with increasing state-action pairs for each method across different training iterations."; reference="The quality of gradient estimation increases as the number of state-action pairs used in estimation increases."
- `spiqa_67`: pred="The Mean-Shift algorithm maintains robustness to 50 outliers by iteratively shifting points toward regions of higher density in the parameter space, which naturally correspond to the true parameters (red dots). This density-based mode-seeking is reinforced by an energy minimization step that only accepts new modes if they do not increase the fit energy, favoring solutions that best explain the data. Finally, a post-processing validation step removes statistically insignificant models (likely outliers) by checking if the mean distance from inlier points to the estimated model is below a threshold, ensuring the final modes are robust and correspond to the true parameters."; reference="The Mean-Shift algorithm is robust to outliers."
- `spiqa_203`: pred="The dashed projection shortcuts in residual networks (a) enable gradients to bypass intermediate layers directly, preventing vanishing gradients. In contrast, inception-like networks (b) lack such shortcuts, forcing gradients to propagate through all layers, which constrains flow and increases vanishing gradient risk."; reference="Deep residual networks have skip connections that allow the gradient to flow directly from one layer to another, while networks built by stacking inception-like blocks do not."
- `spiqa_333`: pred="The residual connections provide a direct pathway for features to propagate from earlier layers to later layers, maintaining information flow and allowing gradients to flow more easily, which helps prevent vanishing gradients."; reference="The residual connections add the output of the previous layer to the input of the next layer. This helps to improve the flow of information through the network and can help to prevent vanishing gradients."
- `spiqa_137`: pred="identity-guided conditional CycleGAN"; reference="The proposed method utilizes Light-CNN as both the source of the identity features and face verification loss. This allows the method to transfer the appearance of eyes, eyebrows, hairs, etc., while keeping other factors intact, e.g., head pose, shape of face, and facial expression."
- `spiqa_347`: pred="20%"; reference="Approximately 80%"
- `spiqa_29`: pred=null; reference="The probability of repaying a debt increases with credit score."
- `spiqa_222`: pred="The predicted frames are more accurate than the reconstructed frames after the second training phase, as the prediction model produces \"perfectly\" accurate frames while the autoencoder generates \"slightly blurred\" frames. This is supported by both the text and the visual comparison in Image 1."; reference="The predicted frame is generated by the prediction model, while the reconstructed frame is generated by the autoencoder. The predicted frame is typically more accurate than the reconstructed frame, as the prediction model is trained to predict the future state of the environment, while the autoencoder is only trained to reconstruct the input image."
- `spiqa_223`: pred=null; reference="The representation module takes an input image and outputs a feature representation. The learning-to-learn module takes a set of features and learns how to segment the image."
- `spiqa_292`: pred="Not enough information is provided to answer the question, as the actual fixation counts in panel c and the predicted probability mass in panel b are not quantified in the text or trajectory insights."; reference="The fixation density map predicts the probability of a person fixating on a particular location in the image. The ground truth fixations are the actual locations where people fixated on the image."

## Durability and recovery

- `PROGRESS.json` is rewritten atomically after every state transition.
- `journal.jsonl` is append-only.
- Each question has independent build and query checkpoints.
- Failed partial outputs are moved to `failed_attempts/` before retry.
- Local VLM and embedding endpoints are health-checked and restarted.
- Re-running the same command skips every validated graph and query.

## Next analysis

After the run, every incorrect or suspicious answer will be classified as
retrieval, Worker-support, decomposition, composition, sufficiency, parser,
infrastructure, or unverifiable, with low-resource confounds recorded separately.

## Findings recorded during execution

### Gate case: `spiqa_542`

- The existing optimized-8B graph loaded correctly and the official online G2
  path returned the reference answer, `RCE`.
- The initial Worker had the decisive table in its context and could identify
  the `RCE = 0.77` row, but its response became distracted by a different
  high-confidence C&W-wb table containing `100, 100`.
- The round-0 sufficiency response began with `<check>` but was truncated before
  producing a complete parseable block. Official G2 therefore recorded
  `parsed=false`, treated the answer as insufficient, and refined globally.
- The run expanded to four Planning Graph executions, 13 Worker results, four
  sufficiency checks, and 22 recorded online model calls before returning the
  correct final answer.
- Cached-query time was 180.92 seconds. This is a confirmed parser/refinement
  efficiency failure, not a final-answer failure. Whether the same behavior is
  specific to the 8B model must remain a separate teacher-validation question.

### Early replay observations: `spiqa_540`, `spiqa_108`, and `spiqa_378`

- `spiqa_540` returned the correct `DMRNet` answer in this audit replay even
  though the earlier matched candidate-graph run answered that the result was
  unavailable. The graph, nominal model, and seed are the same. This is direct
  evidence of operational run-to-run variance; it does not erase the earlier
  failure.
- `spiqa_108` returned a semantically correct answer but used four Planning
  Graph executions, 14 Worker results, and 24 online model calls. This repeats
  the excessive-refinement symptom without repeating the previous missing
  final `</output>` parse failure.
- `spiqa_378` also returned a semantically correct answer, but used four
  Planning Graph executions and 22 online model calls. Three sufficiency-check
  responses were unparseable, so the official fallback repeatedly treated the
  evidence as insufficient.
- These are currently classified only as parser/refinement efficiency signals.
  Any claim that they are intrinsic original-32B G2 failures still requires a
  matched teacher replay.

### Reproducible Planning Graph serialization failures

- `spiqa_79` exhausted three complete query attempts. Within each attempt, all
  three DAG-generation rounds and five retries per round returned the same
  truncated JSON string (`Unterminated string`). No valid Planning Graph was
  produced, so the official online path raised `RuntimeError` before Worker
  execution.
- `spiqa_96` likewise exhausted three query attempts. Its generated Planning
  Graph repeatedly contained an invalid JSON backslash escape, and all DAG
  parser retries failed before Worker execution.
- Both graphs were built correctly, the VLM endpoint remained healthy, and
  subsequent questions continued. These are confirmed structured-output /
  Planning Graph serialization failures in this 8B configuration, not Content
  Graph construction, retrieval, or GPU failures.
- The frozen behavior has not been repaired during the audit. The failed cases
  remain available for later matched 32B replay and structured-output repair
  evaluation.

### Execution-phase completion

- The resumable SPIQA-100 pass completed on 2026-08-25. All **100 Content
  Graphs** were built; **98 online queries** produced complete trace/output
  artifacts, and the two Planning Graph serialization cases above exhausted
  their retries.
- Mean new Content Graph construction time was **160.85 seconds** and mean
  completed online-query time was **71.82 seconds** in this optimized-8B
  configuration.
- **18/98 completed queries** contain a nonempty raw final response but no
  parsed prediction. These are final-output parser candidates, not automatically
  18 incorrect raw answers.
- Behavior-neutral trace screening found **21** multi-refinement cases and
  **4** questions with intermediate sufficiency-parser signals. It generated
  review packets for **79** conservatively flagged questions.
- The 79 packets are a review queue, not an error count: lexical mismatch flags
  include semantically correct paraphrases. Causal error attribution and matched
  original-32B replay remain the next experiment phase.

## Post-hoc audit completion (2026-08-26)

The semantic, trace-based, matched-32B, and raw-image validation phases are now
complete. The source-grounded audit excludes five defective benchmark rows:
`spiqa_79`, `spiqa_164`, `spiqa_195`, `spiqa_281`, and `spiqa_452`.

- Corrected valid denominator: **95**
- Semantically correct parsed or recoverable raw 8B answers: **65/95**
- Incorrect/no-answer outcomes: **30/95**
- Correct raw answers lost by the final-output parser: **6**
- Corrected failure phenomena: Worker support **20**, parser **9**, retrieval
  **4**, decomposition **2**, composition **1**
- Matched 32B replays: **11/11** complete, **5/11** benchmark-semantically
  correct before raw-source correction, and **4** 8B-incorrect cases repaired

Raw visual review restored `spiqa_163` and `spiqa_215` as correct, identified
four question/reference defects, and corrected three causal labels. The full
source-grounded results are in `posthoc_adjudication/POSTHOC_REPORT.md` and
`posthoc_adjudication/visual_validation/VISUAL_VALIDATION.md`.
