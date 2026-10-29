# 06 League-wise performance report (generated 2026-10-20 23:25)

Groups were fixed a priori from the competition id and tier: G1 top-5 European leagues; G2 other European tier-1; G3 European tier-2; G4 European tier-3 and below; G5 non-European leagues. Calendar-year leagues are reported separately (secondary sets). Full tables: `06a_LEAGUE_WISE_METRICS.csv`, `06b_LEAGUE_GROUP_METRICS.csv`, `06c_LEAGUE_WISE_LOGREG_VS_BASELINES.csv`.

## League groups, primary sets (split-year leagues)
| set | league_group | n_multinomial_logreg | accuracy_always_home | accuracy_elo_ordered_logit | accuracy_multinomial_logreg | log_loss_always_home | log_loss_elo_ordered_logit | log_loss_multinomial_logreg |
|---|---|---|---|---|---|---|---|---|
| forward_holdout_primary | G1 top-5 European leagues | 2002 | 0.4391 | 0.5130 | 0.5120 | 1.0723 | 0.9952 | 0.9969 |
| forward_holdout_primary | G2 other European tier-1 | 1077 | 0.4234 | 0.5116 | 0.5135 | 1.0777 | 0.9884 | 0.9889 |
| forward_holdout_primary | G3 European tier-2 | 647 | 0.4158 | 0.4312 | 0.4127 | 1.0831 | 1.0611 | 1.0627 |
| forward_holdout_primary | G5 non-European leagues | 2044 | 0.4521 | 0.4917 | 0.4927 | 1.0743 | 1.0230 | 1.0091 |
| test_primary | G1 top-5 European leagues | 1750 | 0.4206 | 0.5286 | 0.5286 | 1.0788 | 0.9853 | 0.9846 |
| test_primary | G2 other European tier-1 | 6658 | 0.4338 | 0.5246 | 0.5251 | 1.0739 | 0.9826 | 0.9818 |
| test_primary | G3 European tier-2 | 1398 | 0.4492 | 0.4621 | 0.4692 | 1.0694 | 1.0495 | 1.0482 |
| test_primary | G4 European tier-3+ | 3273 | 0.4247 | 0.4549 | 0.4610 | 1.0783 | 1.0585 | 1.0520 |
| test_primary | G5 non-European leagues | 2566 | 0.4330 | 0.4945 | 0.4918 | 1.0792 | 1.0125 | 1.0095 |

## Calendar-year leagues (secondary sets, never pooled with the primary metric)
| set | league_group | n_multinomial_logreg | accuracy_always_home | accuracy_elo_ordered_logit | accuracy_multinomial_logreg | log_loss_always_home | log_loss_elo_ordered_logit | log_loss_multinomial_logreg |
|---|---|---|---|---|---|---|---|---|
| forward_holdout_secondary_calendar_year | G5 non-European leagues | 570 | 0.4614 | 0.5228 | 0.5193 | 1.0665 | 0.9997 | 0.9921 |
| test_secondary_calendar_year | G2 other European tier-1 | 1027 | 0.4391 | 0.5307 | 0.5190 | 1.0707 | 0.9836 | 0.9823 |
| test_secondary_calendar_year | G5 non-European leagues | 2422 | 0.4591 | 0.4633 | 0.4732 | 1.0687 | 1.0350 | 1.0296 |

