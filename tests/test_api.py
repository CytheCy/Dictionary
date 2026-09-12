import unittest

from dictionary_app.api import clean_markup, parse_datamuse_response, parse_response


class ParserTests(unittest.TestCase):
    def test_markup_is_made_readable(self):
        self.assertEqual(clean_markup("{bc}a {it}very{/it} {sx|large||} thing"), ": a very large thing")

    def test_suggestion_response(self):
        entries, suggestions = parse_response(["calm", "clam", "calms"])
        self.assertEqual(entries, [])
        self.assertEqual(suggestions, ["calm", "clam", "calms"])

    def test_dictionary_entry(self):
        payload = [{
            "meta": {"id": "calm:1"},
            "hwi": {"hw": "calm", "prs": [{"mw": "ˈkäm"}]},
            "fl": "adjective",
            "def": [{"sseq": [[["sense", {"sn": "1", "dt": [["text", "{bc}free from agitation"], ["vis", [{"t": "a {it}calm{/it} day"}]]]}]]]}],
            "et": [["text", "Middle English"]],
        }]
        entries, suggestions = parse_response(payload)
        self.assertFalse(suggestions)
        self.assertEqual(entries[0].headword, "calm")
        self.assertEqual(entries[0].senses[0].definition, ": free from agitation")
        self.assertEqual(entries[0].senses[0].examples, ["a calm day"])

    def test_dictionary_sseq_with_multiple_senses(self):
        payload = [{
            "meta": {"id": "test:1"},
            "hwi": {"hw": "test"},
            "fl": "noun",
            "def": [{"sseq": [
                [["sense", {"sn": "1", "dt": [["text", "a means of testing"]]}]],
                [["sense", {"sn": "2", "dt": [["text", "a procedure or reaction"]]}]],
            ]}],
        }]
        entries, _ = parse_response(payload)
        self.assertEqual(
            [sense.definition for sense in entries[0].senses],
            ["a means of testing", "a procedure or reaction"],
        )

    def test_thesaurus_lists(self):
        payload = [{
            "meta": {"id": "calm", "syns": [["quiet", "still"]], "ants": [["agitated"]]},
            "hwi": {"hw": "calm"},
            "fl": "adjective",
            "def": [{"sseq": [[["sense", {"dt": [["text", "without agitation"]], "syn_list": [[{"wd": "peaceful"}]]}]]]}],
        }]
        entries, _ = parse_response(payload)
        self.assertEqual(entries[0].synonyms, ["quiet", "still"])
        self.assertEqual(entries[0].senses[0].synonyms, ["peaceful"])

    def test_datamuse_entry(self):
        payload = [{
            "word": "calm",
            "tags": ["query", "adj", "n", "ipa_pron:kɑm"],
            "defs": [
                "adj\tPeaceful and free from anxiety.",
                "adj\tFree of noise and disturbance.",
                "n\tThe state of being peaceful.",
            ],
        }]
        entries, suggestions = parse_datamuse_response(payload)
        self.assertEqual(suggestions, [])
        self.assertEqual([entry.functional_label for entry in entries], ["adjective", "noun"])
        self.assertEqual(entries[0].pronunciation, "/kɑm/")
        self.assertEqual(entries[0].senses[1].definition, "Free of noise and disturbance.")


if __name__ == "__main__":
    unittest.main()
