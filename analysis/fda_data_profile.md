# FDA Data Profile

- Labels: 704
- QA rows: 17207
- Task distribution: `{"factual": 9875, "multihop": 3398, "refusal": 3934}`

## Distributions

- Label chunk counts: `{"counts": {"0": 5, "1": 1, "10": 8, "100": 2, "101": 1, "102": 1, "103": 3, "104": 2, "105": 2, "106": 1, "107": 2, "108": 2, "109": 4, "11": 19, "110": 1, "111": 3, "112": 2, "113": 2, "114": 2, "115": 1, "117": 1, "118": 1, "119": 2, "12": 54, "120": 1, "122": 2, "125": 1, "13": 58, "132": 1, "133": 1, "134": 2, "137": 1, "138": 2, "139": 1, "14": 28, "143": 2, "144": 1, "148": 1, "15": 21, "150": 1, "151": 1, "153": 2, "156": 2, "159": 1, "16": 24, "162": 1, "167": 1, "17": 15, "172": 1, "173": 1, "18": 15, "180": 1, "184": 1, "188": 1, "19": 10, "20": 4, "209": 1, "21": 7, "22": 10, "23": 12, "24": 6, "25": 11, "26": 5, "27": 6, "28": 6, "29": 6, "30": 7, "31": 5, "32": 6, "33": 4, "34": 7, "35": 5, "36": 2, "37": 6, "38": 6, "39": 6, "40": 2, "41": 5, "42": 3, "43": 3, "44": 7, "45": 8, "46": 4, "47": 1, "48": 3, "49": 1, "5": 2, "50": 5, "51": 3, "52": 5, "53": 3, "54": 2, "55": 2, "56": 4, "57": 6, "58": 5, "59": 9, "60": 11, "61": 6, "62": 3, "63": 4, "64": 7, "65": 5, "66": 6, "67": 3, "68": 4, "69": 4, "7": 2, "70": 3, "71": 3, "72": 8, "73": 3, "74": 1, "75": 1, "76": 3, "77": 6, "78": 5, "79": 3, "8": 1, "80": 1, "81": 6, "82": 3, "83": 4, "84": 6, "85": 4, "86": 5, "87": 3, "88": 4, "89": 4, "9": 6, "91": 2, "92": 4, "93": 3, "94": 5, "95": 5, "96": 2, "97": 3, "98": 3, "99": 5}, "max": 209, "mean": 45.812, "min": 0, "p50": 31, "p90": 99}`
- QA context counts: `{"counts": {"0": 3934, "1": 7679, "10": 80, "101": 2, "11": 46, "12": 42, "13": 46, "14": 30, "15": 32, "16": 24, "17": 26, "18": 16, "19": 16, "2": 3918, "20": 30, "21": 12, "22": 10, "23": 2, "24": 10, "25": 2, "26": 8, "27": 2, "28": 4, "29": 4, "3": 320, "30": 2, "31": 6, "32": 2, "33": 4, "35": 4, "36": 4, "37": 2, "4": 244, "40": 2, "41": 4, "5": 196, "53": 2, "6": 148, "67": 2, "7": 130, "74": 2, "8": 84, "80": 2, "85": 2, "86": 2, "9": 66, "94": 2}, "max": 101, "mean": 1.769, "min": 0, "p50": 1, "p90": 2}`
- QA citation/reference counts: `{"counts": {"0": 3934, "1": 264, "10": 52, "11": 28, "12": 6, "13": 18, "14": 6, "15": 8, "16": 10, "17": 4, "19": 2, "2": 8127, "21": 2, "3": 460, "4": 3702, "5": 224, "6": 118, "7": 104, "8": 94, "9": 44}, "max": 21, "mean": 2.212, "min": 0, "p50": 2, "p90": 4}`
- Answer word counts: `{"counts": {"1": 62, "10": 310, "100": 10, "101": 10, "102": 10, "103": 4, "104": 2, "105": 12, "106": 6, "107": 8, "108": 8, "109": 6, "11": 353, "110": 4, "111": 6, "112": 6, "113": 8, "115": 8, "116": 4, "117": 4, "118": 8, "119": 2, "12": 366, "120": 8, "123": 6, "124": 6, "125": 8, "126": 6, "127": 2, "128": 4, "129": 14, "13": 341, "130": 6, "131": 10, "132": 2, "133": 10, "134": 6, "135": 6, "136": 8, "137": 6, "138": 6, "139": 6, "14": 403, "140": 2, "141": 4, "142": 2, "143": 4, "144": 2, "145": 8, "146": 4, "147": 6, "148": 4, "149": 4, "15": 396, "150": 8, "151": 4, "152": 4, "153": 8, "154": 8, "155": 2, "156": 4, "157": 6, "158": 2, "16": 425, "161": 4, "162": 4, "163": 4, "164": 2, "167": 2, "168": 2, "169": 2, "17": 403, "170": 4, "172": 8, "173": 6, "174": 6, "175": 6, "176": 2, "177": 4, "178": 2, "179": 8, "18": 376, "180": 2, "181": 2, "183": 2, "184": 2, "188": 2, "189": 4, "19": 379, "190": 2, "191": 2, "192": 2, "193": 2, "194": 4, "195": 2, "197": 2, "198": 2, "199": 4, "2": 22, "20": 367, "200": 2, "201": 4, "203": 2, "204": 4, "206": 4, "207": 4, "208": 2, "21": 335, "210": 4, "212": 2, "22": 356, "221": 2, "224": 2, "225": 2, "226": 4, "23": 319, "231": 2, "232": 2, "234": 4, "235": 2, "239": 4, "24": 333, "242": 2, "244": 6, "246": 2, "247": 4, "248": 2, "25": 274, "252": 2, "253": 2, "254": 2, "255": 2, "256": 2, "259": 4, "26": 323, "261": 2, "263": 4, "265": 4, "266": 4, "27": 332, "275": 2, "277": 4, "28": 334, "289": 2, "29": 289, "298": 2, "3": 3998, "30": 351, "31": 343, "319": 2, "32": 342, "322": 2, "33": 268, "331": 2, "34": 276, "340": 2, "35": 256, "354": 2, "355": 2, "357": 2, "36": 246, "37": 235, "38": 200, "39": 184, "4": 82, "40": 161, "41": 157, "42": 98, "43": 97, "44": 82, "45": 59, "46": 90, "47": 49, "479": 2, "48": 64, "49": 46, "5": 128, "50": 46, "51": 37, "52": 43, "53": 34, "54": 50, "55": 32, "56": 22, "57": 16, "58": 17, "59": 29, "6": 138, "60": 26, "61": 12, "62": 35, "63": 20, "64": 12, "65": 30, "66": 22, "67": 10, "68": 18, "69": 26, "7": 158, "70": 18, "71": 18, "72": 26, "73": 8, "74": 18, "75": 20, "76": 22, "77": 16, "78": 16, "79": 6, "8": 203, "80": 18, "81": 12, "82": 12, "83": 8, "84": 14, "85": 14, "86": 10, "87": 10, "88": 8, "89": 18, "9": 317, "90": 18, "91": 10, "92": 10, "93": 12, "94": 10, "95": 2, "96": 8, "97": 6, "98": 6, "99": 14}, "max": 479, "mean": 25.524, "min": 1, "p50": 19, "p90": 46}`

