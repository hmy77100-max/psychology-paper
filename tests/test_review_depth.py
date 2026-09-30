"""Resource-delivery regressions, not a model-output or scientific evaluator."""
import unittest

from test_review_quality import module


class ReviewDepthTests(unittest.TestCase):
    def load(self, *selectors):
        return module('load_skill_resources').load_skill_resources(
            skill='evidence-audit', selectors=list(selectors))

    def test_full_review_contract_is_delivered_only_for_full_scope(self):
        for scope in ('local', 'section', 'change-impact', 'full'):
            with self.subTest(scope=scope):
                resources = self.load('axes.scope.' + scope).resources
                found = [r for r in resources if r.relative_path.endswith('full-review.md')]
                self.assertEqual(len(found), int(scope == 'full'))

    def test_authority_safeguards_reach_even_standalone_local_reviews(self):
        text = '\n'.join(r.content for r in self.load().resources)
        for rule in ('current completed manuscript', 'current approved manuscript',
                     'Approval is not scientific validation',
                     'Do not fill omissions in the manuscript from memory'):
            with self.subTest(rule=rule):
                self.assertIn(rule, text)

    def test_full_review_delivers_four_substantive_duties_without_quotas(self):
        text = '\n'.join(r.content for r in self.load('axes.scope.full').resources)
        for duty in ('Contribution assessment', 'Section-level examination',
                     'Competing explanations', 'Prioritized revision advice',
                     'No minimum issue count', 'not a checklist of headings'):
            with self.subTest(duty=duty):
                self.assertIn(duty, text)

    def test_quality_distinguishes_requested_deep_review_from_delta_check(self):
        text = '\n'.join(r.content for r in self.load('conditional_loads.quality_review').resources)
        self.assertIn('requested deep re-review', text)
        self.assertIn('unchanged manuscript', text)
        self.assertIn('incremental verification', text)

    def test_full_design_and_quality_loads_stay_within_default_budget(self):
        for selectors in (
            ['axes.paper_type.empirical', 'axes.design_tags.survey',
             'axes.design_tags.experiment', 'axes.design_tags.longitudinal',
             'axes.design_tags.behavioral-task', 'axes.scope.full',
             'axes.risk_threshold.all', 'conditional_loads.methods_review'],
            ['axes.scope.full', 'conditional_loads.quality_review'],
        ):
            with self.subTest(selectors=selectors):
                self.assertLessEqual(self.load(*selectors).total_chars, 12000)
