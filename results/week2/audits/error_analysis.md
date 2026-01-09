# Error Analysis Report

**Threshold**: 0.5
**Top-K per label**: 20

## VAL Split

### adhd
- False Positives: 152
- False Negatives: 152
- Top FP IDs: ognistyptak555:rl4f27, Ok_Seaworthiness3555:jfnwuj, Distant_Past:q4ut7d, liazluc:r1qthv, herrwaldos:pnnp2t
- Top FN IDs: SuperTriniGamer:q381tl, h3110sunshine:r59fzk, Salt_Ninja_6298:qtoxoi, lizzrman:qti1wo, Meadowlie:qx3aq6

### depression
- False Positives: 155
- False Negatives: 186
- Top FP IDs: Jeetujayson:e7qed9, maybetheresagodabove:gml82j, lizzrman:qti1wo, achodeisstilladick:rka6se, Meadowlie:qx3aq6
- Top FN IDs: achilleschant:rdq1iy, PatsyWoodTipCline:qtb41p, Fantastic_Dot9288:r8sb61, subiacOSB:rbbevp, John_Wick_550:rkfcod

### ocd
- False Positives: 50
- False Negatives: 132
- Top FP IDs: SherlockPhonesIII:oj6i22, kojima-:relugj, captainmixtape:r46v40, Chemical-Ad3703:rgra6p, ForestNymph320:nlzg2c
- Top FN IDs: boopityboop8:nkp767, nonliberalelite:pn5lw3, georgegetsmoney:mmips9, askkorial:rbc0vj, magoogafool:qw9jnd

### other
- False Positives: 90
- False Negatives: 122
- Top FP IDs: moleskineandpen:pqlkev, Numb_Loch:m6tjrh, dinasum732:ndmvt5, Disastrous-Whale564:qvemki, MummaGoose:dcyt44
- Top FN IDs: IcarusKiki:psb5fq, jmldmk:p6rcuz, jarbyj:nnegqq, AConflictedMan:nefh15, MaineCoinMeow:psdvv9

### ptsd
- False Positives: 71
- False Negatives: 143
- Top FP IDs: gg2ezpzlemonsqz:rgxk54, John_Wick_550:rkfcod, __Opal_:r5fj75, nonliberalelite:pn5lw3, Deidric_Bane:rizlb1
- Top FN IDs: Discodiscodiscodisco:jb70ak, AislingAshbeck:pvw8a4, aweirdnobody:q8ew6b, the_official_phrique:pn0bi1, anonlolo:qg0d2m

### Confusion Patterns

When label X is missed, which other labels were present:

- depression: [('adhd', 17), ('ptsd', 9), ('ocd', 3)]
- ptsd: [('adhd', 13), ('ocd', 9), ('depression', 7)]
- adhd: [('ptsd', 6), ('ocd', 6), ('depression', 4)]
- ocd: [('depression', 7), ('adhd', 5), ('other', 5)]
- other: [('adhd', 6), ('ocd', 4), ('ptsd', 2)]

## TEST Split

### adhd
- False Positives: 131
- False Negatives: 153
- Top FP IDs: Mini_Squatch:qhsot5, vampie-cat:q82t2d, mirrorhouse:oyu50v, Shenina:f1md34, Yodalfree:rb27dh
- Top FN IDs: Wonderful-Otter84:qakl0d, Forsaken_Salt_3066:que0mf, MianadOfDiyonisas:q0y0di, throw-away-sad-sack:r6t00i, MadamJules:q5c2x7

### depression
- False Positives: 151
- False Negatives: 179
- Top FP IDs: Substantial-You-7180:ol8qsa, Far_n_Away:fs292n, throwaway4788432709:iy3ulq, MyBrainsInPain:ph71mw, imsosadplshelp:o8esr1
- Top FN IDs: Imyours002:r2x5k3, udidthis2me:qw5vjj, Juice_Freak:qvi8qm, PotatoPancake73:rijeu3, senioritissss:ri0jrq

### ocd
- False Positives: 65
- False Negatives: 122
- Top FP IDs: scrapie22:p00bsx, MianadOfDiyonisas:q0y0di, nightmarepinster:qso4ms, Forsaken_Salt_3066:que0mf, Wattsherfayce:o5r26e
- Top FN IDs: Choice_Shine6175:nmvitj, IveGotIssues9918:m603hv, JackfruitOk6600:nde7ci, time_fo_that:qpk4ci, snozkat:qmom8c

### other
- False Positives: 86
- False Negatives: 156
- Top FP IDs: ellieisherenow:r5ole0, endrrslime:quiru1, Bumiller:qrtq1q, RealCryptographer205:qwvdx9, Herge2020:r7twaa
- Top FN IDs: Sayonara_1818:pgf9y2, Mini_Squatch:qhsot5, Matrixblackhole:lj580y, Alesoria:onbke3, vampie-cat:q82t2d

### ptsd
- False Positives: 69
- False Negatives: 130
- Top FP IDs: lilnasery:oepg3v, Senorita27:rmctqs, Proseteacher:o2101t, rbr55:prooke, Ambitious-Address979:pti3su
- Top FN IDs: february_friday:iwgtfe, Sagafreyja:pqzm3u, dsc203:hf5ct6, wsupdoggo:drrg5t, Mylifeis-hell:kq291q

### Confusion Patterns

When label X is missed, which other labels were present:

- depression: [('adhd', 10), ('ocd', 10), ('other', 9)]
- ptsd: [('ocd', 11), ('other', 5), ('adhd', 3)]
- adhd: [('ptsd', 4), ('depression', 3), ('other', 2)]
- ocd: [('other', 13), ('adhd', 8), ('depression', 3)]
- other: [('adhd', 8), ('ocd', 5), ('depression', 4)]

## Common Themes

- val/adhd: High FN count (152)
- val/adhd: High FP count (152)
- val/depression: High FN count (186)
- val/depression: High FP count (155)
- val/ocd: High FN count (132)
- val/other: High FN count (122)
- val/other: High FP count (90)
- val/ptsd: High FN count (143)
- val/ptsd: High FP count (71)
- test/adhd: High FN count (153)
- test/adhd: High FP count (131)
- test/depression: High FN count (179)
- test/depression: High FP count (151)
- test/ocd: High FN count (122)
- test/ocd: High FP count (65)
- test/other: High FN count (156)
- test/other: High FP count (86)
- test/ptsd: High FN count (130)
- test/ptsd: High FP count (69)