## Leagues with at least 100 evaluated matches - logistic regression, test primary, ordered by log loss
| competition_id | n | accuracy | log_loss_logreg | log_loss_elo | log_loss_home | delta_vs_elo |
|---|---|---|---|---|---|---|
| europe/gibraltar:gi1 | 125 | 0.6800 | 0.7807 | 0.8135 | 1.0467 | -0.0328 |
| europe/andorra:ad1 | 125 | 0.6800 | 0.7836 | 0.8072 | 1.0674 | -0.0236 |
| europe/bosnia-herzegovina:ba1 | 188 | 0.6489 | 0.8644 | 0.8609 | 1.0572 | 0.0035 |
| world/africa:tz1 | 223 | 0.6054 | 0.8722 | 0.8759 | 1.0500 | -0.0037 |
| europe/czech-republic:cz1 | 235 | 0.6128 | 0.8896 | 0.8868 | 1.0602 | 0.0028 |
| europe/armenia:am1 | 154 | 0.5909 | 0.8983 | 0.9158 | 1.0595 | -0.0174 |
| europe/luxembourg:lu1 | 224 | 0.5982 | 0.9049 | 0.9135 | 1.0643 | -0.0087 |
| europe/san-marino:sm1 | 240 | 0.5792 | 0.9167 | 0.9149 | 1.0913 | 0.0019 |
| europe/portugal:pt1 | 306 | 0.5490 | 0.9444 | 0.9402 | 1.0758 | 0.0042 |
| europe/cyprus:cy1 | 226 | 0.5929 | 0.9462 | 0.9431 | 1.0604 | 0.0031 |
| europe/russia:ru1 | 230 | 0.5565 | 0.9500 | 0.9493 | 1.0759 | 0.0007 |
| europe/netherlands:nl1 | 306 | 0.5261 | 0.9636 | 0.9615 | 1.0663 | 0.0021 |
| europe/france:fr1 | 305 | 0.5475 | 0.9668 | 0.9702 | 1.0550 | -0.0033 |
| world/africa:ug1 | 229 | 0.5502 | 0.9693 | 0.9716 | 1.0731 | -0.0023 |
| europe/scotland:sco1 | 228 | 0.5219 | 0.9711 | 0.9666 | 1.0540 | 0.0044 |
| italy:1-seriea | 380 | 0.5237 | 0.9738 | 0.9772 | 1.0917 | -0.0035 |
| world/north-america:mx1 | 306 | 0.5654 | 0.9743 | 0.9727 | 1.0529 | 0.0017 |
| espana:1-liga | 380 | 0.5526 | 0.9776 | 0.9729 | 1.0704 | 0.0047 |
| world/africa:ma1 | 190 | 0.5211 | 0.9788 | 0.9807 | 1.0814 | -0.0020 |
| europe/azerbaijan:az1 | 170 | 0.5294 | 0.9797 | 0.9751 | 1.0927 | 0.0046 |
| europe/greece:gr1 | 219 | 0.5205 | 0.9879 | 0.9860 | 1.0736 | 0.0019 |
| england:1-premierleague | 380 | 0.5211 | 0.9898 | 0.9910 | 1.0830 | -0.0011 |
| europe/wales:wal1 | 182 | 0.5330 | 0.9898 | 0.9851 | 1.0632 | 0.0047 |
| world/africa:gh1 | 278 | 0.5396 | 0.9935 | 1.0045 | 1.0247 | -0.0110 |
| europe/serbia:rs1 | 283 | 0.4982 | 1.0048 | 1.0068 | 1.0755 | -0.0020 |
| belgium:be1 | 307 | 0.5179 | 1.0049 | 1.0042 | 1.0748 | 0.0007 |
| europe/ukraine:ua1 | 225 | 0.5156 | 1.0061 | 0.9987 | 1.0897 | 0.0075 |
| europe/slovenia:si1 | 171 | 0.5322 | 1.0089 | 1.0021 | 1.0839 | 0.0068 |
| europe/kosovo:kos1 | 171 | 0.4737 | 1.0098 | 1.0148 | 1.0604 | -0.0050 |
| world/middle-east:il1 | 229 | 0.4934 | 1.0175 | 1.0145 | 1.0891 | 0.0030 |
| deutschland:4-regionalliga-suedwest | 262 | 0.5153 | 1.0177 | 1.0383 | 1.0561 | -0.0206 |
| deutschland:1-bundesliga | 305 | 0.4951 | 1.0182 | 1.0189 | 1.0918 | -0.0006 |
| england:3-league1 | 552 | 0.4909 | 1.0206 | 1.0190 | 1.0735 | 0.0016 |
| europe/north-macedonia:mk1 | 177 | 0.4746 | 1.0256 | 1.0329 | 1.0843 | -0.0072 |
| europe/northern-ireland:nir1 | 223 | 0.4843 | 1.0290 | 1.0212 | 1.0647 | 0.0078 |
| europe/croatia:hr1 | 175 | 0.4514 | 1.0331 | 1.0467 | 1.0765 | -0.0136 |
| world/africa:rw1 | 236 | 0.4746 | 1.0333 | 1.0369 | 1.0865 | -0.0036 |
| europe/slovakia:sk1 | 187 | 0.4866 | 1.0335 | 1.0406 | 1.0882 | -0.0071 |
| europe/france:fr2 | 301 | 0.5083 | 1.0362 | 1.0311 | 1.0507 | 0.0051 |
| europe/hungary:hu1 | 189 | 0.4656 | 1.0369 | 1.0350 | 1.0834 | 0.0019 |
| world/africa:zm1 | 292 | 0.4315 | 1.0403 | 1.0470 | 1.0963 | -0.0068 |
| austria:2-liga2 | 239 | 0.4979 | 1.0406 | 1.0632 | 1.0705 | -0.0227 |
| england:2-championship | 552 | 0.4620 | 1.0412 | 1.0376 | 1.0686 | 0.0036 |
| deutschland:4-regionalliga-nordost | 268 | 0.4776 | 1.0433 | 1.0575 | 1.0695 | -0.0142 |
| europe/poland:pl1 | 293 | 0.4676 | 1.0452 | 1.0417 | 1.0628 | 0.0035 |
| england:5-nationalleague | 547 | 0.4589 | 1.0494 | 1.0493 | 1.0822 | 0.0002 |
| deutschland:3-liga3 | 370 | 0.4892 | 1.0541 | 1.0517 | 1.0657 | 0.0024 |
| europe/switzerland:ch1 | 228 | 0.4912 | 1.0567 | 1.0543 | 1.0593 | 0.0024 |
| europe/romania:ro1 | 265 | 0.4453 | 1.0573 | 1.0550 | 1.0910 | 0.0023 |
| europe/montenegro:me1 | 169 | 0.4497 | 1.0617 | 1.0597 | 1.0958 | 0.0020 |
| deutschland:4-regionalliga-west | 201 | 0.4279 | 1.0645 | 1.0928 | 1.0947 | -0.0284 |
| europe/malta:mt1 | 182 | 0.4725 | 1.0688 | 1.0694 | 1.0955 | -0.0007 |
| england:4-league2 | 552 | 0.4384 | 1.0745 | 1.0746 | 1.0833 | -0.0001 |
| deutschland:4-regionalliga-nord | 261 | 0.4215 | 1.0750 | 1.0991 | 1.0828 | -0.0242 |
| world/africa:ke1 | 301 | 0.4053 | 1.0762 | 1.0832 | 1.1095 | -0.0070 |
| deutschland:2-bundesliga2 | 306 | 0.4216 | 1.0787 | 1.0785 | 1.0884 | 0.0002 |
| deutschland:4-regionalliga-bayern | 260 | 0.4038 | 1.0835 | 1.0917 | 1.1013 | -0.0082 |
| europe/albania:al1 | 170 | 0.3882 | 1.0961 | 1.1004 | 1.1005 | -0.0043 |
| world/africa:sn1 | 213 | 0.3380 | 1.1251 | 1.1256 | 1.1276 | -0.0005 |

