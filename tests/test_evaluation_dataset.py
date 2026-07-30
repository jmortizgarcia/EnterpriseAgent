from enterpriseagent.evaluation.dataset import EVAL_DATASET


class TestEvalDataset:
    def test_has_40_items(self):
        assert len(EVAL_DATASET) == 40

    def test_all_items_have_required_fields(self):
        for item in EVAL_DATASET:
            assert item.question, f"Missing question in {item}"
            assert item.expected_answer, f"Missing expected_answer in {item}"
            assert isinstance(item.category, str)
            assert isinstance(item.expected_sources, list)

    def test_categories_are_valid(self):
        valid = {"factual", "synthetic", "no_answer", "edge"}
        for item in EVAL_DATASET:
            assert item.category in valid, f"Invalid category {item.category} in {item.question}"

    def test_category_counts(self):
        counts = {}
        for item in EVAL_DATASET:
            counts[item.category] = counts.get(item.category, 0) + 1
        assert counts.get("factual", 0) == 15
        assert counts.get("synthetic", 0) == 10
        assert counts.get("no_answer", 0) == 10
        assert counts.get("edge", 0) == 5

    def test_no_answer_items_have_empty_sources(self):
        for item in EVAL_DATASET:
            if item.category == "no_answer":
                assert item.expected_sources == [], f"no_answer item should have empty sources: {item.question}"