## Top 20 Longest Labels

- Paxlovid (`8a99d6d6-fd9e-45bb-b1bf-48c7f761232a`): 209 chunks, 95303 chars
- Lopinavir-Ritonavir (`4b1caefa-e6a2-42f3-9194-6dc1dd9e6d85`): 188 chunks, 111189 chars
- FEIRZA 1.5/30 TM (`dd18e808-bb80-8182-bf7b-8e6d5763570d`): 184 chunks, 118772 chars
- Actoplus Met (`42e49120-6f3f-11db-9fe1-0800200c9a66`): 180 chunks, 90330 chars
- INVOKAMET (`6868666b-c25e-40d1-9d1f-306bbe9390c1`): 173 chunks, 130455 chars
- Microgestin Fe (`54262321-1af5-4433-88c6-4409ff428079`): 172 chunks, 110422 chars
- Emtricitabine, Rilpivirine, Tenofovir Disoproxil Fumarate (`d9a4185e-43fa-4aeb-9b0f-8db01b166038`): 167 chunks, 119655 chars
- Quetiapine Fumarate ER (`23820efc-4df7-9dc9-e063-6394a90a0bb4`): 162 chunks, 149390 chars
- Lamotrigine (`15d801a0-f0a5-40c1-bc88-d5ba9a02c696`): 159 chunks, 128745 chars
- CIBINQO (`16c12a56-4550-414b-ac9d-b785b41fea6b`): 156 chunks, 72362 chars
- Saxagliptin (`6e8d8c4f-96eb-4b64-9c8c-4a5448a23a78`): 156 chunks, 83655 chars
- CELECOXIB (`27f17ae7-939b-402e-9498-3b6611104089`): 153 chunks, 96103 chars
- VALTYA 1/50 (`1aff28b0-93eb-5e44-9164-d76ffd08cd59`): 153 chunks, 97854 chars
- RYBELSUS (`27f15fac-7d98-4114-a2ec-92494a91da98`): 151 chunks, 76056 chars
- Omeprazole (`d9b3918c-a66e-4277-8b8f-b7ece93fa7db`): 150 chunks, 103883 chars
- Jardiance (`5777b8a8-ada6-4950-8548-43a1de11f075`): 148 chunks, 95250 chars
- COMPLERA (`d637cfab-f1e8-4eb3-a1b3-f85ca3bec612`): 144 chunks, 91935 chars
- LYBALVI (`32ffddd1-4e2b-45d9-9b36-bb730167ec80`): 143 chunks, 88657 chars
- Lenalidomide (`ed7a3099-ce31-4865-b212-358d9ff6261b`): 143 chunks, 146486 chars
- ziprasidone hydrochloride (`7e7261d7-4902-4bb5-a268-6c358890f963`): 139 chunks, 104821 chars