## Same, forward holdout primary
| competition_id | n | accuracy | log_loss_logreg | log_loss_elo | log_loss_home | delta_vs_elo |
|---|---|---|---|---|---|---|
| world/africa:tz1 | 234 | 0.5855 | 0.8912 | 0.8924 | 1.0700 | -0.0011 |
| europe/portugal:pt1 | 306 | 0.5621 | 0.9301 | 0.9297 | 1.0827 | 0.0004 |
| world/africa:ng2 | 176 | 0.6875 | 0.9449 | 0.9767 | 0.9722 | -0.0318 |
| world/africa:ug1 | 224 | 0.5402 | 0.9525 | 0.9585 | 1.0812 | -0.0060 |
| deutschland:1-bundesliga | 342 | 0.5409 | 0.9639 | 0.9624 | 1.0675 | 0.0015 |
| world/africa:ng1 | 326 | 0.6288 | 0.9642 | 0.9991 | 0.9964 | -0.0349 |
| europe/netherlands:nl1 | 363 | 0.5207 | 0.9754 | 0.9714 | 1.0802 | 0.0040 |
| espana:1-liga | 449 | 0.5189 | 0.9765 | 0.9755 | 1.0546 | 0.0010 |
| italy:1-seriea | 430 | 0.5302 | 0.9908 | 0.9912 | 1.0885 | -0.0003 |
| europe/france:fr1 | 351 | 0.5100 | 1.0055 | 1.0021 | 1.0667 | 0.0035 |
| world/africa:zm1 | 299 | 0.4314 | 1.0340 | 1.0434 | 1.0838 | -0.0094 |
| england:1-premierleague | 430 | 0.4651 | 1.0436 | 1.0402 | 1.0831 | 0.0034 |
| austria:1-bundesliga | 234 | 0.4444 | 1.0584 | 1.0632 | 1.0717 | -0.0048 |
| england:2-championship | 647 | 0.4127 | 1.0627 | 1.0611 | 1.0831 | 0.0016 |
| world/africa:rw1 | 257 | 0.3969 | 1.0696 | 1.0756 | 1.1073 | -0.0060 |
| world/africa:sn1 | 233 | 0.3348 | 1.0902 | 1.1134 | 1.1494 | -0.0231 |
| world/africa:ke1 | 295 | 0.3864 | 1.0913 | 1.0917 | 1.1221 | -0.0004 |

## Reading the tables
* Predictability falls with tier: the top-5 and other tier-1 leagues have log loss about 0.98-1.00, tier-2 about 1.05-1.06, lower tiers up to 1.06; the non-European and calendar-year leagues sit in between.
* Per-league samples of 100-400 matches carry large sampling error (a log-loss standard error of about 0.02-0.04); differences of a few hundredths between leagues are not significant.
* The logistic regression and the Elo mapping are almost indistinguishable in every group; the largest advantage of the logistic regression appears in non-European leagues on the holdout.
