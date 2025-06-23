export const wordMap = {
    "svg1-1": "svg2-1", "svg1-2": "svg2-2", "svg1-3": "svg2-4", "svg1-4": "svg2-3",
    "svg1-5": "svg2-3", "svg1-6": "svg2-5", "svg1-7": "svg2-6", "svg1-8": "svg2-6",
    "svg1-9": "svg2-7", "svg1-10": "svg2-8", "svg1-11": "svg2-9", "svg1-12": "svg2-10",
    "svg2-1": "svg1-1", "svg2-2": "svg1-2", "svg2-3": "svg1-5", "svg2-4": "svg1-3",
    "svg2-5": "svg1-6", "svg2-6": "svg1-8", "svg2-7": "svg1-9", "svg2-8": "svg1-10",
    "svg2-9": "svg1-11", "svg2-10": "svg1-12"
  };
  
  export const sentences = [
    {
      svgId: "svg1",
      data: `1\tεἴδομεν\tὁράω\tVERB\tV-\tAspect=Perf|Mood=Ind|Number=Plur|Person=1|Tense=Past|VerbForm=Fin|Voice=Act\t0\troot
  2\tγὰρ\tγάρ\tADV\tDf\t_\t1\tdiscourse
  3\tαὐτοῦ\tαὐτός\tPRON\tPp\tCase=Gen|Gender=Masc|Number=Sing|Person=3|PronType=Prs\t5\tdet
  4\tτὸν\tὁ\tDET\tS-\tCase=Acc|Definite=Def|Gender=Masc|Number=Sing|PronType=Dem\t5\tdet
  5\tἀστέρα\tἀστήρ\tNOUN\tNb\tCase=Acc|Gender=Masc|Number=Sing\t1\tobj
  6\tἐν\tἐν\tADP\tR-\t_\t8\tcase
  7\tτῇ\tὁ\tDET\tS-\tCase=Dat|Definite=Def|Gender=Fem|Number=Sing|PronType=Dem\t8\tdet
  8\tἀνατολῇ\tἀνατολή\tNOUN\tNb\tCase=Dat|Gender=Fem|Number=Sing\t1\tobl
  9\tκαὶ\tκαί\tCCONJ\tC-\t_\t10\tcc
  10\tἤλθομεν\tἔρχομαι\tVERB\tV-\tAspect=Perf|Mood=Ind|Number=Plur|Person=1|Tense=Past|VerbForm=Fin|Voice=Act\t1\tconj
  11\tπροσκυνῆσαι\tπροσκυνέω\tVERB\tV-\tAspect=Perf|Tense=Past|VerbForm=Inf|Voice=Act\t10\txcomp
  12\tαὐτῷ\tαὐτός\tPRON\tPp\tCase=Dat|Gender=Masc|Number=Sing|Person=3|PronType=Prs\t11\tobl:arg`
    },
    {
      svgId: "svg2",
      data: `1\tvidimus\tvideo\tVERB\tV-\tAspect=Perf|Mood=Ind|Number=Plur|Person=1|Tense=Past|VerbForm=Fin|Voice=Act\t0\troot
  2\tenim\tenim\tADV\tDf\t_\t1\tdiscourse
  3\tstellam\tstella\tNOUN\tNb\tCase=Acc|Gender=Fem|Number=Sing\t1\tobj
  4\teius\tis\tPRON\tPp\tCase=Gen|Gender=Masc|Number=Sing|Person=3|PronType=Prs\t3\tdet
  5\tin\tin\tADP\tR-\t_\t6\tcase
  6\toriente\toriens\tNOUN\tNb\tCase=Abl|Gender=Masc|Number=Sing\t1\tobl
  7\tet\tet\tCCONJ\tC-\t_\t8\tcc
  8\tvenimus\tvenio\tVERB\tV-\tAspect=Perf|Mood=Ind|Number=Plur|Person=1|Tense=Past|VerbForm=Fin|Voice=Act\t1\tconj
  9\tadorare\tadoro\tVERB\tV-\tTense=Pres|VerbForm=Inf|Voice=Act\t8\tadvcl
  10\teum\tis\tPRON\tPp\tCase=Acc|Gender=Masc|Number=Sing|Person=3|PronType=Prs\t9\tobj`
    }
  ];
  