## Top 20 QA Rows With Many Citations/Context Chunks

- `b2531657ba5c7a78` Paxlovid: What important drug interactions are noted for Paxlovid? (task=factual, context=101, citations=4, label_chunks=209)
- `6f12607a1ba14dd5` Paxlovid: Which medications should be avoided with Paxlovid? (task=factual, context=101, citations=4, label_chunks=209)
- `daef650b92e56473` Lopinavir-Ritonavir: How should Lopinavir-Ritonavir be administered? (task=factual, context=94, citations=10, label_chunks=188)
- `a0576a26f2a2eeac` Lopinavir-Ritonavir: What is the recommended dosage regimen of Lopinavir-Ritonavir? (task=factual, context=94, citations=10, label_chunks=188)
- `9be5515bc3064979` Lopinavir-Ritonavir: What safety risks are listed for Lopinavir-Ritonavir? (task=factual, context=86, citations=15, label_chunks=188)
- `18078efe9380c8dc` Lopinavir-Ritonavir: What important warnings or precautions are associated with Lopinavir-Ritonavir? (task=factual, context=86, citations=15, label_chunks=188)
- `fbab4114f66e2dda` Paxlovid: What important warnings or precautions are associated with Paxlovid? (task=factual, context=85, citations=5, label_chunks=209)
- `2d63e0a82215867f` Paxlovid: What safety risks are listed for Paxlovid? (task=factual, context=85, citations=5, label_chunks=209)
- `cf74a5a8ac9b19de` Paxlovid: What are the contraindications for Paxlovid? (task=factual, context=80, citations=2, label_chunks=209)
- `c4dc176c4827f0ef` Paxlovid: Who should not take Paxlovid? (task=factual, context=80, citations=2, label_chunks=209)
- `157a695e67604b3c` Lopinavir-Ritonavir: What important drug interactions are noted for Lopinavir-Ritonavir? (task=factual, context=74, citations=4, label_chunks=188)
- `5aae262ce6873745` Lopinavir-Ritonavir: Which medications should be avoided with Lopinavir-Ritonavir? (task=factual, context=74, citations=4, label_chunks=188)
- `55d09c5df742eaec` Emtricitabine, Rilpivirine, Tenofovir Disoproxil Fumarate: What is the recommended dosage regimen of Emtricitabine, Rilpivirine, Tenofovir Disoproxil Fumarate? (task=factual, context=67, citations=7, label_chunks=167)
- `005acaea4542b5ca` Emtricitabine, Rilpivirine, Tenofovir Disoproxil Fumarate: How should Emtricitabine, Rilpivirine, Tenofovir Disoproxil Fumarate be administered? (task=factual, context=67, citations=7, label_chunks=167)
- `ce280919eec0df0d` Emtricitabine, Rilpivirine, Tenofovir Disoproxil Fumarate: Are there any population-specific considerations for Emtricitabine, Rilpivirine, Tenofovir Disoproxil Fumarate? (task=factual, context=53, citations=5, label_chunks=167)
- `030f2184eac4386f` Emtricitabine, Rilpivirine, Tenofovir Disoproxil Fumarate: What is known about the use of Emtricitabine, Rilpivirine, Tenofovir Disoproxil Fumarate in specific populations? (task=factual, context=53, citations=5, label_chunks=167)
- `9397027b0b4c37ea` SYMBRAVO: What important warnings or precautions are associated with SYMBRAVO? (task=factual, context=37, citations=20, label_chunks=134)
- `cf2ab8f16c514479` SYMBRAVO: What safety risks are listed for SYMBRAVO? (task=factual, context=37, citations=20, label_chunks=134)
- `8800c9162fc7d1af` Fingolimod: What safety risks are listed for Fingolimod? (task=factual, context=40, citations=15, label_chunks=109)
- `c385a24052fa4844` Fingolimod: What important warnings or precautions are associated with Fingolimod? (task=factual, context=40, citations=15, label_chunks=109)

