import unittest

from test_review_quality import module


class ReviewStrategyResourcesTests(unittest.TestCase):
    def test_strategy_is_conditional_and_each_stage_fits_budget(self):
        loader = module('load_skill_resources')
        base = loader.load_skill_resources(skill='evidence-audit', selectors=[])
        for selector, filename in [('contribution_review', 'contribution-review.md'),
                                   ('revision_options', 'revision-options.md')]:
            with self.subTest(selector=selector):
                self.assertFalse(any(r.relative_path.endswith(filename) for r in base.resources))
                result = loader.load_skill_resources(skill='evidence-audit', selectors=[
                    'axes.scope.full', 'axes.risk_threshold.all', 'conditional_loads.' + selector])
                self.assertTrue(any(r.relative_path.endswith(filename) for r in result.resources))
                self.assertLessEqual(result.total_chars, 12000)

    def test_strategy_stages_can_be_loaded_together_for_compact_review(self):
        result = module('load_skill_resources').load_skill_resources(skill='evidence-audit', selectors=[
            'conditional_loads.contribution_review', 'conditional_loads.revision_options',
            'axes.scope.local'])
        self.assertLessEqual(result.total_chars, 12000)
