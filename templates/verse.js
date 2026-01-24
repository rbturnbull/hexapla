const wordMap = {{ mapping | tojson }};
  
const sentences = [
{
    svgId: "{{ lang_a_id }}",
    data: {{ greek | tojson }},
    rtl: {{ lang_a_rtl | tojson }},
    noSpaceAfter: {{ lang_a_no_space_after | tojson }}
},
{
    svgId: "{{ lang_b_id }}",
    data: {{ latin | tojson }},
    rtl: {{ lang_b_rtl | tojson }},
    noSpaceAfter: {{ lang_b_no_space_after | tojson }}
}
];