## Repeated Question Templates

- 244x `what are the contraindications for drug`
- 224x `what adverse reactions have been reported for drug`
- 224x `what are the side effects of drug`
- 222x `how should drug be administered`
- 222x `who should not take drug`
- 221x `what important warnings or precautions are associated with drug`
- 221x `what is the recommended dosage regimen of drug`
- 221x `what safety risks are listed for drug`
- 216x `what is drug used to treat`
- 214x `what conditions is drug indicated for`
- 210x `what dosage forms are available for drug`
- 210x `what strengths does drug come in`
- 200x `what important drug interactions are noted for drug`
- 200x `which medications should be avoided with drug`
- 167x `are there any population specific considerations for drug`
- 167x `what is known about the use of drug in specific populations`
- 136x `what is the recommended approach for adjusting drug dosage in response to elevated inflammatory markers`
- 86x `what does the boxed warning for drug emphasize`
- 86x `what serious risks are included in the boxed warning for drug`
- 73x `what is the inr cutoff for commencing drug therapy in patients experiencing severe hepatic impairment`

## Easy/Obvious Refusal Questions

- `a043ffd15298b8c8` Her Style: How must Her Style dosing be altered in cases of hyperthyroidism? (task=refusal, context=0, citations=0, label_chunks=23)
- `4c7f677874e4f8c5` Premier Value: How is Premier Value dosing modified in cases of hyperthyroidism? (task=refusal, context=0, citations=0, label_chunks=13)
- `556286abacf83010` meijer: How should the dosing of meijer be altered in cases of hyperthyroidism? (task=refusal, context=0, citations=0, label_chunks=14)
- `b662a069d12c0b1a` TopCare: How should the dosage of TopCare be altered in cases of hyperthyroidism? (task=refusal, context=0, citations=0, label_chunks=13)
- `17a314420ee3b044` Danazol: How is Danazol dosage modified in response to elevated inflammatory markers? (task=refusal, context=0, citations=0, label_chunks=21)
- `34180964124cc0df` Orquidea: In cases of hyperthyroidism, what changes should be made to Orquidea dosing? (task=refusal, context=0, citations=0, label_chunks=60)
- `6c7fe9fa0a06f65c` Nora BE: How must Nora's BE dosing be altered in response to elevated thyroid function? (task=refusal, context=0, citations=0, label_chunks=45)
- `6645294b7e43426d` Affodel: What is the QTc interval cutoff for starting Affodel therapy in pregnant women? (task=refusal, context=0, citations=0, label_chunks=46)
- `748ca6c8c6042d55` EVOXAC: What is the QTc interval cutoff for commencing EVOXAC therapy in pregnant women? (task=refusal, context=0, citations=0, label_chunks=12)
- `e3ebdd94134c2dc1` Mucus Relief D: What is the QTc interval cutoff for commencing Mucus Relief D in pregnant women? (task=refusal, context=0, citations=0, label_chunks=15)
- `34748a31d9678cd1` Prednisolone: What is the QTc interval cutoff for commencing Prednisolone in pregnant females? (task=refusal, context=0, citations=0, label_chunks=25)
- `374f4cc0243b4d0b` Aleve PM: What is the QTc interval cutoff for beginning Aleve PM therapy in pregnant women? (task=refusal, context=0, citations=0, label_chunks=15)
- `0a591a82651c29b4` Benznidazole: How is Benznidazole dosage modified in response to elevated inflammatory markers? (task=refusal, context=0, citations=0, label_chunks=92)
- `924a34b934edd729` CYTOTEC: How is CYTOTEC dosing altered in response to elevated inflammatory marker levels? (task=refusal, context=0, citations=0, label_chunks=22)
- `c436096093a698ad` Lyleq: What is the QTc interval cutoff for commencing Lyleq therapy in pregnant females? (task=refusal, context=0, citations=0, label_chunks=18)
- `56c23a4ca7f97771` Omeclamox-Pak: What is the HbA1c cutoff for commencing Omeclamox-Pak in G6PD deficient patients? (task=refusal, context=0, citations=0, label_chunks=118)
- `ae29598a134a3571` SheWise: What is the QTc interval cutoff for starting SheWise therapy in pregnant females? (task=refusal, context=0, citations=0, label_chunks=24)
- `4aff1ee18cceb895` Alavert: What is the QTc interval cutoff for beginning Alavert therapy in pregnant females? (task=refusal, context=0, citations=0, label_chunks=15)
- `70b65027806263e4` Allergy: What is the QTc interval cutoff for beginning allergy therapy in pregnant females? (task=refusal, context=0, citations=0, label_chunks=13)
- `42025e90955afe4d` Camila: What is the QTc interval cutoff for commencing Camila therapy in pregnant females? (task=refusal, context=0, citations=0, label_chunks=33)

