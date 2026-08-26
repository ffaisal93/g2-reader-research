# Parser Recovery Inventory

Original G2 outputs are immutable. Recovery is recorded only in derived
artifacts and only when an explicit `<output>` tag lacks its closing tag.
Thought text is never silently promoted to an answer.

- Completed query outputs: **98**
- Officially parsed predictions: **80**
- Explicit unclosed outputs recovered: **10**
- No candidate answer recoverable: **8**

| Question | Derived status | Recovered candidate | Reference |
|---|---|---|---|
| `spiqa_39` | `derived_unclosed_output_tag` | TRPO maintains a higher cosine similarity with the true gradient at low state-action pair counts, implying more stable and efficient convergence due to better alignment with the true gradient direction. | TRPO generally converges faster to the true gradient than PPO. |
| `spiqa_110` | `derived_unclosed_output_tag` | As the forecasting horizon increases, the RMSE of the LSTNet-attn model increases while its correlation decreases. | The performance of LSTNet-attn generally improves as the horizon increases on the Solar-Energy dataset. This is evident from the fact that both the RMSE and correlation values improve with increasing horizon. |
| `spiqa_381` | `derived_unclosed_output_tag` | VIDXL has the highest number of interactions with 69,312,698, which is 7.690 times larger than CLASS, the dataset with the fewest interactions (9,011,321). | The VIDXL dataset contains the most interactions (events) in the training set with 69,312,698 events. This is roughly 7.7 times larger than the RSC15 dataset, which has the least interactions (9,011,321) in the training set.  |
| `spiqa_368` | `no_candidate_answer` |  | The most effective attack method at reducing the accuracy of the Resnet-32 model on the MNIST dataset is BIM/CE. |
| `spiqa_245` | `derived_unclosed_output_tag` | The Hamilton-based PCB enables data acquisition by housing the sensors that collect raw measurements and enables data transmission by implementing TCP/CoAP protocols to send the data to a server, but it does not perform the complex processing required to calculate air velocity. | The Hamilton-based PCB is the electronic control board of the anemometer. It houses the microcontroller, sensors, and other electronic components that are necessary for the anemometer to function. |
| `spiqa_522` | `no_candidate_answer` |  | The Conv-KNRM model performs best when trained on the NYT dataset and evaluated on the WT14 dataset, achieving an nDCG@20 score of 0.3215. This performance is significantly better than all the baselines: BM25 (B), WT10 (W), and AOL (A). |
| `spiqa_396` | `no_candidate_answer` |  | HUMBI performs best when used alone for training, with an average AUC of 0.399. While this is lower than the average AUC of models trained on combined datasets (0.433 for H36M+HUMBI and 0.413 for MI3D+HUMBI), HUMBI still achieves the highest score among the individual datasets. |
| `spiqa_195` | `no_candidate_answer` |  | The training curves for the ACGAN show that the generator and discriminator losses both decrease over time. This indicates that the ACGAN is able to learn to generate realistic images. |
| `spiqa_272` | `derived_unclosed_output_tag` | Participants are asked to choose which of the two images (A or B) is perceptually closer to the reference video. | The user study is designed to test which of two images is closer to a reference video. |
| `spiqa_55` | `derived_unclosed_output_tag` | Scaling the training set from 10K to 70K improves both ODS-F for lane marking (from 45.41 to 54.48) and IoU for drivable area segmentation (from 64.23 to 71.37), but the gains diminish after 20K, indicating diminishing returns. | Increasing the training set size generally leads to improved performance for both lane marking and drivable area segmentation tasks. |
| `spiqa_510` | `no_candidate_answer` |  | The Transfer + MTSA model performed best on the SNLI test set with an accuracy of 86.9%. |
| `spiqa_98` | `derived_unclosed_output_tag` | Both the segment loss rate and goodput decrease as the maximum link delay increases. | As the maximum link delay increases, the segment loss rate increases and the goodput decreases. |
| `spiqa_571` | `no_candidate_answer` |  | Step 4, Reason disambiguation. |
| `spiqa_26` | `no_candidate_answer` |  | No, adversarial examples generated with the 2-keyword constraint deviate significantly from the original syntactic structure. |
| `spiqa_61` | `derived_unclosed_output_tag` | BDD100K has a larger scale (318K frames, 1,600 sequences, 131K identities) and greater diversity (in object scale and occlusion) than KITTI (8K frames, 21 sequences, 917 identities) and MOT17 (34K frames, 21 sequences, 1,638 identities), making it more suitable for robust multiple object tracking. | The BDD100K dataset is significantly larger and more complex than both the KITTI and MOT17 datasets. It contains roughly 40 times more frames, 16 times more sequences, and 13 times more identities than KITTI. Compared to MOT17, BDD100K has about 10 times more frames, 80 times more sequences, and 8 times more identities. This increase in size and complexity makes BDD100K a more challenging and comprehensive benchmark for multiple object tracking algorithms.  |
| `spiqa_249` | `derived_unclosed_output_tag` | UDA and MVL have T-R target-domain training data available, while ZDDA does not. | The key difference lies in the availability of target-domain training data. While UDA and MVL methods require T-R training data from the target domain, ZDDA does not. ZDDA only requires T-R training data from a single source domain. |
| `spiqa_29` | `derived_unclosed_output_tag` | For both black and white groups, the probability of debt repayment increases with credit score. However, at every credit score level, the probability of repayment is lower for the black group compared to the white group. | The probability of repaying a debt increases with credit score. |
| `spiqa_223` | `no_candidate_answer` |  | The representation module takes an input image and outputs a feature representation. The learning-to-learn module takes a set of features and learns how to segment the image. |
