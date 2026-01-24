export const wordMap = {
    "greek-1": "latin-1",
    "greek-2": "latin-2",
    "greek-3": "latin-3",
    "greek-4": "latin-4",
    "greek-5": "latin-6",
    "greek-6": "latin-7",
    "greek-7": "latin-7",
  
    "latin-1": "greek-1",
    "latin-2": "greek-2",
    "latin-3": "greek-3",
    "latin-4": "greek-4",
    "latin-6": "greek-5",
    "latin-7": "greek-7"
  };
  
  export const sentences = [
    {
      svgId: "greek",
      data: `1\tποῦ\tποῦ\tADV\tDu\tPronType=Int\t2\tadvmod
  2\tἐστιν\tεἰμί\tAUX\tV-\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin|Voice=Act\t0\troot
  3\tὁ\tὁ\tDET\tS-\tCase=Nom|Definite=Def|Gender=Masc|Number=Sing|PronType=Dem\t5\tdet
  4\tτεχθεὶς\tτίκτω\tVERB\tV-\tAspect=Perf|Case=Nom|Gender=Masc|Number=Sing|Tense=Past|VerbForm=Part|Voice=Pass\t5\tacl
  5\tβασιλεὺς\tβασιλεύς\tNOUN\tNb\tCase=Nom|Gender=Masc|Number=Sing\t2\tnsubj
  6\tτῶν\tὁ\tDET\tS-\tCase=Gen|Definite=Def|Gender=Masc|Number=Plur|PronType=Dem\t7\tdet
  7\tἸουδαίων\tἸουδαῖος\tADJ\tA-\tCase=Gen|Degree=Pos|Gender=Masc|Number=Plur\t5\tnmod`
    },
    {
      svgId: "latin",
      data: `1\tubi\tubi\tADV\tDu\tPronType=Int\t2\tadvmod
  2\test\tsum\tAUX\tV-\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin|Voice=Act\t0\troot
  3\tqui\tqui\tPRON\tPr\tCase=Nom|Gender=Masc|Number=Sing|PronType=Rel\t4\tnsubj
  4\tnatus\tnascor\tVERB\tV-\tAspect=Perf|Case=Nom|Gender=Masc|Number=Sing|Tense=Past|VerbForm=Part|Voice=Pass\t6\tacl
  5\test\tsum\tAUX\tV-\tMood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin|Voice=Act\t4\taux
  6\trex\trex\tNOUN\tNb\tCase=Nom|Gender=Masc|Number=Sing\t2\tnsubj
  7\tIudaeorum\tIudaei\tNOUN\tNb\tCase=Gen|Gender=Masc|Number=Plur\t6\tnmod`
    }
  ];
  