## Better Hard/Refusal Questions

- `673aac2fadecebd6` kirkland signature allerclear: Does the prescribing information for Kirkland Signature Allerclear indicate the need for dose modifications in patients with severe hepatic impairment and altered thyroid function? (task=refusal, context=0, citations=0, label_chunks=12)
- `89640877ce2b6cfe` Loratadine Allergy Relief: Does the prescribing information indicate the need for dose modifications of Loratadine Allergy Relief in patients with significant hepatic impairment and altered thyroid function? (task=refusal, context=0, citations=0, label_chunks=8)
- `c92a088041b4c972` SUNMARK CHILDRENS LORATADINE SRP SF GRAPE: Does the product label indicate the need for dose alterations of SUNMARK CHILDRENS LORATADINE SRP SF GRAPE in patients with severe hepatic impairment and abnormal thyroid function? (task=refusal, context=0, citations=0, label_chunks=15)
- `4ace1a09e9b5f831` Fexofenadine Hydrochloride: Does the prescribing information indicate the need for dose modifications of Fexofenadine Hydrochloride in individuals with severe hepatic impairment and altered thyroid function? (task=refusal, context=0, citations=0, label_chunks=14)
- `18f4ded85dc0da5c` INVOKAMET: Does the prescribing information for INVOKAMET indicate the need for dose modifications in cases of abnormal thyroid function in patients suffering from severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=173)
- `1f319a9cec715b25` Cabinet Allergy Relief Fexofenadine: Are dose adjustments for Cabinet Allergy Relief Fexofenadine indicated in patients with severe hepatic impairment who also have abnormal thyroid function according to the label? (task=refusal, context=0, citations=0, label_chunks=9)
- `214f6d452eed1197` Cetirizine Hydrochloride: Does the prescribing information indicate the need for dose modifications of Cetirizine Hydrochloride in individuals with severe hepatic impairment and altered thyroid function? (task=refusal, context=0, citations=0, label_chunks=12)
- `cf20aae5cc9e853a` berkley jensen allergy relief: Does the prescribing information suggest altering the dose of Berkley Jensen Allergy Relief in cases of abnormal thyroid function among patients with severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=13)
- `371e488941c44c3e` caring mill mucus dm: Does the prescribing information indicate the need for dose modifications of Caring Mill Mucus DM in cases of thyroid dysfunction among patients with severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=12)
- `d20c048a26f3cb77` CAREALL Loratadine: Does the prescribing information for CAREALL Loratadine indicate the need for dose modifications in cases of thyroid dysfunction among patients with severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=7)
- `b11eecfd390fb8c4` good neighbor pharmacy childrens loratadine: Does the prescribing information suggest altering the dose of good neighbor pharmacy children's loratadine for patients with severe hepatic impairment and thyroid dysfunction? (task=refusal, context=0, citations=0, label_chunks=12)
- `173b4753e31153d0` Benztropine Mesylate: Does the prescribing information indicate that Benztropine Mesylate requires dose modifications in cases of thyroid dysfunction among patients with severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=21)
- `dccbf8e5efae212e` Curist Allergy Relief: Does the prescribing information indicate the need for dose modifications of Curist Allergy Relief in individuals with severe hepatic impairment and altered thyroid function? (task=refusal, context=0, citations=0, label_chunks=13)
- `2a81bfa7e66f3e7a` Mibelas 24 Fe: Does the prescribing information for Mibelas 24 Fe indicate the need for dose adjustments in cases of abnormal thyroid function among patients with severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=94)
- `71640d56831c846f` Phenelzine Sulfate: Does the prescribing information indicate the need for dose modifications of Phenelzine Sulfate in cases of thyroid dysfunction among patients with severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=42)
- `4d6c1eb3b9cbce91` equate diarrhea control: Does the prescribing information indicate the need for dose alterations of equate for diarrhea control in individuals with severe hepatic impairment and thyroid dysfunction? (task=refusal, context=0, citations=0, label_chunks=16)
- `e2d5410b59ac5431` Methadone Hydrochloride: Does the prescribing information indicate the need for dose modifications of Methadone Hydrochloride in patients with severe hepatic impairment and altered thyroid function? (task=refusal, context=0, citations=0, label_chunks=67)
- `4d70b3b5254fb346` basic care levonorgestrel: Does the prescribing information suggest altering the dose of basic care levonorgestrel in cases of abnormal thyroid function among patients with severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=18)
- `6527b32ed772b0ff` Nicotine Polacrilex Lozenge Mint: Does the prescribing information suggest modifying the dose of Nicotine Polacrilex Lozenge Mint in individuals with severe hepatic impairment and abnormal thyroid activity? (task=refusal, context=0, citations=0, label_chunks=25)
- `806a2b6740347037` ROPINIROLE HYDROCHLORIDE: Does the prescribing information suggest modifying the dose of ROPINIROLE HYDROCHLORIDE in cases of abnormal thyroid function among patients with severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=57)

