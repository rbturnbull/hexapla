const wordMap = {"greek-1": "latin-1", "greek-10": "latin-8", "greek-11": "latin-9", "greek-12": "latin-10", "greek-2": "latin-2", "greek-3": "latin-4", "greek-4": "latin-3", "greek-5": "latin-3", "greek-6": "latin-5", "greek-7": "latin-6", "greek-8": "latin-6", "greek-9": "latin-7", "latin-1": "greek-1", "latin-10": "greek-12", "latin-2": "greek-2", "latin-3": "greek-5", "latin-4": "greek-3", "latin-5": "greek-6", "latin-6": "greek-8", "latin-7": "greek-9", "latin-8": "greek-10", "latin-9": "greek-11"};
  
const sentences = [
{
    svgId: "greek",
    data: `1	εἴδομεν	ὁράω	VERB	V-	Aspect=Perf|Mood=Ind|Number=Plur|Person=1|Tense=Past|VerbForm=Fin|Voice=Act	0	root
2	γὰρ	γάρ	ADV	Df	_	1	discourse
3	αὐτοῦ	αὐτός	PRON	Pp	Case=Gen|Gender=Masc|Number=Sing|Person=3|PronType=Prs	5	det
4	τὸν	ὁ	DET	S-	Case=Acc|Definite=Def|Gender=Masc|Number=Sing|PronType=Dem	5	det
5	ἀστέρα	ἀστήρ	NOUN	Nb	Case=Acc|Gender=Masc|Number=Sing	1	obj
6	ἐν	ἐν	ADP	R-	_	8	case
7	τῇ	ὁ	DET	S-	Case=Dat|Definite=Def|Gender=Fem|Number=Sing|PronType=Dem	8	det
8	ἀνατολῇ	ἀνατολή	NOUN	Nb	Case=Dat|Gender=Fem|Number=Sing	1	obl
9	καὶ	καί	CCONJ	C-	_	10	cc
10	ἤλθομεν	ἔρχομαι	VERB	V-	Aspect=Perf|Mood=Ind|Number=Plur|Person=1|Tense=Past|VerbForm=Fin|Voice=Act	1	conj
11	προσκυνῆσαι	προσκυνέω	VERB	V-	Aspect=Perf|Tense=Past|VerbForm=Inf|Voice=Act	10	xcomp
12	αὐτῷ	αὐτός	PRON	Pp	Case=Dat|Gender=Masc|Number=Sing|Person=3|PronType=Prs	11	obl:arg`
},
{
    svgId: "latin",
    data: `1	vidimus	video	VERB	V-	Aspect=Perf|Mood=Ind|Number=Plur|Person=1|Tense=Past|VerbForm=Fin|Voice=Act	0	root
2	enim	enim	ADV	Df	_	1	discourse
3	stellam	stella	NOUN	Nb	Case=Acc|Gender=Fem|Number=Sing	1	obj
4	eius	is	PRON	Pp	Case=Gen|Gender=Masc|Number=Sing|Person=3|PronType=Prs	3	det
5	in	in	ADP	R-	_	6	case
6	oriente	oriens	NOUN	Nb	Case=Abl|Gender=Masc|Number=Sing	1	obl
7	et	et	CCONJ	C-	_	8	cc
8	venimus	venio	VERB	V-	Aspect=Perf|Mood=Ind|Number=Plur|Person=1|Tense=Past|VerbForm=Fin|Voice=Act	1	conj
9	adorare	adoro	VERB	V-	Tense=Pres|VerbForm=Inf|Voice=Act	8	advcl
10	eum	is	PRON	Pp	Case=Acc|Gender=Masc|Number=Sing|Person=3|PronType=Prs	9	obj`
}
];