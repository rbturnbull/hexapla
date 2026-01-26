const wordMap = {{ mapping | tojson }};
const siglum = {{ siglum | tojson }};
  
const sentences = [
{
    svgId: "{{ lang_a_id }}",
    data: {{ greek | tojson }},
    rtl: {{ lang_a_rtl | tojson }},
    noSpaceAfter: {{ lang_a_no_space_after | tojson }},
    languageSlug: {{ lang_a_slug | tojson }},
    lemmaMap: {{ lang_a_lemmas | tojson }}
},
{
    svgId: "{{ lang_b_id }}",
    data: {{ latin | tojson }},
    rtl: {{ lang_b_rtl | tojson }},
    noSpaceAfter: {{ lang_b_no_space_after | tojson }},
    languageSlug: {{ lang_b_slug | tojson }},
    lemmaMap: {{ lang_b_lemmas | tojson }}
}
];