## Candidate Hard Examples

### Many Citations Or Context

- `b2531657ba5c7a78` Paxlovid: What important drug interactions are noted for Paxlovid? (task=factual, context=101, citations=4, label_chunks=209)
- `6f12607a1ba14dd5` Paxlovid: Which medications should be avoided with Paxlovid? (task=factual, context=101, citations=4, label_chunks=209)
- `daef650b92e56473` Lopinavir-Ritonavir: How should Lopinavir-Ritonavir be administered? (task=factual, context=94, citations=10, label_chunks=188)
- `a0576a26f2a2eeac` Lopinavir-Ritonavir: What is the recommended dosage regimen of Lopinavir-Ritonavir? (task=factual, context=94, citations=10, label_chunks=188)
- `9be5515bc3064979` Lopinavir-Ritonavir: What safety risks are listed for Lopinavir-Ritonavir? (task=factual, context=86, citations=15, label_chunks=188)
- `18078efe9380c8dc` Lopinavir-Ritonavir: What important warnings or precautions are associated with Lopinavir-Ritonavir? (task=factual, context=86, citations=15, label_chunks=188)
- `fbab4114f66e2dda` Paxlovid: What important warnings or precautions are associated with Paxlovid? (task=factual, context=85, citations=5, label_chunks=209)
- `2d63e0a82215867f` Paxlovid: What safety risks are listed for Paxlovid? (task=factual, context=85, citations=5, label_chunks=209)
- `cf74a5a8ac9b19de` Paxlovid: What are the contraindications for Paxlovid? (task=factual, context=80, citations=2, label_chunks=209)
- `c4dc176c4827f0ef` Paxlovid: Who should not take Paxlovid? (task=factual, context=80, citations=2, label_chunks=209)

