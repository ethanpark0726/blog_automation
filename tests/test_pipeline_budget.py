import ast
import unittest
from pathlib import Path


PIPELINE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "multi_agent.py"


class PipelineBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PIPELINE_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_removed_nonessential_gemini_stages(self):
        for removed_stage in ("classifier", "search_enrichment", "verifier_ko", "verifier_en"):
            self.assertNotIn(f'stage="{removed_stage}"', self.source)

    def test_standard_budget_is_three_successful_calls(self):
        assignments = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "STANDARD_SUCCESSFUL_CALLS"
                for target in node.targets
            )
        ]

        self.assertEqual(len(assignments), 1)
        self.assertEqual(ast.literal_eval(assignments[0].value), 3)

    def test_only_phase_four_call_sites_remain(self):
        stages = []
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "call_gemini":
                continue
            stage_keyword = next(
                (keyword.value for keyword in node.keywords if keyword.arg == "stage"),
                None,
            )
            if stage_keyword is not None:
                stages.append(ast.unparse(stage_keyword))

        self.assertEqual(
            sorted(stages),
            sorted(
                [
                    "'research_writer_en'",
                    "'editor_en'",
                    "'localizer_ko'",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
