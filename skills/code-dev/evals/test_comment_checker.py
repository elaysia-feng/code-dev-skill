"""复现并防止注释检查器漏检；不依赖第三方测试库。"""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "check_comments.py"
spec = importlib.util.spec_from_file_location("comment_checker", CHECKER)
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)


class CommentCheckerTests(unittest.TestCase):
    """验证真实源码诊断与命令行阻断行为。"""

    def codes(self, source, suffix=".py"):
        return {issue.code for issue in checker.check_source(Path("sample" + suffix), source)}

    def python_function(self, name="run", doc=False, comments=""):
        documentation = '    """处理任务。\n\n    Returns:\n        处理结果。\n    """\n' if doc else ""
        return f"def {name}():\n" + documentation + comments + "".join(
            f"    value = {i}\n" for i in range(22)) + "    return value\n"

    def test_python_missing_doc_does_not_skip_steps(self):
        self.assertTrue({"missing-doc", "missing-step-comments"} <= self.codes(self.python_function()))

    def test_private_python_checks_steps_without_public_doc(self):
        codes = self.codes(self.python_function("_run"))
        self.assertIn("missing-step-comments", codes)
        self.assertNotIn("missing-doc", codes)

    def test_java_public_and_private_without_javadoc_check_steps(self):
        body = "".join(f"        value = {i};\n" for i in range(22))
        for visibility in ("public", "private"):
            source = f"class Example {{\n    {visibility} void run() {{\n        int value;\n{body}    }}\n}}\n"
            codes = self.codes(source, ".java")
            self.assertIn("missing-step-comments", codes)
            self.assertEqual("missing-doc" in codes, visibility == "public")

    def test_valid_hierarchy_is_accepted(self):
        comments = "    # 1. 校验输入\n    # 1.1 核对权限\n    # 1.2 核对状态\n    # 1.2.1 核对版本\n    # 2. 执行业务\n"
        codes = self.codes(self.python_function(doc=True, comments=comments))
        self.assertNotIn("invalid-step-numbering", codes)
        self.assertNotIn("missing-step-comments", codes)

    def test_duplicate_skipped_and_orphan_steps_are_reported(self):
        for steps in (("1.", "1."), ("1.", "3."), ("1.1", "2."), ("1.", "1.2")):
            comments = "".join(f"    # {step} 业务步骤\n" for step in steps)
            self.assertIn("invalid-step-numbering", self.codes(self.python_function(comments=comments)))

    def test_strings_and_docstrings_cannot_supply_steps(self):
        source = self.python_function(doc=True).replace('    value = 0\n', '    text = """\n# 1. 字符串内容\n# 2. 字符串内容\n"""\n')
        self.assertIn("missing-step-comments", self.codes(source))

    def test_nested_function_steps_do_not_cover_outer_function(self):
        source = "def run():\n    def inner():\n        # 1. 内部校验\n        validate()\n        # 2. 内部保存\n        save()\n" + "".join(
            f"    value = {i}\n" for i in range(22))
        self.assertIn("missing-step-comments", self.codes(source))

    def test_inheritdoc_does_not_require_duplicate_tags(self):
        source = "class Example {\n    /** {@inheritDoc} */\n    public int run(int value) {\n        return value;\n    }\n}"
        self.assertFalse({"missing-param", "missing-return"} & self.codes(source, ".java"))

    def test_short_single_step_has_no_numbering_warning(self):
        self.assertNotIn("missing-step-comments", self.codes("def _run():\n    return service.run()\n"))

    def test_short_function_still_checks_written_numbering(self):
        source = "def _run():\n    # 1. 校验\n    validate()\n    # 1. 保存\n    save()\n"
        self.assertIn("invalid-step-numbering", self.codes(source))

    def test_cli_warning_threshold_and_unmatched_path(self):
        # 临时文件置于测试文件所在工作区，避免依赖不可写的系统 TEMP。
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent, prefix="comment-test-") as directory:
            path = Path(directory) / "sample.py"
            path.write_text(self.python_function(doc=True), encoding="utf-8")
            for args, expected in (([], 0), (["--fail-on", "warning"], 1)):
                result = subprocess.run([sys.executable, "-X", "utf8", str(CHECKER), str(path), *args],
                                        capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertIn("missing-step-comments", result.stdout)
            result = subprocess.run([sys.executable, str(CHECKER), str(Path(directory) / "missing.py")],
                                    capture_output=True)
            self.assertEqual(result.returncode, 2)

    def test_staged_warnings_and_strict_hook_use_index(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent, prefix="comment-test-") as directory:
            def git(*args):
                result = subprocess.run(["git", "-C", directory, *args], capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)

            git("init", "-q")
            path = Path(directory) / "sample.py"
            path.write_text("def run():\n    return 1\n", encoding="utf-8")
            git("add", ".")
            path.write_text("value = 1\n", encoding="utf-8")
            result = subprocess.run([sys.executable, str(CHECKER), "--staged", "--fail-on", "warning"],
                                    cwd=directory, capture_output=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn(b"missing-doc", result.stdout)
            bash = os.environ.get("READABILITY_BASH", "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else "bash")
            hook = CHECKER.parent / "pre-commit-check.sh"
            # 只改变注释阈值，不让外部环境中的抽象阈值干扰断言。
            for strict, expected in (("0", 0), ("1", 1)):
                environment = {**os.environ, "READABILITY_PYTHON": sys.executable,
                               "READABILITY_FAIL_ON": "none", "COMMENT_FAIL_ON": "error",
                               "READABILITY_FIRST_STRICT": strict}
                result = subprocess.run([bash, str(hook)], cwd=directory, env=environment,
                                        capture_output=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertIn(b"missing-doc", result.stdout)


if __name__ == "__main__":
    unittest.main()