### Long Label Retrieval

- `20e15c8cb83e851c` Paxlovid: What important drug interactions are noted for Paxlovid? (task=factual, context=1, citations=0, label_chunks=209)
- `c57a276f24de19d0` Paxlovid: Which medications should be avoided with Paxlovid? (task=factual, context=1, citations=0, label_chunks=209)
- `1264e056f32a838f` Paxlovid: What conditions is Paxlovid indicated for? (task=factual, context=2, citations=1, label_chunks=209)
- `2a6926e783e7deee` Paxlovid: What is Paxlovid used to treat? (task=factual, context=2, citations=1, label_chunks=209)
- `000ecd1d6df50389` Paxlovid: What is the recommended dosage regimen of Paxlovid? (task=factual, context=28, citations=7, label_chunks=209)
- `b54c25890c1ae3a6` Paxlovid: How should Paxlovid be administered? (task=factual, context=28, citations=7, label_chunks=209)
- `89c06119461a4430` Paxlovid: What dosage forms are available for Paxlovid? (task=factual, context=1, citations=1, label_chunks=209)
- `b8f28849dee58ead` Paxlovid: What strengths does Paxlovid come in? (task=factual, context=1, citations=1, label_chunks=209)
- `cf74a5a8ac9b19de` Paxlovid: What are the contraindications for Paxlovid? (task=factual, context=80, citations=2, label_chunks=209)
- `c4dc176c4827f0ef` Paxlovid: Who should not take Paxlovid? (task=factual, context=80, citations=2, label_chunks=209)

### Safety Warning Candidates

- `b2531657ba5c7a78` Paxlovid: What important drug interactions are noted for Paxlovid? (task=factual, context=101, citations=4, label_chunks=209)
- `6f12607a1ba14dd5` Paxlovid: Which medications should be avoided with Paxlovid? (task=factual, context=101, citations=4, label_chunks=209)
- `daef650b92e56473` Lopinavir-Ritonavir: How should Lopinavir-Ritonavir be administered? (task=factual, context=94, citations=10, label_chunks=188)
- `a0576a26f2a2eeac` Lopinavir-Ritonavir: What is the recommended dosage regimen of Lopinavir-Ritonavir? (task=factual, context=94, citations=10, label_chunks=188)
- `9be5515bc3064979` Lopinavir-Ritonavir: What safety risks are listed for Lopinavir-Ritonavir? (task=factual, context=86, citations=15, label_chunks=188)
- `18078efe9380c8dc` Lopinavir-Ritonavir: What important warnings or precautions are associated with Lopinavir-Ritonavir? (task=factual, context=86, citations=15, label_chunks=188)
- `fbab4114f66e2dda` Paxlovid: What important warnings or precautions are associated with Paxlovid? (task=factual, context=85, citations=5, label_chunks=209)
- `2d63e0a82215867f` Paxlovid: What safety risks are listed for Paxlovid? (task=factual, context=85, citations=5, label_chunks=209)
- `cf74a5a8ac9b19de` Paxlovid: What are the contraindications for Paxlovid? (task=factual, context=80, citations=2, label_chunks=209)
- `c4dc176c4827f0ef` Paxlovid: Who should not take Paxlovid? (task=factual, context=80, citations=2, label_chunks=209)

### Better Hard Refusals

