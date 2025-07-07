const wordMap = {"greek-1": "latin-1", "greek-2": "latin-2", "greek-3": "latin-3", "greek-4": "latin-4", "greek-5": "latin-6", "greek-6": "latin-7", "greek-7": "latin-7", "latin-1": "greek-1", "latin-2": "greek-2", "latin-3": "greek-3", "latin-4": "greek-4", "latin-6": "greek-5", "latin-7": "greek-7"};
  
const sentences = [
{
    svgId: "greek",
    data: `1	ποῦ	ποῦ	ADV	Du	PronType=Int	2	advmod
2	ἐστιν	εἰμί	AUX	V-	Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin|Voice=Act	0	root
3	ὁ	ὁ	DET	S-	Case=Nom|Definite=Def|Gender=Masc|Number=Sing|PronType=Dem	5	det
4	τεχθεὶς	τίκτω	VERB	V-	Aspect=Perf|Case=Nom|Gender=Masc|Number=Sing|Tense=Past|VerbForm=Part|Voice=Pass	5	acl
5	βασιλεὺς	βασιλεύς	NOUN	Nb	Case=Nom|Gender=Masc|Number=Sing	2	nsubj
6	τῶν	ὁ	DET	S-	Case=Gen|Definite=Def|Gender=Masc|Number=Plur|PronType=Dem	7	det
7	Ἰουδαίων	Ἰουδαῖος	ADJ	A-	Case=Gen|Degree=Pos|Gender=Masc|Number=Plur	5	nmod`
},
{
    svgId: "latin",
    data: `1	ubi	ubi	ADV	Du	PronType=Int	2	advmod
2	est	sum	AUX	V-	Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin|Voice=Act	0	root
3	qui	qui	PRON	Pr	Case=Nom|Gender=Masc|Number=Sing|PronType=Rel	4	nsubj
4	natus	nascor	VERB	V-	Aspect=Perf|Case=Nom|Gender=Masc|Number=Sing|Tense=Past|VerbForm=Part|Voice=Pass	6	acl
5	est	sum	AUX	V-	Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin|Voice=Act	4	aux
6	rex	rex	NOUN	Nb	Case=Nom|Gender=Masc|Number=Sing	2	nsubj
7	Iudaeorum	Iudaei	NOUN	Nb	Case=Gen|Gender=Masc|Number=Plur	6	nmod`
}
];