- `673aac2fadecebd6` kirkland signature allerclear: Does the prescribing information for Kirkland Signature Allerclear indicate the need for dose modifications in patients with severe hepatic impairment and altered thyroid function? (task=refusal, context=0, citations=0, label_chunks=12)
- `89640877ce2b6cfe` Loratadine Allergy Relief: Does the prescribing information indicate the need for dose modifications of Loratadine Allergy Relief in patients with significant hepatic impairment and altered thyroid function? (task=refusal, context=0, citations=0, label_chunks=8)
- `c92a088041b4c972` SUNMARK CHILDRENS LORATADINE SRP SF GRAPE: Does the product label indicate the need for dose alterations of SUNMARK CHILDRENS LORATADINE SRP SF GRAPE in patients with severe hepatic impairment and abnormal thyroid function? (task=refusal, context=0, citations=0, label_chunks=15)
- `4ace1a09e9b5f831` Fexofenadine Hydrochloride: Does the prescribing information indicate the need for dose modifications of Fexofenadine Hydrochloride in individuals with severe hepatic impairment and altered thyroid function? (task=refusal, context=0, citations=0, label_chunks=14)
- `18f4ded85dc0da5c` INVOKAMET: Does the prescribing information for INVOKAMET indicate the need for dose modifications in cases of abnormal thyroid function in patients suffering from severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=173)
- `1f319a9cec715b25` Cabinet Allergy Relief Fexofenadine: Are dose adjustments for Cabinet Allergy Relief Fexofenadine indicated in patients with severe hepatic impairment who also have abnormal thyroid function according to the label? (task=refusal, context=0, citations=0, label_chunks=9)
- `214f6d452eed1197` Cetirizine Hydrochloride: Does the prescribing information indicate the need for dose modifications of Cetirizine Hydrochloride in individuals with severe hepatic impairment and altered thyroid function? (task=refusal, context=0, citations=0, label_chunks=12)
- `cf20aae5cc9e853a` berkley jensen allergy relief: Does the prescribing information suggest altering the dose of Berkley Jensen Allergy Relief in cases of abnormal thyroid function among patients with severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=13)
- `371e488941c44c3e` caring mill mucus dm: Does the prescribing information indicate the need for dose modifications of Caring Mill Mucus DM in cases of thyroid dysfunction among patients with severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=12)
- `d20c048a26f3cb77` CAREALL Loratadine: Does the prescribing information for CAREALL Loratadine indicate the need for dose modifications in cases of thyroid dysfunction among patients with severe hepatic impairment? (task=refusal, context=0, citations=0, label_chunks=7)

### Easy Or Obvious Refusals

- `a043ffd15298b8c8` Her Style: How must Her Style dosing be altered in cases of hyperthyroidism? (task=refusal, context=0, citations=0, label_chunks=23)
- `4c7f677874e4f8c5` Premier Value: How is Premier Value dosing modified in cases of hyperthyroidism? (task=refusal, context=0, citations=0, label_chunks=13)
- `556286abacf83010` meijer: How should the dosing of meijer be altered in cases of hyperthyroidism? (task=refusal, context=0, citations=0, label_chunks=14)
- `b662a069d12c0b1a` TopCare: How should the dosage of TopCare be altered in cases of hyperthyroidism? (task=refusal, context=0, citations=0, label_chunks=13)
- `17a314420ee3b044` Danazol: How is Danazol dosage modified in response to elevated inflammatory markers? (task=refusal, context=0, citations=0, label_chunks=21)
- `34180964124cc0df` Orquidea: In cases of hyperthyroidism, what changes should be made to Orquidea dosing? (task=refusal, context=0, citations=0, label_chunks=60)
- `6c7fe9fa0a06f65c` Nora BE: How must Nora's BE dosing be altered in response to elevated thyroid function? (task=refusal, context=0, citations=0, label_chunks=45)
- `6645294b7e43426d` Affodel: What is the QTc interval cutoff for starting Affodel therapy in pregnant women? (task=refusal, context=0, citations=0, label_chunks=46)
- `748ca6c8c6042d55` EVOXAC: What is the QTc interval cutoff for commencing EVOXAC therapy in pregnant women? (task=refusal, context=0, citations=0, label_chunks=12)
- `e3ebdd94134c2dc1` Mucus Relief D: What is the QTc interval cutoff for commencing Mucus Relief D in pregnant women? (task=refusal, context=0, citations=0, label_chunks=15)
